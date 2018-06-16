import logging

import pytest

from little_boxes import activitypub as ap
from little_boxes.collection import parse_collection
from little_boxes.errors import RecursionLimitExceededError
from little_boxes.errors import UnexpectedActivityTypeError
from test_backend import InMemBackend

logging.basicConfig(level=logging.DEBUG)


def test_empty_collection():
    back = InMemBackend()
    ap.use_backend(back)

    back.FETCH_MOCK["https://lol.com"] = {
        "type": "Collection",
        "items": [],
        "id": "https://lol.com",
    }

    out = parse_collection(url="https://lol.com", fetcher=back.fetch_iri)
    assert out == []


def test_recursive_collection_limit():
    back = InMemBackend()
    ap.use_backend(back)

    back.FETCH_MOCK["https://lol.com"] = {
        "type": "Collection",
        "first": "https://lol.com",
        "id": "https://lol.com",
    }

    with pytest.raises(RecursionLimitExceededError):
        parse_collection(url="https://lol.com", fetcher=back.fetch_iri)


def test_unexpected_activity_type():
    back = InMemBackend()
    ap.use_backend(back)

    back.FETCH_MOCK["https://lol.com"] = {"type": "Actor", "id": "https://lol.com"}

    with pytest.raises(UnexpectedActivityTypeError):
        parse_collection(url="https://lol.com", fetcher=back.fetch_iri)


def test_collection():
    back = InMemBackend()
    ap.use_backend(back)

    back.FETCH_MOCK["https://lol.com"] = {
        "type": "Collection",
        "first": "https://lol.com/page1",
        "id": "https://lol.com",
    }
    back.FETCH_MOCK["https://lol.com/page1"] = {
        "type": "CollectionPage",
        "id": "https://lol.com/page1",
        "items": [1, 2, 3],
    }

    out = parse_collection(url="https://lol.com", fetcher=back.fetch_iri)
    assert out == [1, 2, 3]


def test_ordered_collection():
    back = InMemBackend()
    ap.use_backend(back)

    back.FETCH_MOCK["https://lol.com"] = {
        "type": "OrderedCollection",
        "first": {
            "type": "OrderedCollectionPage",
            "id": "https://lol.com/page1",
            "orderedItems": [1, 2, 3],
            "next": "https://lol.com/page2",
        },
        "id": "https://lol.com",
    }
    back.FETCH_MOCK["https://lol.com/page2"] = {
        "type": "OrderedCollectionPage",
        "id": "https://lol.com/page2",
        "orderedItems": [4, 5, 6],
    }

    out = parse_collection(url="https://lol.com", fetcher=back.fetch_iri)
    assert out == [1, 2, 3, 4, 5, 6]
