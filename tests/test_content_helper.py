import logging

from little_boxes import activitypub as ap
from little_boxes import content_helper
from test_backend import InMemBackend

logging.basicConfig(level=logging.DEBUG)


def test_little_content_helper_simple():
    back = InMemBackend()
    ap.use_backend(back)

    content, tags = content_helper.parse_markdown("hello")
    assert content == "<p>hello</p>"
    assert tags == []
