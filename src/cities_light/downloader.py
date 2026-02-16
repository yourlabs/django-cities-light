"""Data downloader."""

import logging
import time
import os

from urllib.request import Request, urlopen
from urllib.parse import urlparse

from .exceptions import SourceFileDoesNotExist


class Downloader:
    """Geonames data downloader class."""

    def download(self, source: str, destination: str, force: bool = False):
        """Download source file/url to destination."""
        logger = logging.getLogger("cities_light")

        # Prevent copying itself
        # If same file then return
        if self.source_matches_destination(source, destination):
            logger.warning("Download source matches destination file")
            return False
        # Checking if download is needed i.e. names are different but
        # they are same file essentiallly
        # If needed continue else return.
        if not self.needs_downloading(source, destination, force):
            logger.warning("Assuming local download is up to date for %s", source)
            return False
        # If the files are different, download/copy happens
        logger.info("Downloading %s into %s", source, destination)
        with urlopen(source) as source_stream:
            with open(destination, "wb") as local_file:
                local_file.write(source_stream.read())

        return True

    @staticmethod
    def source_matches_destination(source: str, destination: str):
        """Return True if source and destination point to the same file."""
        parsed_source = urlparse(source)
        if parsed_source.scheme == "file":
            source_path = os.path.abspath(
                os.path.join(parsed_source.netloc, parsed_source.path)
            )
            # Checking exception of file exist or not
            if not os.path.exists(source_path):
                raise SourceFileDoesNotExist(source_path)

            if source_path == destination:
                return True
        return False

    @staticmethod
    def needs_downloading(source: str, destination: str, force: bool):
        """Return True if source should be downloaded to destination."""
        parsed = urlparse(source)

        if parsed.scheme == "file":
            source_path = os.path.abspath(os.path.join(parsed.netloc, parsed.path))
            if not os.path.exists(source_path):
                raise SourceFileDoesNotExist(source_path)
            src_size = os.path.getsize(source_path)
            src_mtime = os.path.getmtime(source_path)
            src_last_modified = time.gmtime(src_mtime)
        else:
            # Use HEAD for http/https to avoid fetching the body
            if parsed.scheme in ("http", "https"):
                req = Request(source, method="HEAD")
                src_file = urlopen(req)
            else:
                src_file = urlopen(source)

            try:
                src_size = int(src_file.headers["content-length"])
                src_last_modified = time.strptime(
                    src_file.headers["last-modified"],
                    "%a, %d %b %Y %H:%M:%S %Z",
                )
            except (KeyError, TypeError, ValueError):
                return True
            finally:
                src_file.close()

        if os.path.exists(destination) and not force:
            local_time = time.gmtime(os.path.getmtime(destination))
            local_size = os.path.getsize(destination)
            if local_time >= src_last_modified and local_size == src_size:
                return False
        return True
