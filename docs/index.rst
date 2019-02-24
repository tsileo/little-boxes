.. Little Boxes documentation master file, created by
   sphinx-quickstart on Sat Jun 16 00:44:45 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Little Boxes
============

.. image:: https://img.shields.io/travis/tsileo/little-boxes.svg
  :target: https://travis-ci.org/tsileo/little-boxes

.. image:: https://codecov.io/gh/tsileo/little-boxes/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/tsileo/little-boxes

.. image:: https://img.shields.io/pypi/v/little-boxes.svg
  :target: https://pypi.org/project/little-boxes

.. image:: https://img.shields.io/pypi/pyversions/little-boxes.svg
  :target: https://pypi.org/project/little-boxes

.. image:: https://img.shields.io/pypi/l/little-boxes.svg
  :target: https://github.com/tsileo/little-boxes
 

Tiny `ActivityPub <https://activitypub.rocks/>`_ framework written in Python, both database and server agnostic.


Features
--------

* Database and server agnostic
  * You need to implement a backend that respond to activity side-effects
    * This also mean you're responsible for serving the activities/collections and receiving them
* ActivityStreams helper classes
  * with Outbox/Inbox abstractions
* Content helper using Mardown
  * with helpers for parsing hashtags and linkify content
* Key (RSA) helper
* HTTP signature helper
* JSON-LD signature helper
* Webfinger helper


Project using Little Boxes
--------------------------

* `microblog.pub <http://github.com/tsileo/microblog.pub>`_


Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
