"""Errors raised by this package."""
from typing import Any
from typing import Dict
from typing import Optional


class Error(Exception):
    """Base error for exceptions raised by this package."""


class DropActivityPreProcessError(Error):
    """Raised in `_pre_process_from_inbox` to notify that we don't want to save the message.

    (like when receiving `Announce` with an OStatus link).
    """


class ServerError(Error):
    """HTTP-friendly base error, with a status code, a message and an optional payload."""

    status_code = 400

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        rv = dict(self.payload or {})
        rv["message"] = self.message
        return rv

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__qualname__}({self.message!r}, "
            f"payload={self.payload!r}, status_code={self.status_code})"
        )

    def __str__(self) -> str:  # pragma: no cover
        return self.__repr__()


class ActorBlockedError(ServerError):
    """Raised when an activity from a blocked actor is received."""


class NotFromOutboxError(ServerError):
    """Raised when an activity targets an object from the inbox when an object from the oubox was expected."""


class ActivityNotFoundError(ServerError):
    """Raised when an activity is not found."""

    status_code = 404


class ActivityGoneError(ServerError):
    """Raised when trying to fetch a remote activity that was deleted."""

    status_code = 410


class BadActivityError(ServerError):
    """Raised when an activity could not be parsed/initialized."""


class RecursionLimitExceededError(BadActivityError):
    """Raised when the recursion limit for fetching remote object was exceeded (likely a collection)."""


class UnexpectedActivityTypeError(BadActivityError):
    """Raised when an another activty was expected."""


class ActivityUnavailableError(ServerError):
    """Raises when fetching a remote activity times out."""

    status_code = 503


class NotAnActivityError(ServerError):
    """Raised when no JSON can be decoded.

    Most likely raised when stumbling upon a OStatus notice or failed lookup.
    """
