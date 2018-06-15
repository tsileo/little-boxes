from unittest import mock
import logging
import json

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
@httpretty.activate
def test_webfinger(_):
    # FIXME(tsileo): it should try https first
    httpretty.register_uri(
        httpretty.GET,
        "http://microblog.pub/.well-known/webfinger",
        body=json.dumps(_WEBFINGER_RESP),
    )
    data = webfinger.webfinger("@dev@microblog.pub")
    assert data == _WEBFINGER_RESP

    assert webfinger.get_actor_url("@dev@microblog.pub") == "https://microblog.pub"
    assert (
        webfinger.get_remote_follow_template("@dev@microblog.pub")
        == "https://microblog.pub/authorize_follow?profile={uri}"
    )
