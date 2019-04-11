import logging
from unittest import mock

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


def test_little_content_helper_linkify():
    back = InMemBackend()
    ap.use_backend(back)

    content, tags = content_helper.parse_markdown("hello https://google.com")
    assert content.startswith("<p>hello <a")
    assert "https://google.com" in content
    assert tags == []


@mock.patch(
    "little_boxes.content_helper.get_actor_url", return_value="https://microblog.pub"
)
def test_little_content_helper_mention(_):
    back = InMemBackend()
    ap.use_backend(back)
    back.FETCH_MOCK["https://microblog.pub"] = {
        "id": "https://microblog.pub",
        "url": "https://microblog.pub",
    }

    content, tags = content_helper.parse_markdown("hello @dev@microblog.pub")
    assert content == (
        '<p>hello <span class="h-card"><a href="https://microblog.pub" class="u-url mention">@<span>dev</span>'
        "@microblog.pub</a></span></p>"
    )
    assert tags == [
        {
            "href": "https://microblog.pub",
            "name": "@dev@microblog.pub",
            "type": "Mention",
        }
    ]


@mock.patch(
    "little_boxes.content_helper.get_actor_url", return_value="https://microblog.pub"
)
def test_little_content_helper_tag(_):
    back = InMemBackend()
    ap.use_backend(back)

    content, tags = content_helper.parse_markdown("hello #activitypub")
    base_url = back.base_url()
    assert content == (
        f'<p>hello <a href="{base_url}/tags/activitypub" class="mention hashtag" rel="tag">#'
        f"<span>activitypub</span></a></p>"
    )
    assert tags == [
        {
            "href": f"{base_url}/tags/activitypub",
            "name": "#activitypub",
            "type": "Hashtag",
        }
    ]
