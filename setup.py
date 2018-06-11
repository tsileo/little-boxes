#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

setup(
    name='Little Boxes',
    version='0.1.0',
    description='Tiny ActivityPub framework written in Python, both database and server agnostic.',
    author='Thomas Sileo',
    author_email='t@a4.io',
    url='https://github.com/tsileo/little-boxes',
    packages=find_packages(),
)
