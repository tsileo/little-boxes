from unittest import mock

import pytest
from little_boxes import urlutils


def test_urlutils_reject_invalid_scheme():
    assert not urlutils.is_url_valid("ftp://localhost:123")


def test_urlutils_reject_localhost():
    assert not urlutils.is_url_valid("http://localhost:8000")


def test_urlutils_reject_private_ip():
    assert not urlutils.is_url_valid("http://192.168.1.10:8000")


@mock.patch("socket.getaddrinfo", return_value=[[0, 1, 2, 3, ["192.168.1.11", None]]])
def test_urlutils_reject_domain_that_resolve_to_private_ip(_):
    assert not urlutils.is_url_valid("http://resolve-to-private.com")


@mock.patch("socket.getaddrinfo", return_value=[[0, 1, 2, 3, ["1.2.3.4", None]]])
def test_urlutils_accept_valid_url(_):
    assert urlutils.is_url_valid("https://microblog.pub")


def test_urlutils_check_url_helper():
    with pytest.raises(urlutils.InvalidURLError):
        urlutils.check_url("http://localhost:5000")
