import json
import logging

from little_boxes import linked_data_sig
from little_boxes.key import Key

logging.basicConfig(level=logging.DEBUG)


DOC = """{"type": "Create", "actor": "https://microblog.pub", "object": {"type": "Note", "sensitive": false, "cc": ["https://microblog.pub/followers"], "to": ["https://www.w3.org/ns/activitystreams#Public"], "content": "<p>Hello world!</p>", "tag": [], "source": {"mediaType": "text/markdown", "content": "Hello world!"}, "attributedTo": "https://microblog.pub", "published": "2018-05-21T15:51:59Z", "id": "https://microblog.pub/outbox/988179f13c78b3a7/activity", "url": "https://microblog.pub/note/988179f13c78b3a7", "replies": {"type": "OrderedCollection", "totalItems": 0, "first": "https://microblog.pub/outbox/988179f13c78b3a7/replies?page=first", "id": "https://microblog.pub/outbox/988179f13c78b3a7/replies"}, "likes": {"type": "OrderedCollection", "totalItems": 2, "first": "https://microblog.pub/outbox/988179f13c78b3a7/likes?page=first", "id": "https://microblog.pub/outbox/988179f13c78b3a7/likes"}, "shares": {"type": "OrderedCollection", "totalItems": 3, "first": "https://microblog.pub/outbox/988179f13c78b3a7/shares?page=first", "id": "https://microblog.pub/outbox/988179f13c78b3a7/shares"}}, "@context": ["https://www.w3.org/ns/activitystreams", "https://w3id.org/security/v1", {"Hashtag": "as:Hashtag", "sensitive": "as:sensitive"}], "published": "2018-05-21T15:51:59Z", "to": ["https://www.w3.org/ns/activitystreams#Public"], "cc": ["https://microblog.pub/followers"], "id": "https://microblog.pub/outbox/988179f13c78b3a7"}"""  # noqa: E501


def test_linked_data_sig():
    doc = json.loads(DOC)

    k = Key("https://lol.com")
    k.new()

    linked_data_sig.generate_signature(doc, k)
    assert linked_data_sig.verify_signature(doc, k)
