"""Downloader class tests."""

import tempfile
import time
from unittest import mock
import logging
from urllib.error import HTTPError, URLError

from django import test

from cities_light.downloader import Downloader
from cities_light.exceptions import SourceFileDoesNotExist


class TestDownloader(test.TransactionTestCase):
    """Downloader tests."""

    logger = logging.getLogger("cities_light")

    @mock.patch("cities_light.downloader.os.path.exists")
    def test_source_matches_destination(self, mock_func):
        """Tests for source_matches_destination behavior."""
        mock_func.return_value = True
        downloader = Downloader()
        # Different destination
        source = "file:///a.txt"
        dest = "/b.txt"
        self.assertFalse(downloader.source_matches_destination(source, dest))
        # Same destination with same file name
        source = "file:///data/a.txt"
        dest = "/data/a.txt"
        self.assertTrue(downloader.source_matches_destination(source, dest))
        # Different destination with same file name
        source = "http://server/download/data/a.txt"
        dest = "/data/a.txt"
        self.assertFalse(downloader.source_matches_destination(source, dest))

        mock_func.return_value = False
        # Exception handling, checking whether file exist or not,
        # if exist then checking source and destination
        source = "file:///data/a.txt"
        dest = "/data/a.txt"
        with self.assertRaises(SourceFileDoesNotExist):
            downloader.source_matches_destination(source, dest)

    @mock.patch("cities_light.downloader.time.gmtime")
    @mock.patch("cities_light.downloader.os.path.getmtime")
    @mock.patch("cities_light.downloader.os.path.getsize")
    @mock.patch("cities_light.downloader.os.path.exists")
    def test_needs_downloading(self, *args):
        """Tests for needs_downloading behavior."""
        m_urlopen = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )

        loc_exists = args[0]
        loc_getsize = args[1]
        loc_getmtime = args[2]
        loc_gmtime = args[3]

        loc_getmtime.return_value = 1
        loc_exists.return_value = True
        destination = "/data/abc"
        downloader = Downloader()
        with mock.patch("cities_light.downloader.urlopen", return_value=m_urlopen):
            # Source and local time and size's equal
            loc_gmtime.return_value = time.strptime(
                "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
            )
            loc_getsize.return_value = 13469
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": False,
            }
            result = downloader.needs_downloading(**params)
            self.assertFalse(result)

            # Destination time > source time, size is equal
            loc_gmtime.return_value = time.strptime(
                "02-01-2016 00:04:15 GMT", "%d-%m-%Y %H:%M:%S %Z"
            )
            loc_getsize.return_value = 13469
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": False,
            }
            result = downloader.needs_downloading(**params)
            self.assertFalse(result)

            # Destination time < source time, size is equal
            # gmtime is called twice: for source, then destination.
            # Source must be newer (00:04:14), destination older (00:04:13).
            loc_gmtime.side_effect = [
                time.strptime("02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"),
                time.strptime("02-01-2016 00:04:13 GMT", "%d-%m-%Y %H:%M:%S %Z"),
            ]
            loc_getsize.return_value = 13469
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": False,
            }
            result = downloader.needs_downloading(**params)
            self.assertTrue(result)

            # Source and destination time is equal,
            # source and destination size is not equal
            # getsize is called twice: for source, then destination.
            loc_gmtime.side_effect = None  # Reset after using side_effect
            loc_gmtime.return_value = time.strptime(
                "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
            )
            loc_getsize.side_effect = [13469, 13470]  # source, destination
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": False,
            }
            result = downloader.needs_downloading(**params)
            self.assertTrue(result)

            # Source and destination have the same time and size
            # force = True
            loc_getsize.side_effect = None  # Reset after using side_effect
            loc_getsize.return_value = 13469
            loc_gmtime.return_value = time.strptime(
                "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
            )
            loc_getsize.return_value = 13469
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": True,
            }
            result = downloader.needs_downloading(**params)
            self.assertTrue(result)

            # Destination file does not exist
            # exists is called for source first, then destination.
            # Source must exist, destination must not.
            loc_exists.side_effect = [True, False]
            loc_gmtime.return_value = time.strptime(
                "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
            )
            loc_getsize.return_value = 13470
            params = {
                "source": "file:///a.txt",
                "destination": destination,
                "force": False,
            }
            result = downloader.needs_downloading(**params)
            self.assertTrue(result)

    @mock.patch.object(Downloader, "source_matches_destination")
    def test_download_calls_source_matches_destination(self, m_check):
        """Test if download() checks for source and destination match."""
        m_check.return_value = True
        downloader = Downloader()
        source = "file:///a.txt"
        destination = "/tmp/a.txt"
        # The downloader.download will return false
        # as source and destination are same
        # The downloader.source_matches_destination will return
        # true and downloader.download will return false
        self.assertFalse(downloader.download(source, destination, False))
        m_check.assert_called_with(source, destination)

    @mock.patch.object(Downloader, "needs_downloading")
    @mock.patch.object(Downloader, "source_matches_destination")
    def test_download_calls_needs_downloading(self, m_check, m_need):
        """Test if download() checks if source should be downloaded."""
        m_check.return_value = False
        m_need.return_value = False
        downloader = Downloader()
        source = "file:///a.txt"
        destination = "/tmp/a.txt"
        # Here dowaloder.needs_downloading() will return false
        # as the time of modifiaction of dest>= time of source
        # and the size od source and destination are same
        # and downloader.download will return false
        self.assertFalse(downloader.download(source, destination, False))
        m_check.assert_called_with(source, destination)
        m_need.assert_called_with(source, destination, False)

    @mock.patch.object(Downloader, "needs_downloading")
    @mock.patch.object(Downloader, "source_matches_destination")
    def test_download(self, m_check, m_need):
        """Test actual download."""
        m_check.return_value = False
        m_need.return_value = True
        downloader = Downloader()
        source = "file:///b.txt"
        destination = "/tmp/a.txt"

        tmpfile = tempfile.SpooledTemporaryFile(max_size=1024000, mode="wb")
        tmpfile.write(b"source content")
        tmpfile.seek(0)

        mock_open = mock.mock_open()
        with (
            mock.patch("cities_light.downloader.urlopen", return_value=tmpfile),
            mock.patch("cities_light.downloader.open", mock_open),
        ):
            # The downloader.needs_downloading will return true and last three
            # lines of downloader.download will copy the source to destination
            self.assertTrue(downloader.download(source, destination, False))
            handle = mock_open()
            handle.write.assert_called_once_with(b"source content")

    def test_not_download(self):
        """Tests actual not download."""
        with mock.patch.object(Downloader, "source_matches_destination") as m:
            m.return_value = True
            downloader = Downloader()
            source = "file:///b.txt"
            destination = "/tmp/a.txt"
            with mock.patch("cities_light.downloader.urlopen") as uo_mock:
                downloader.download(source, destination)
                uo_mock.assert_not_called()

        with mock.patch.object(Downloader, "source_matches_destination") as m:
            m.return_value = False
            with mock.patch.object(Downloader, "needs_downloading") as n:
                n.return_value = False
                downloader = Downloader()
                source = "file:///b.txt"
                destination = "/a.txt"
                # Here copy of b has been made in above function,the
                # downloder.needs_downloading() will return false
                # and no download will happen
                with mock.patch("cities_light.downloader.urlopen") as uo_mock:
                    downloader.download(source, destination)
                    uo_mock.assert_not_called()


class TestNeedsDownloadingHttpHttps(test.TransactionTestCase):
    """Tests for needs_downloading HTTP/HTTPS branch."""

    def test_head_used_for_http(self):
        """Verify HTTP sources use HEAD request."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        destination = "/data/abc"
        with (
            mock.patch("cities_light.downloader.urlopen", return_value=m_response),
            mock.patch("cities_light.downloader.Request") as m_request,
            mock.patch("cities_light.downloader.os.path.exists", return_value=True),
            mock.patch("cities_light.downloader.os.path.getsize", return_value=13469),
            mock.patch("cities_light.downloader.os.path.getmtime", return_value=1),
            mock.patch(
                "cities_light.downloader.time.gmtime",
                return_value=time.strptime(
                    "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
                ),
            ),
        ):
            m_request.return_value = "request_obj"
            result = Downloader.needs_downloading(
                "http://example.com/file.zip", destination, False
            )
            m_request.assert_called_once_with("http://example.com/file.zip", method="HEAD")
            self.assertFalse(result)

    def test_head_used_for_https(self):
        """Verify HTTPS sources use HEAD request."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        destination = "/data/abc"
        with (
            mock.patch("cities_light.downloader.urlopen", return_value=m_response),
            mock.patch("cities_light.downloader.Request") as m_request,
            mock.patch("cities_light.downloader.os.path.exists", return_value=True),
            mock.patch("cities_light.downloader.os.path.getsize", return_value=13469),
            mock.patch("cities_light.downloader.os.path.getmtime", return_value=1),
            mock.patch(
                "cities_light.downloader.time.gmtime",
                return_value=time.strptime(
                    "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
                ),
            ),
        ):
            m_request.return_value = "request_obj"
            result = Downloader.needs_downloading(
                "https://example.com/data.zip", destination, False
            )
            m_request.assert_called_once_with(
                "https://example.com/data.zip", method="HEAD"
            )
            self.assertFalse(result)

    @mock.patch("cities_light.downloader.time.gmtime")
    @mock.patch("cities_light.downloader.os.path.getmtime")
    @mock.patch("cities_light.downloader.os.path.getsize")
    @mock.patch("cities_light.downloader.os.path.exists")
    def test_http_valid_headers_no_download_needed(
        self, loc_exists, loc_getsize, loc_getmtime, loc_gmtime
    ):
        """Destination exists with same time and size - no download needed."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        loc_exists.return_value = True
        loc_getsize.return_value = 13469
        loc_getmtime.return_value = 1
        loc_gmtime.return_value = time.strptime(
            "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertFalse(result)

    @mock.patch("cities_light.downloader.time.gmtime")
    @mock.patch("cities_light.downloader.os.path.getmtime")
    @mock.patch("cities_light.downloader.os.path.getsize")
    @mock.patch("cities_light.downloader.os.path.exists")
    def test_http_valid_headers_download_needed_dest_older(
        self, loc_exists, loc_getsize, loc_getmtime, loc_gmtime
    ):
        """Destination older than source - download needed."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        loc_exists.return_value = True
        loc_getsize.return_value = 13469
        loc_getmtime.return_value = 1
        # Local destination older (00:04:13) than source (00:04:14)
        loc_gmtime.return_value = time.strptime(
            "02-01-2016 00:04:13 GMT", "%d-%m-%Y %H:%M:%S %Z"
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    @mock.patch("cities_light.downloader.time.gmtime")
    @mock.patch("cities_light.downloader.os.path.getmtime")
    @mock.patch("cities_light.downloader.os.path.getsize")
    @mock.patch("cities_light.downloader.os.path.exists")
    def test_http_valid_headers_download_needed_size_differs(
        self, loc_exists, loc_getsize, loc_getmtime, loc_gmtime
    ):
        """Destination size differs from source - download needed."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        loc_exists.return_value = True
        loc_getsize.return_value = 13470  # Different from 13469
        loc_getmtime.return_value = 1
        loc_gmtime.return_value = time.strptime(
            "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_missing_last_modified_header(self):
        """Missing last-modified header returns True (download needed)."""
        m_response = mock.Mock(headers={"content-length": "13469"})
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_missing_content_length_header(self):
        """Missing content-length header returns True (download needed)."""
        m_response = mock.Mock(
            headers={"last-modified": "Sat, 02 Jan 2016 00:04:14 GMT"}
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_both_headers_missing(self):
        """Both headers missing returns True (download needed)."""
        m_response = mock.Mock(headers={})
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_malformed_content_length(self):
        """Malformed content-length (non-integer) returns True."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "abc",
            }
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_malformed_last_modified(self):
        """Malformed last-modified format returns True."""
        m_response = mock.Mock(
            headers={
                "last-modified": "invalid-date-format",
                "content-length": "13469",
            }
        )
        with mock.patch("cities_light.downloader.urlopen", return_value=m_response):
            result = Downloader.needs_downloading(
                "http://example.com/data.zip", "/data/abc", False
            )
        self.assertTrue(result)

    def test_http_head_request_fails_http_error(self):
        """HEAD request raising HTTPError propagates exception."""
        with mock.patch(
            "cities_light.downloader.urlopen",
            side_effect=HTTPError(
                "http://example.com/file.zip", 405, "Method Not Allowed", {}, None
            ),
        ):
            with self.assertRaises(HTTPError):
                Downloader.needs_downloading(
                    "http://example.com/file.zip", "/data/abc", False
                )

    def test_http_head_request_fails_url_error(self):
        """HEAD request raising URLError propagates exception."""
        with mock.patch(
            "cities_light.downloader.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaises(URLError):
                Downloader.needs_downloading(
                    "http://example.com/file.zip", "/data/abc", False
                )

    def test_non_http_scheme_uses_get(self):
        """Non-HTTP(S) scheme uses GET (urlopen with URL, not HEAD Request)."""
        m_response = mock.Mock(
            headers={
                "last-modified": "Sat, 02 Jan 2016 00:04:14 GMT",
                "content-length": "13469",
            }
        )
        destination = "/data/abc"
        with (
            mock.patch("cities_light.downloader.urlopen", return_value=m_response) as m_uo,
            mock.patch("cities_light.downloader.Request") as m_request,
            mock.patch("cities_light.downloader.os.path.exists", return_value=True),
            mock.patch("cities_light.downloader.os.path.getsize", return_value=13469),
            mock.patch("cities_light.downloader.os.path.getmtime", return_value=1),
            mock.patch(
                "cities_light.downloader.time.gmtime",
                return_value=time.strptime(
                    "02-01-2016 00:04:14 GMT", "%d-%m-%Y %H:%M:%S %Z"
                ),
            ),
        ):
            result = Downloader.needs_downloading(
                "ftp://example.com/data.zip", destination, False
            )
            m_request.assert_not_called()
            m_uo.assert_called_once_with("ftp://example.com/data.zip")
            self.assertFalse(result)
