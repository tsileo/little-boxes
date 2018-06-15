import logging

from little_boxes import webfinger

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


def test_webfinger():
    data = webfinger.webfinger("@dev@microblog.pub")

    assert data == _WEBFINGER_RESP
