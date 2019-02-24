import json
import logging
from unittest import mock

import pytest
from little_boxes import urlutils
from little_boxes import webfinger

import httpretty

logging.basicConfig(level=logging.DEBUG)


_WEBFINGER_RESP = {
    "aliases": ["https://microblog.pub"],
    "links": [
        {
            "href": "https://microblog.pub",
            "rel": "http://webfinger.net/rel/profile-page",
            "type": "text/html",
        },
        {
            "href": "https://microblog.pub",
            "rel": "self",
            "type": "application/activity+json",
        },
        {
            "rel": "http://ostatus.org/schema/1.0/subscribe",
            "template": "https://microblog.pub/authorize_follow?profile={uri}",
        },
    ],
    "subject": "acct:dev@microblog.pub",
}


@mock.patch("little_boxes.webfinger.check_url", return_value=None)
@mock.patch("little_boxes.backend.check_url", return_value=None)
@httpretty.activate
def test_webfinger(_, _1):
    # FIXME(tsileo): it should try https first
    httpretty.register_uri(
        httpretty.GET,
        "https://microblog.pub/.well-known/webfinger",
        body=json.dumps(_WEBFINGER_RESP),
    )
    data = webfinger.webfinger("@dev@microblog.pub")
    assert data == _WEBFINGER_RESP

    assert webfinger.get_actor_url("@dev@microblog.pub") == "https://microblog.pub"
    assert (
        webfinger.get_remote_follow_template("@dev@microblog.pub")
        == "https://microblog.pub/authorize_follow?profile={uri}"
    )


def test_webfinger_invalid_url():
    with pytest.raises(urlutils.InvalidURLError):
        webfinger.webfinger("@dev@localhost:8080")
