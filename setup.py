#!/usr/bin/env python

from distutils.core import setup
import io
import os

from setuptools import find_packages


here = os.path.abspath(os.path.dirname(__file__))


# Package meta-data.
NAME = "little_boxes"
DESCRIPTION = (
    "Tiny ActivityPub framework written in Python, both database and server agnostic."
)
URL = "https://github.com/tsileo/little-boxes"
EMAIL = "t@a4.io"
AUTHOR = "Thomas Sileo"
REQUIRES_PYTHON = ">=3.6.0"
VERSION = None


REQUIRED = [
    "requests",
    "markdown",
    "bleach",
    "pyld",
    "pycryptodome",
    "html2text",
    "mdx_linkify",
    "regex",
]

DEPENDENCY_LINKS = []


# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, NAME, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


# Import the README and use it as the long-description.
with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()


setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(),
    install_requires=REQUIRED,
    dependency_links=DEPENDENCY_LINKS,
    license="ISC",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
