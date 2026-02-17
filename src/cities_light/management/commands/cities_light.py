import collections
import itertools
import os
import datetime
import logging
from argparse import RawTextHelpFormatter

import psutil
import pickle

from django.conf import settings
from django.db import transaction, connection
from django.db import reset_queries, IntegrityError
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError

import progressbar

from ...settings import (
    BULK_BATCH_SIZE,
    COUNTRY_SOURCES,
    REGION_SOURCES,
    SUBREGION_SOURCES,
    CITY_SOURCES,
    TRANSLATION_SOURCES,
    DATA_DIR,
    TRANSLATION_LANGUAGES,
    ICountry,
    IRegion,
    ISubRegion,
    ICity,
    IAlternate,
)
from ...signals import (
    country_items_pre_import,
    region_items_pre_import,
    subregion_items_pre_import,
    city_items_pre_import,
    translation_items_pre_import,
    country_items_post_import,
    region_items_post_import,
    subregion_items_post_import,
    city_items_post_import,
)
from ...exceptions import InvalidItems
from ...geonames import Geonames
from ...abstract_models import to_ascii
from ...loading import get_cities_models
from ...validators import timezone_validator

Country, Region, SubRegion, City = get_cities_models()


class MemoryUsageWidget(progressbar.widgets.WidgetBase):
    def __call__(self, progress, data):
        process = psutil.Process()
        rss_bytes = process.memory_info().rss
        return "%s MB" % (rss_bytes // 1048576)


class Command(BaseCommand):
    help = """
Download all files in CITIES_LIGHT_COUNTRY_SOURCES if they were updated or if
--force-all option was used.
Import country data if they were downloaded or if --force-import-all was used.

Same goes for CITIES_LIGHT_CITY_SOURCES.

It is possible to force the download of some files which have not been updated
on the server:

    manage.py cities_light --force cities15000 --force countryInfo

It is possible to force the import of files which weren't downloaded using the
--force-import option:

    manage.py cities_light --force-import cities15000 --force-import country
    """.strip()

    logger = logging.getLogger("cities_light")

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        (
            parser.add_argument(
                "--force-import-all",
                action="store_true",
                default=False,
                help="Import even if files are up-to-date.",
            ),
        )
        (
            parser.add_argument(
                "--force-all",
                action="store_true",
                default=False,
                help="Download and import if files are up-to-date.",
            ),
        )
        (
            parser.add_argument(
                "--force-import",
                action="append",
                default=[],
                help="Import even if files matching files are up-to-date",
            ),
        )
        (
            parser.add_argument(
                "--force",
                action="append",
                default=[],
                help="Download and import even if matching files are up-to-date",
            ),
        )
        (
            parser.add_argument(
                "--noinsert",
                action="store_true",
                default=False,
                help="Update existing data only",
            ),
        )
        (
            parser.add_argument(
                "--hack-translations",
                action="store_true",
                default=False,
                help="Set this if you intend to import translations a lot",
            ),
        )
        (
            parser.add_argument(
                "--keep-slugs",
                action="store_true",
                default=False,
                help="Do not update slugs",
            ),
        )
        (
            parser.add_argument(
                "--progress",
                action="store_true",
                default=False,
                help="Show progress bar",
            ),
        )

    def progress_init(self):
        """Initialize progress bar."""
        if self.progress_enabled:
            self.progress_widgets = [
                "RAM used: ",
                MemoryUsageWidget(),
                " ",
                progressbar.ETA(),
                " Done: ",
                progressbar.Percentage(),
                progressbar.Bar(),
            ]

    def progress_start(self, max_value):
        """Start progress bar."""
        if self.progress_enabled:
            self.progress = progressbar.ProgressBar(
                max_value=max_value, widgets=self.progress_widgets
            ).start()

    def progress_update(self, value):
        """Update progress bar."""
        if self.progress_enabled:
            self.progress.update(value)

    def progress_finish(self):
        """Finalize progress bar."""
        if self.progress_enabled:
            self.progress.finish()

    def handle(self, *args, **options):
        # initialize lazy identity maps
        self._clear_identity_maps()
        self._country_insert_buffer = []
        self._region_insert_buffer = []
        self._subregion_insert_buffer = []

        if not os.path.exists(DATA_DIR):
            self.logger.info("Creating %s", DATA_DIR)
            os.mkdir(DATA_DIR)

        install_file_path = os.path.join(DATA_DIR, "install_datetime")
        translation_hack_path = os.path.join(DATA_DIR, "translation_hack")

        self.noinsert = options.get("noinsert", False)
        self.keep_slugs = options.get("keep_slugs", False)
        self.progress_enabled = options.get("progress")

        self.progress_init()

        sources = list(
            itertools.chain(
                COUNTRY_SOURCES,
                REGION_SOURCES,
                SUBREGION_SOURCES,
                CITY_SOURCES,
                TRANSLATION_SOURCES,
            )
        )

        for url in sources:
            if url in TRANSLATION_SOURCES:
                # free some memory
                self._clear_identity_maps()

            # Flush insert buffers before switching to next source type
            self._flush_country_buffer()
            self._flush_region_buffer()
            self._flush_subregion_buffer()

            destination_file_name = url.split("/")[-1]

            force = options.get("force_all", False)
            if not force:
                for f in options["force"]:
                    if f in destination_file_name or f in url:
                        force = True

            geonames = Geonames(url, force=force)
            downloaded = geonames.downloaded

            force_import = options.get("force_import_all", False)

            if not force_import:
                for f in options["force_import"]:
                    if f in destination_file_name or f in url:
                        force_import = True

            if not os.path.exists(install_file_path):
                self.logger.info(
                    "Forced import of %s because data do not seem"
                    " to have installed successfully yet, note that this is"
                    " equivalent to --force-import-all.",
                    destination_file_name,
                )
                force_import = True

            if downloaded or force_import:
                self.logger.info("Importing %s", destination_file_name)

                if url in TRANSLATION_SOURCES:
                    if options.get("hack_translations", False):
                        if os.path.exists(translation_hack_path):
                            self.logger.debug(
                                "Using translation parsed data: %s",
                                translation_hack_path,
                            )
                            continue

                i = 0
                self.progress_start(geonames.num_lines())

                for items in geonames.parse():
                    if url in CITY_SOURCES:
                        self.city_import(items)
                    elif url in REGION_SOURCES:
                        self.region_import(items)
                    elif url in COUNTRY_SOURCES:
                        self.country_import(items)
                    elif url in SUBREGION_SOURCES:
                        self.subregion_import(items)
                    elif url in TRANSLATION_SOURCES:
                        self.translation_parse(items)

                    # prevent memory leaks in DEBUG mode
                    # https://docs.djangoproject.com/en/1.9/faq/models/
                    # #how-can-i-see-the-raw-sql-queries-django-is-running
                    if settings.DEBUG:
                        reset_queries()

                    i += 1
                    self.progress_update(i)

                self.progress_finish()

                if url in TRANSLATION_SOURCES and options.get(
                    "hack_translations", False
                ):
                    with open(translation_hack_path, "wb+") as f:
                        pickle.dump(self.translation_data, f)

        if options.get("hack_translations", False):
            if os.path.getsize(translation_hack_path) > 0:
                with open(translation_hack_path, "rb") as f:
                    self.translation_data = pickle.load(f)
            else:
                self.logger.debug(
                    "The translation file that you are trying to load is empty: %s",
                    translation_hack_path,
                )

        self.logger.info("Importing parsed translation in the database")
        self.translation_import()

        with open(install_file_path, "wb+") as f:
            pickle.dump(datetime.datetime.now(), f)

    def _clear_identity_maps(self):
        """Clear identity maps and free some memory."""
        if getattr(self, "_country_codes", False):
            del self._country_codes
        if getattr(self, "_region_codes", False):
            del self._region_codes
        if getattr(self, "_subregion_codes", False):
            del self._subregion_codes
        self._country_codes = {}
        self._region_codes = collections.defaultdict(dict)
        self._subregion_codes = collections.defaultdict(
            lambda: collections.defaultdict(dict)
        )

    def _flush_country_buffer(self):
        """Flush country insert buffer with bulk_create."""
        buffer = getattr(self, "_country_insert_buffer", [])
        if not buffer:
            return
        self._country_insert_buffer = []
        for country in buffer:
            name_ascii = to_ascii(country.name).strip()
            country.name_ascii = name_ascii or ""
        seen = set()
        to_insert = []
        for country in buffer:
            if country.geoname_id in seen:
                continue
            seen.add(country.geoname_id)
            to_insert.append(country)
        existing = set(
            Country.objects.filter(
                geoname_id__in=[x.geoname_id for x in to_insert]
            ).values_list("geoname_id", flat=True)
        )
        to_insert = [c for c in to_insert if c.geoname_id not in existing]
        if to_insert:
            with transaction.atomic():
                Country.objects.bulk_create(to_insert)
        for c in Country.objects.filter(
            geoname_id__in=[x.geoname_id for x in buffer]
        ).values_list("code2", "pk"):
            self._country_codes[c[0]] = c[1]

    def _flush_region_buffer(self):
        """Flush region insert buffer with bulk_create."""
        buffer = getattr(self, "_region_insert_buffer", [])
        if not buffer:
            return
        self._region_insert_buffer = []
        country_ids = {r.country_id for r in buffer}
        countries = {
            c["pk"]: c["name"]
            for c in Country.objects.filter(pk__in=country_ids).values("pk", "name")
        }
        for region in buffer:
            name_ascii = to_ascii(region.name).strip()
            region.name_ascii = name_ascii or ""
            region.display_name = "%s, %s" % (
                region.name,
                countries.get(region.country_id, ""),
            )
        seen = set()
        to_insert = []
        for region in buffer:
            if region.geoname_id in seen:
                continue
            seen.add(region.geoname_id)
            to_insert.append(region)
        existing = set(
            Region.objects.filter(
                geoname_id__in=[x.geoname_id for x in to_insert]
            ).values_list("geoname_id", flat=True)
        )
        to_insert = [r for r in to_insert if r.geoname_id not in existing]
        if to_insert:
            with transaction.atomic():
                Region.objects.bulk_create(to_insert)
        for r in Region.objects.filter(
            geoname_id__in=[x.geoname_id for x in buffer]
        ).values_list("country__code2", "geoname_code", "pk"):
            if r[0] in self._country_codes:
                self._region_codes[self._country_codes[r[0]]][r[1]] = r[2]

    def _flush_subregion_buffer(self):
        """Flush subregion insert buffer with bulk_create."""
        buffer = getattr(self, "_subregion_insert_buffer", [])
        if not buffer:
            return
        self._subregion_insert_buffer = []
        country_ids = {s.country_id for s in buffer if s.country_id}
        countries = (
            {
                c["pk"]: c["name"]
                for c in Country.objects.filter(pk__in=country_ids).values("pk", "name")
            }
            if country_ids
            else {}
        )
        for subregion in buffer:
            name_ascii = to_ascii(subregion.name).strip()
            subregion.name_ascii = name_ascii or ""
            subregion.display_name = "%s, %s" % (
                subregion.name,
                countries.get(subregion.country_id, ""),
            )
        seen = set()
        to_insert = []
        for subregion in buffer:
            if subregion.geoname_id in seen:
                continue
            seen.add(subregion.geoname_id)
            to_insert.append(subregion)
        existing = set(
            SubRegion.objects.filter(
                geoname_id__in=[x.geoname_id for x in to_insert]
            ).values_list("geoname_id", flat=True)
        )
        to_insert = [s for s in to_insert if s.geoname_id not in existing]
        if to_insert:
            with transaction.atomic():
                SubRegion.objects.bulk_create(to_insert)
        for s in SubRegion.objects.filter(
            geoname_id__in=[x.geoname_id for x in buffer]
        ).values_list("country__code2", "region__geoname_code", "geoname_code", "pk"):
            country_id = self._country_codes.get(s[0])
            if country_id is not None:
                if s[1] not in self._region_codes[country_id]:
                    region_pk = (
                        Region.objects.filter(country_id=country_id, geoname_code=s[1])
                        .values_list("pk", flat=True)
                        .first()
                    )
                    if region_pk:
                        self._region_codes[country_id][s[1]] = region_pk
                self._subregion_codes[country_id][s[1]][s[2]] = s[3]

    def _get_country_id(self, country_code2):
        """
        Simple lazy identity map for code2->country
        """
        if country_code2 not in self._country_codes:
            self._country_codes[country_code2] = Country.objects.get(
                code2=country_code2
            ).pk

        return self._country_codes[country_code2]

    def _get_region_id(self, country_code2, region_id):
        """
        Simple lazy identity map for (country_code2, region_id)->region
        """
        country_id = self._get_country_id(country_code2)
        if region_id not in self._region_codes[country_id]:
            self._region_codes[country_id][region_id] = Region.objects.get(
                country_id=country_id, geoname_code=region_id
            ).pk

        return self._region_codes[country_id][region_id]

    def _get_subregion_id(self, country_code2, region_id, subregion_id):
        """
        Simple lazy identity map for (country_code2, region_id,
        subregion_id)->subregion
        """
        country_id = self._get_country_id(country_code2)
        if region_id not in self._region_codes[country_id]:
            self._region_codes[country_id][region_id] = Region.objects.get(
                country_id=country_id, geoname_code=region_id
            ).pk

        if subregion_id not in self._subregion_codes[country_id][region_id]:
            self._subregion_codes[country_id][region_id][subregion_id] = (
                SubRegion.objects.get(
                    region_id=self._region_codes[country_id][region_id],
                    geoname_code=subregion_id,
                ).pk
            )
        return self._subregion_codes[country_id][region_id][subregion_id]

    def country_import(self, items):
        try:
            country_items_pre_import.send(sender=self, items=items)
        except InvalidItems:
            return
        force_insert = False
        force_update = False
        if items[ICountry.geonameid] == "":
            return
        try:
            country = Country.objects.get(geoname_id=items[ICountry.geonameid])
            force_update = True
        except Country.DoesNotExist:
            if self.noinsert:
                return
            country = Country(geoname_id=items[ICountry.geonameid])
            force_insert = True

        country.name = items[ICountry.name]
        country.code2 = items[ICountry.code2]
        country.code3 = items[ICountry.code3]
        country.continent = items[ICountry.continent]
        country.tld = items[ICountry.tld][1:]  # strip the leading dot
        # Strip + prefix for consistency. Note that some countries have several
        # prefixes i.e. Puerto Rico
        country.phone = items[ICountry.phone].replace("+", "")
        # Clear name_ascii to always update it by set_name_ascii() signal
        country.name_ascii = ""

        if force_update and not self.keep_slugs:
            country.slug = None

        country_items_post_import.send(sender=self, instance=country, items=items)

        if force_insert and BULK_BATCH_SIZE > 0:
            self._country_insert_buffer.append(country)
            if len(self._country_insert_buffer) >= BULK_BATCH_SIZE:
                self._flush_country_buffer()
        else:
            self.save(country, force_insert=force_insert, force_update=force_update)

    def region_import(self, items):
        try:
            region_items_pre_import.send(sender=self, items=items)
        except InvalidItems:
            return

        force_insert = False
        force_update = False
        try:
            region = Region.objects.get(geoname_id=items[IRegion.geonameid])
            force_update = True
        except Region.DoesNotExist:
            if self.noinsert:
                return
            region = Region(geoname_id=items[IRegion.geonameid])
            force_insert = True

        name = items[IRegion.name]
        if not items[IRegion.name]:
            name = items[IRegion.asciiName]

        code2, geoname_code = items[IRegion.code].split(".")
        country_id = self._get_country_id(code2)

        save = False
        if region.name != name:
            region.name = name
            save = True

        if region.country_id != country_id:
            region.country_id = country_id
            save = True

        if region.geoname_code != geoname_code:
            region.geoname_code = geoname_code
            save = True

        if region.name_ascii != items[IRegion.asciiName]:
            region.name_ascii = items[IRegion.asciiName]
            save = True

        if force_update and not self.keep_slugs:
            region.slug = None

        region_items_post_import.send(sender=self, instance=region, items=items)

        if save:
            if force_insert and BULK_BATCH_SIZE > 0:
                self._region_insert_buffer.append(region)
                if len(self._region_insert_buffer) >= BULK_BATCH_SIZE:
                    self._flush_region_buffer()
            else:
                self.save(region, force_insert=force_insert, force_update=force_update)

    def subregion_import(self, items):

        try:
            subregion_items_pre_import.send(sender=self, items=items)
        except InvalidItems:
            return

        force_insert = False
        force_update = False
        try:
            subregion = SubRegion.objects.get(geoname_id=items[ISubRegion.geonameid])
            force_update = True
        except SubRegion.DoesNotExist:
            if self.noinsert:
                return
            subregion = SubRegion(geoname_id=items[ISubRegion.geonameid])
            force_insert = True

        name = items[ISubRegion.name]
        if not items[ISubRegion.name]:
            name = items[ISubRegion.asciiName]

        code2, admin1Code, geoname_code = items[ISubRegion.code].split(".")
        try:
            country_id = self._get_country_id(code2)
        except Country.DoesNotExist:
            country_id = None

        try:
            region_id = self._get_region_id(code2, admin1Code)
        except Region.DoesNotExist:
            region_id = None

        save = False
        if subregion.name != name:
            subregion.name = name
            save = True

        if subregion.country_id != country_id:
            subregion.country_id = country_id
            save = True

        if subregion.region_id != region_id:
            subregion.region_id = region_id
            save = True

        if subregion.geoname_code != geoname_code:
            subregion.geoname_code = geoname_code
            save = True

        if subregion.name_ascii != items[ISubRegion.asciiName]:
            subregion.name_ascii = items[ISubRegion.asciiName]
            save = True

        if force_update and not self.keep_slugs:
            subregion.slug = None

        subregion_items_post_import.send(sender=self, instance=subregion, items=items)

        if save:
            if force_insert and BULK_BATCH_SIZE > 0:
                self._subregion_insert_buffer.append(subregion)
                if len(self._subregion_insert_buffer) >= BULK_BATCH_SIZE:
                    self._flush_subregion_buffer()
            else:
                self.save(
                    subregion, force_insert=force_insert, force_update=force_update
                )

    def city_import(self, items):
        try:
            city_items_pre_import.send(sender=self, items=items)
        except InvalidItems:
            return

        force_insert = False
        force_update = False
        try:
            city = City.objects.get(geoname_id=items[ICity.geonameid])
            force_update = True
        except City.DoesNotExist:
            if self.noinsert:
                return
            city = City(geoname_id=items[ICity.geonameid])
            force_insert = True

        try:
            country_id = self._get_country_id(items[ICity.countryCode])
        except Country.DoesNotExist:
            if self.noinsert:
                return
            else:
                raise

        try:
            region_id = self._get_region_id(
                items[ICity.countryCode], items[ICity.admin1Code]
            )
        except Region.DoesNotExist:
            region_id = None

        try:
            subregion_id = self._get_subregion_id(
                items[ICity.countryCode],
                items[ICity.admin1Code],
                items[ICity.admin2Code],
            )
        except (SubRegion.DoesNotExist, Region.DoesNotExist):
            subregion_id = None

        save = False
        if city.country_id != country_id:
            city.country_id = country_id
            save = True

        if city.region_id != region_id:
            city.region_id = region_id
            save = True

        if city.subregion_id != subregion_id:
            city.subregion_id = subregion_id
            save = True

        if city.name != items[ICity.name]:
            city.name = items[ICity.name]
            save = True

        if city.name_ascii != items[ICity.asciiName]:
            # useful for cities with chinese names
            city.name_ascii = items[ICity.asciiName]
            save = True

        if city.latitude != items[ICity.latitude]:
            city.latitude = items[ICity.latitude]
            save = True

        if city.longitude != items[ICity.longitude]:
            city.longitude = items[ICity.longitude]
            save = True

        if city.population != items[ICity.population]:
            city.population = items[ICity.population]
            save = True

        if city.feature_code != items[ICity.featureCode]:
            city.feature_code = items[ICity.featureCode]
            save = True

        if city.timezone != items[ICity.timezone]:
            try:
                timezone_validator(items[ICity.timezone])
                city.timezone = items[ICity.timezone]
            except ValidationError as e:
                city.timezone = None
                self.logger.warning(e.messages)
            save = True

        altnames = items[ICity.alternateNames]
        if not TRANSLATION_SOURCES and city.alternate_names != altnames:
            city.alternate_names = altnames
            save = True

        if force_update and not self.keep_slugs:
            city.slug = None

        city_items_post_import.send(sender=self, instance=city, items=items, save=save)

        if save:
            self.save(city, force_insert=force_insert, force_update=force_update)

    def translation_parse(self, items):
        if not hasattr(self, "translation_data"):
            self.country_ids = set(Country.objects.values_list("geoname_id", flat=True))
            self.region_ids = set(Region.objects.values_list("geoname_id", flat=True))
            self.city_ids = set(City.objects.values_list("geoname_id", flat=True))
            self.subregion_ids = set(
                SubRegion.objects.values_list("geoname_id", flat=True)
            )

            self.translation_data = collections.OrderedDict(
                (
                    (Country, {}),
                    (Region, {}),
                    (City, {}),
                    (SubRegion, {}),
                )
            )

        # https://code.djangoproject.com/ticket/21597#comment:29
        # Skip connection.close() when inside atomic block (e.g. TestCase)
        # TransactionManagementError on subsequent queries (Django #21239).
        if (
            "mysql" in settings.DATABASES["default"]["ENGINE"]
            and not connection.in_atomic_block
        ):
            connection.close()

        try:
            translation_items_pre_import.send(sender=self, items=items)
        except InvalidItems:
            return

        if len(items) > 5:
            # avoid shortnames, colloquial, and historic
            return

        item_lang = items[IAlternate.language]

        if item_lang not in TRANSLATION_LANGUAGES:
            return

        item_geoid = items[IAlternate.geonameid]
        item_name = items[IAlternate.name]

        # arg optimisation code kills me !!!
        item_geoid = int(item_geoid)

        if item_geoid in self.country_ids:
            model_class = Country
        elif item_geoid in self.region_ids:
            model_class = Region
        elif item_geoid in self.city_ids:
            model_class = City
        elif item_geoid in self.subregion_ids:
            model_class = SubRegion
        else:
            return

        if item_geoid not in self.translation_data[model_class]:
            self.translation_data[model_class][item_geoid] = {}

        if item_lang not in self.translation_data[model_class][item_geoid]:
            self.translation_data[model_class][item_geoid][item_lang] = []

        self.translation_data[model_class][item_geoid][item_lang].append(item_name)

    def translation_import(self):
        data = getattr(self, "translation_data", None)

        if not data:
            return

        max = 0
        for model_class, model_class_data in data.items():
            max += len(model_class_data.keys())

        i = 0
        self.progress_start(max)

        for model_class, model_class_data in data.items():
            for geoname_id, geoname_data in model_class_data.items():
                try:
                    model = model_class.objects.get(geoname_id=geoname_id)
                except model_class.DoesNotExist:
                    continue

                save = False
                alternate_names = set()
                for lang, names in geoname_data.items():
                    if lang == "post":
                        # we might want to save the postal codes somewhere
                        # here's where it will all start ...
                        continue

                    for name in names:
                        if name == model.name:
                            continue

                        alternate_names.add(name)

                alternate_names = ";".join(sorted(alternate_names))
                if model.alternate_names != alternate_names:
                    model.alternate_names = alternate_names
                    save = True

                if model.translations != geoname_data:
                    model.translations = geoname_data
                    save = True

                if save:
                    model.save(force_update=True)

                i += 1
                self.progress_update(i)

        self.progress_finish()

    def save(self, model, force_insert=False, force_update=False):
        try:
            with transaction.atomic():
                self.logger.debug("Saving %s", model.name)
                model.save(force_insert=force_insert, force_update=force_update)
        except IntegrityError as e:
            # Regarding %r see the https://code.djangoproject.com/ticket/20572
            # Also related to http://bugs.python.org/issue2517
            self.logger.warning("Saving %s failed: %r", model, e)
