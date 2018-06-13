import re
from typing import List
from typing import Tuple
from typing import Dict

from bleach.linkifier import Linker
from markdown import markdown

from .webfinger import get_actor_url
from .activitypub import BACKEND
from .activitypub import UninitializedBackendError


def _set_attrs(attrs, new=False):
    attrs[(None, "target")] = "_blank"
    attrs[(None, "class")] = "external"
    attrs[(None, "rel")] = "noopener"
    attrs[(None, "title")] = attrs[(None, "href")]
    return attrs


LINKER = Linker(callbacks=[_set_attrs])
HASHTAG_REGEX = re.compile(r"(#[\d\w\.]+)")
MENTION_REGEX = re.compile(r"@[\d\w_.+-]+@[\d\w-]+\.[\d\w\-.]+")


def hashtagify(content: str) -> Tuple[str, List[Dict[str, str]]]:
    if BACKEND is None:
        raise UninitializedBackendError

    base_url = BACKEND.base_url()
    tags = []
    for hashtag in re.findall(HASHTAG_REGEX, content):
        tag = hashtag[1:]
        link = f'<a href="{base_url}/tags/{tag}" class="mention hashtag" rel="tag">#<span>{tag}</span></a>'
        tags.append(dict(href=f"{base_url}/tags/{tag}", name=hashtag, type="Hashtag"))
        content = content.replace(hashtag, link)
    return content, tags


def mentionify(content: str) -> Tuple[str, List[Dict[str, str]]]:
    if BACKEND is None:
        raise UninitializedBackendError

    tags = []
    for mention in re.findall(MENTION_REGEX, content):
        _, username, domain = mention.split("@")
        actor_url = get_actor_url(mention)
        p = BACKEND.fetch_iri(actor_url)
        tags.append(dict(type="Mention", href=p["id"], name=mention))
        link = f'<span class="h-card"><a href="{p["url"]}" class="u-url mention">@<span>{username}</span></a></span>'
        content = content.replace(mention, link)
    return content, tags


def parse_markdown(content: str) -> Tuple[str, List[Dict[str, str]]]:
    tags = []
    content = LINKER.linkify(content)
    content, hashtag_tags = hashtagify(content)
    tags.extend(hashtag_tags)
    content, mention_tags = mentionify(content)
    tags.extend(mention_tags)
    content = markdown(content)
    return content, tags
