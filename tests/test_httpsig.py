import logging

import httpretty
import requests

from little_boxes import activitypub as ap
from little_boxes import httpsig
from little_boxes.key import Key
from test_backend import InMemBackend

logging.basicConfig(level=logging.DEBUG)


@httpretty.activate
def test_httpsig():
    back = InMemBackend()
    ap.use_backend(back)

    k = Key("https://lol.com")
    k.new()
    back.FETCH_MOCK["https://lol.com#main-key"] = {
        "publicKey": k.to_dict(),
        "id": "https://lol.com",
    }

    httpretty.register_uri(httpretty.POST, "https://remote-instance.com", body="ok")

    auth = httpsig.HTTPSigAuth(k)
    resp = requests.post("https://remote-instance.com", json={"ok": 1}, auth=auth)

    assert httpsig.verify_request(
        resp.request.method,
        resp.request.path_url,
        resp.request.headers,
        resp.request.body,
    )
