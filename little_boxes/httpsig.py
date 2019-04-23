"""Implements HTTP signature for Flask requests.

Mastodon instances won't accept requests that are not signed using this scheme.

"""
import base64
import hashlib
import logging
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import urlparse

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from requests.auth import AuthBase

from .activitypub import get_backend
from .activitypub import _has_type
from .errors import ActivityNotFoundError
from .errors import ActivityGoneError
from .key import Key

logger = logging.getLogger(__name__)


def _build_signed_string(
    signed_headers: str, method: str, path: str, headers: Any, body_digest: str
) -> str:
    out = []
    for signed_header in signed_headers.split(" "):
        if signed_header == "(request-target)":
            out.append("(request-target): " + method.lower() + " " + path)
        elif signed_header == "digest":
            out.append("digest: " + body_digest)
        else:
            out.append(signed_header + ": " + headers[signed_header])
    return "\n".join(out)


def _parse_sig_header(val: Optional[str]) -> Optional[Dict[str, str]]:
    if not val:
        return None
    out = {}
    for data in val.split(","):
        k, v = data.split("=", 1)
        out[k] = v[1 : len(v) - 1]  # noqa: black conflict
    return out


def _verify_h(signed_string, signature, pubkey):
    signer = PKCS1_v1_5.new(pubkey)
    digest = SHA256.new()
    digest.update(signed_string.encode("utf-8"))
    return signer.verify(digest, signature)


def _body_digest(body: str) -> str:
    h = hashlib.new("sha256")
    h.update(body)  # type: ignore
    return "SHA-256=" + base64.b64encode(h.digest()).decode("utf-8")


def _get_public_key(key_id: str) -> Key:
    actor = get_backend().fetch_iri(key_id)
    if _has_type(actor["type"], "Key"):
        # The Key is not embedded in the Person
        k = Key(actor["owner"], actor["id"])
        k.load_pub(actor["publicKeyPem"])
    else:
        k = Key(actor["id"], actor["publicKey"]["id"])
        k.load_pub(actor["publicKey"]["publicKeyPem"])

    # Ensure the right key was fetch
    if key_id != k.key_id():
        raise ValueError(
            f"failed to fetch requested key {key_id}: got {actor['publicKey']['id']}"
        )

    return k


def verify_request(method: str, path: str, headers: Any, body: str) -> bool:
    hsig = _parse_sig_header(headers.get("Signature"))
    if not hsig:
        logger.debug("no signature in header")
        return False
    logger.debug(f"hsig={hsig}")
    signed_string = _build_signed_string(
        hsig["headers"], method, path, headers, _body_digest(body)
    )

    try:
        k = _get_public_key(hsig["keyId"])
    except (ActivityGoneError, ActivityNotFoundError):
        logger.debug("cannot get public key")
        return False

    return _verify_h(signed_string, base64.b64decode(hsig["signature"]), k.pubkey)


class HTTPSigAuth(AuthBase):
    """Requests auth plugin for signing requests on the fly."""

    def __init__(self, key: Key) -> None:
        self.key = key

    def __call__(self, r):
        logger.info(f"keyid={self.key.key_id()}")
        host = urlparse(r.url).netloc

        bh = hashlib.new("sha256")
        body = r.body
        try:
            body = r.body.encode("utf-8")
        except AttributeError:
            pass
        bh.update(body)
        bodydigest = "SHA-256=" + base64.b64encode(bh.digest()).decode("utf-8")

        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        r.headers.update({"Digest": bodydigest, "Date": date, "Host": host})

        sigheaders = "(request-target) user-agent host date digest content-type"

        to_be_signed = _build_signed_string(
            sigheaders, r.method, r.path_url, r.headers, bodydigest
        )
        signer = PKCS1_v1_5.new(self.key.privkey)
        digest = SHA256.new()
        digest.update(to_be_signed.encode("utf-8"))
        sig = base64.b64encode(signer.sign(digest))
        sig = sig.decode("utf-8")

        key_id = self.key.key_id()
        headers = {
            "Signature": f'keyId="{key_id}",algorithm="rsa-sha256",headers="{sigheaders}",signature="{sig}"'
        }
        logger.debug(f"signed request headers={headers}")

        r.headers.update(headers)

        return r
