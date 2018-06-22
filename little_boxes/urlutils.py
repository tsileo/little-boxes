import ipaddress
import logging
import os
import socket
from typing import Dict
from urllib.parse import urlparse

from . import strtobool
from .errors import Error

logger = logging.getLogger(__name__)


_CACHE: Dict[str, bool] = {}


class InvalidURLError(Error):
    pass


def is_url_valid(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return False

    # XXX in debug mode, we want to allow requests to localhost to test the federation with local instances
    debug_mode = strtobool(os.getenv("MICROBLOGPUB_DEBUG", "false"))
    if debug_mode:  # pragma: no cover
        return True

    if parsed.hostname in ["localhost"]:
        return False

    if _CACHE.get(parsed.hostname, False):
        return True

    try:
        ip_address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        try:
            ip_address = socket.getaddrinfo(parsed.hostname, parsed.port or 80)[0][4][0]
            logger.debug(f"dns lookup: {parsed.hostname} -> {ip_address}")
        except socket.gaierror:
            logger.exception(f"failed to lookup url {url}")
            _CACHE[parsed.hostname] = False
            return False

    logger.debug(f"{ip_address}")

    if ipaddress.ip_address(ip_address).is_private:
        logger.info(f"rejecting private URL {url}")
        _CACHE[parsed.hostname] = False
        return False

    _CACHE[parsed.hostname] = True
    return True


def check_url(url: str) -> None:
    logger.debug(f"check_url {url}")
    if not is_url_valid(url):
        raise InvalidURLError(f'"{url}" is invalid')

    return None
