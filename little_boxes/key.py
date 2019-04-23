import base64
from typing import Any
from typing import Dict
from typing import Optional

from Crypto.PublicKey import RSA
from Crypto.Util import number


class Key(object):
    DEFAULT_KEY_SIZE = 2048

    def __init__(self, owner: str, id_: Optional[str] = None) -> None:
        self.owner = owner
        self.privkey_pem: Optional[str] = None
        self.pubkey_pem: Optional[str] = None
        self.privkey: Optional[RSA.RsaKey] = None
        self.pubkey: Optional[RSA.RsaKey] = None
        self.id_ = id_

    def load_pub(self, pubkey_pem: str) -> None:
        self.pubkey_pem = pubkey_pem
        self.pubkey = RSA.importKey(pubkey_pem)

    def load(self, privkey_pem: str) -> None:
        self.privkey_pem = privkey_pem
        self.privkey = RSA.importKey(self.privkey_pem)
        self.pubkey_pem = self.privkey.publickey().exportKey("PEM").decode("utf-8")

    def new(self) -> None:
        k = RSA.generate(self.DEFAULT_KEY_SIZE)
        self.privkey_pem = k.exportKey("PEM").decode("utf-8")
        self.pubkey_pem = k.publickey().exportKey("PEM").decode("utf-8")
        self.privkey = k

    def key_id(self) -> str:
        return self.id_ or f"{self.owner}#main-key"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.key_id(),
            "owner": self.owner,
            "publicKeyPem": self.pubkey_pem,
            "type": "Key",
        }

    @classmethod
    def from_dict(cls, data):
        try:
            k = cls(data["owner"], data["id"])
            k.load_pub(data["publicKeyPem"])
        except KeyError:
            raise ValueError(f"bad key data {data!r}")
        return k

    def to_magic_key(self) -> str:
        mod = base64.urlsafe_b64encode(
            number.long_to_bytes(self.privkey.n)  # type: ignore
        ).decode("utf-8")
        pubexp = base64.urlsafe_b64encode(
            number.long_to_bytes(self.privkey.e)  # type: ignore
        ).decode("utf-8")
        return f"data:application/magic-public-key,RSA.{mod}.{pubexp}"
