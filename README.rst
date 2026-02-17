.. image:: https://github.com/yourlabs/django-cities-light/actions/workflows/django.yml/badge.svg?branch=master
    :target: https://github.com/yourlabs/django-cities-light/actions/workflows/django.yml
.. image:: https://img.shields.io/pypi/dm/django-cities-light.svg
    :target: https://pypi.org/project/django-cities-light/
.. image:: https://img.shields.io/pypi/v/django-cities-light.svg
    :target: https://pypi.org/project/django-cities-light/
.. image:: https://codecov.io/gh/yourlabs/django-cities-light/graph/badge.svg
    :target: https://codecov.io/gh/yourlabs/django-cities-light


django-cities-light -- *Simple django-cities alternative*
=========================================================

This add-on provides models and commands to import country, subregion, region/state, and
city data in your database.

The data is pulled from `GeoNames
<http://www.geonames.org/>`_ and contains cities, subregions, regions/states and countries.

Spatial query support is not required by this application.

This application is very simple and is useful if you want to make a simple
address book for example. If you intend to build a fully featured spatial
database, you should use
`django-cities
<https://github.com/coderholic/django-cities>`_.

Requirements:

- Python >= 3.10
- Django >= 4.2
- MySQL or PostgreSQL or SQLite.

Features
--------
- GraphQL support
- Built-in admin support
- Rest-Framework support
- Ajax Select Lookup support

Upgrade
-------

See CHANGELOG.

Installation
------------

Install django-cities-light::

    pip install django-cities-light

Or the development version::

    pip install -e git+https://github.com/yourlabs/django-cities-light.git#egg=django-cities-light

Add `cities_light` to your `INSTALLED_APPS`.

Configure filters to exclude data you don't want, ie.::

    CITIES_LIGHT_TRANSLATION_LANGUAGES = ['fr', 'en']
    CITIES_LIGHT_INCLUDE_COUNTRIES = ['FR']
    CITIES_LIGHT_INCLUDE_CITY_TYPES = ['PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC', 'PPLF', 'PPLG', 'PPLL', 'PPLR', 'PPLS', 'STLMT',]

To tune import performance, you can set ``CITIES_LIGHT_BULK_BATCH_SIZE`` (default: 500).
This controls the batch size for bulk inserts of Country, Region, and SubRegion during import.
Set to 0 to disable batching and use per-row saves::

    CITIES_LIGHT_BULK_BATCH_SIZE = 500  # or 0 to disable

Now, run migrations, it will only create tables for models that are not
disabled::

    ./manage.py migrate

Data import/update
------------------

Finally, populate your database with command::

    ./manage.py cities_light

This command is well documented, consult the help with::

    ./manage.py help cities_light

By default, update procedure attempts to update all fields, including Country/Region/Subregion/City slugs. But there is an option to keep them intact::

    ./manage.py cities_light --keep-slugs


Get more cities
---------------

The configuration parameter CITIES_LIGHT_CITY_SOURCES, comes with the default value
http://download.geonames.org/export/dump/cities15000.zip that has cities with a population
over 15000, if you need to load cities with less population please use another source. For the list
of available source please check here: http://download.geonames.org/export/dump/readme.txt



Using fixtures
--------------

Geonames.org is updated on daily basis and its full import is quite slow, so
if you want to import the same data multiple times (for example on different
servers) it is convenient to use fixtures with the helper management command::

    ./manage.py cities_light_fixtures dump
    ./manage.py cities_light_fixtures load

To reduce space, JSON fixtures are compressed with bzip2 and can be fetched
from any HTTP server or local filesystem.

Consult the help with::

    ./manage.py help cities_light_fixtures


Common issues
--------------

Search names index size issue
------------------------------

If you get the following error::

    django.db.utils.OperationalError: index row size 2848 exceeds btree version 4 maximum 2704 for index "cities_light_city_search_names_fb77fed2"
    DETAIL:  Index row references tuple (1314,1) in relation "cities_light_city".
    HINT:  Values larger than 1/3 of a buffer page cannot be indexed.
    Consider a function index of an MD5 hash of the value, or use full text indexing.

You can fix it by adding the following to your settings.py, this will disable the indexing of the search_names field::
    
    CITIES_LIGHT_INDEX_SEARCH_NAMES = False

Another option is limiting the languages for example to only English and abbreviation, this will fix the issue::
    
    CITIES_LIGHT_TRANSLATION_LANGUAGES = [ 'en',  'abbr']

You want to import only the countries you need, for example France, Belgium and Netherlands, you can do it by adding the following to your settings.py::
    
    CITIES_LIGHT_INCLUDE_COUNTRIES = ['FR', 'BE', 'NL']

You want to import only the cities you need, for example Paris, Brussels and Amsterdam, you can do it by adding the following to your settings.py::
    
    CITIES_LIGHT_INCLUDE_CITY_TYPES = ['PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC', 'PPLF', 'PPLG', 'PPLL', 'PPLR', 'PPLS', 'STLMT',]

You don't want to import the cities and regions and subregions, you can do it by adding the following to your settings.py::
    
    CITIES_LIGHT_INCLUDE_CITY_TYPES = []
    CITIES_LIGHT_INCLUDE_REGION_TYPES = []
    CITIES_LIGHT_INCLUDE_SUBREGION_TYPES = []

Or you can set the sources to empty list:

    CITIES_LIGHT_REGION_SOURCES = []
    CITIES_LIGHT_SUBREGION_SOURCES = []
    CITIES_LIGHT_CITY_SOURCES = []


Development
-----------

Create development virtualenv (you need to have tox installed in your base system)::

    tox -e dev
    source .tox/dev/bin/activate # for linux
    .\.tox\dev\Scripts\activate # for windows

To run the test project, with the folder of the project as the current directory, run::
    
    export PYTHONPATH="${PYTHONPATH}:/app/src"
    docker run  -d postgres -p 5432:5432


Then run the full import::

    test_project/manage.py migrate
    test_project/manage.py cities_light

There are several environment variables which affect project settings (like DB_ENGINE and CI), you can find them all in test_project/settings.py.

For example to change the database engine, you can run::

    export DB_ENGINE=postgresql
    export DB_HOST=192.168.0.118
    export DB_NAME=app
    export DB_USER=postgres
    export DB_PORT=5432

To run the test suite you need to have postgresql or mysql installed with passwordless login, or just use sqlite. Otherwise the tests which try to create/drop database will fail.

Running the full test suite::

    tox

To run the tests in specific environment use the following command::

    tox -e py312-django42-sqlite

And to run one specific test use this one::

    tox -e py312-django42-sqlite -- cities_light/tests/test_form.py::FormTestCase::testCountryFormNameAndContinentAlone

To run it even faster, you can switch to specific tox virtualenv::
    
    export DB_HOST=mysql
    export DB_USER=root
    export DB_PASSWORD=example
    export DB_PORT=3306

    source .tox/py312-django42-sqlite/bin/activate
    CI=True py.test -v --cov cities_light --create-db --strict -r fEsxXw cities_light/tests/test_form.py::FormTestCase::testCountryFormNameAndContinentAlone
    CI=true test_project/manage.py test cities_light.tests.test_form.FormTestCase.testCountryFormNameAndContinentAlone


If you want to build the docs, use the following steps::

    source .tox/dev/bin/activate
    cd docs
    make html

TODOS
-----

- Improve the performance of the import command
- Improve the local development environment with https://tox.wiki/en/legacy/example/devenv.html

Resources
---------

You could subscribe to the mailing list ask questions or just be informed of
package updates.

- `Git graciously hosted
  <https://github.com/yourlabs/django-cities-light/>`_ by `GitHub
  <http://github.com>`_,
- `Documentation graciously hosted
  <http://django-cities-light.rtfd.org>`_ by `RTFD
  <http://rtfd.org>`_,
- `Package graciously hosted
  <https://pypi.org/project/django-cities-light/>`_ by `PyPI
  <https://pypi.org>`_,
- `Continuous integration graciously hosted
  <https://github.com/yourlabs/django-cities-light/actions>`_ by `GitHub Actions
  <https://github.com/features/actions>`_
