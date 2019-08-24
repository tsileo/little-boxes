import abc
import binascii
import json
import os
import typing
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests

from .__version__ import __version__
from .collection import parse_collection
from .errors import ActivityGoneError
from .errors import ActivityNotFoundError
from .errors import ActivityUnavailableError
from .errors import NotAnActivityError
from .errors import RemoteServerUnavailableError
from .urlutils import URLLookupFailedError
from .urlutils import check_url as check_url

if typing.TYPE_CHECKING:
    from little_boxes import activitypub as ap  # noqa: type checking


class Backend(abc.ABC):
    def ap_context(self) -> Any:
        return "https://www.w3.org/ns/activitystreams"

    @abc.abstractmethod
    def base_url(self) -> str:
        pass  # pragma: no cover

    def debug_mode(self) -> bool:
        """Should be overidded to return `True` in order to enable the debug mode."""
        return False

    def check_url(self, url: str) -> None:
        check_url(url, debug=self.debug_mode())

    def user_agent(self) -> str:
        return f"Little Boxes/{__version__}; +http://github.com/tsileo/little-boxes"

    def random_object_id(self) -> str:
        """Generates a random object ID."""
        return binascii.hexlify(os.urandom(8)).decode("utf-8")

    def fetch_json(self, url: str, **kwargs):
        self.check_url(url)
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": self.user_agent(), "Accept": "application/json"},
                **kwargs,
                timeout=10,
                allow_redirects=True,
            )
        except requests.RequestException as err:
            raise RemoteServerUnavailableError(
                f"failed to fetch {url} as JSON: {err!r}"
            )

        resp.raise_for_status()

        return resp

    def parse_collection(
        self, payload: Optional[Dict[str, Any]] = None, url: Optional[str] = None
    ) -> List[str]:
        return parse_collection(payload=payload, url=url, fetcher=self.fetch_iri)

    def extra_inboxes(self) -> List[str]:
        """Allows to define inboxes that will be part of of the recipient for every activity."""
        return []

    def is_from_outbox(
        self, as_actor: "ap.Person", activity: "ap.BaseActivity"
    ) -> bool:
        return activity.get_actor().id == as_actor.id

    def fetch_iri(self, iri: str, **kwargs) -> "ap.ObjectType":  # pragma: no cover
        if not iri.startswith("http"):
            raise NotAnActivityError(f"{iri} is not a valid IRI")

        try:
            self.check_url(iri)
        except URLLookupFailedError:
            # The IRI is inaccessible
            raise ActivityUnavailableError(f"unable to fetch {iri}, url lookup failed")

        try:
            resp = requests.get(
                iri,
                headers={
                    "User-Agent": self.user_agent(),
                    "Accept": "application/activity+json",
                },
                timeout=10,
                allow_redirects=True,
                **kwargs,
            )
        except requests.RequestException as err:
            raise RemoteServerUnavailableError(f"unable to fetch {iri}: {err!r}")

        if resp.status_code == 404:
            raise ActivityNotFoundError(f"{iri} is not found")
        elif resp.status_code == 410:
            raise ActivityGoneError(f"{iri} is gone")
        elif resp.status_code in [403, 500, 502, 503]:
            raise ActivityUnavailableError(
                f"unable to fetch {iri}, server error ({resp.status_code})"
            )
        elif resp.status_code == 406:
            # The resource does not have an AP representation
            raise NotAnActivityError(f"request failed with 406 Not Acceptable")

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise ActivityUnavailableError(
                f"unable to fetch {iri}, server error ({resp.status_code})"
            )

        try:
            out = resp.json()
        except (json.JSONDecodeError, ValueError):
            # TODO(tsileo): a special error type?
            raise NotAnActivityError(f"{iri} is not JSON")

        return out
