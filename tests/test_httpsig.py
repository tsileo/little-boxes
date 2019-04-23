import logging

import requests
from little_boxes import activitypub as ap
from little_boxes import httpsig
from little_boxes.key import Key

import httpretty
from test_backend import InMemBackend

logging.basicConfig(level=logging.DEBUG)


@httpretty.activate
def test_httpsig():
    back = InMemBackend()
    ap.use_backend(back)

    k = Key("https://lol.com", "https://lol.com#lol")
    k.new()
    back.FETCH_MOCK["https://lol.com#lol"] = {
        "publicKey": k.to_dict(),
        "id": "https://lol.com",
        "type": "Person",
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


@httpretty.activate
def test_httpsig_key():
    back = InMemBackend()
    ap.use_backend(back)

    k = Key("https://lol.com", "https://lol.com/key/lol")
    k.new()
    back.FETCH_MOCK["https://lol.com/key/lol"] = k.to_dict()

    httpretty.register_uri(httpretty.POST, "https://remote-instance.com", body="ok")

    auth = httpsig.HTTPSigAuth(k)
    resp = requests.post("https://remote-instance.com", json={"ok": 1}, auth=auth)

    assert httpsig.verify_request(
        resp.request.method,
        resp.request.path_url,
        resp.request.headers,
        resp.request.body,
    )
