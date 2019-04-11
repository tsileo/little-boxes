from typing import Dict
from typing import List
from typing import Tuple

from markdown import markdown

import regex as re

from .activitypub import get_backend
from .webfinger import get_actor_url


def _set_attrs(attrs, new=False):
    attrs[(None, "target")] = "_blank"
    attrs[(None, "class")] = "external"
    attrs[(None, "rel")] = "noopener"
    attrs[(None, "title")] = attrs[(None, "href")]
    return attrs


HASHTAG_REGEX = re.compile(r"(#[\d\w]+)")
MENTION_REGEX = re.compile(r"@[\d\w_.+-]+@[\d\w-]+\.[\d\w\-.]+")


def hashtagify(content: str) -> Tuple[str, List[Dict[str, str]]]:
    base_url = get_backend().base_url()
    tags = []
    hashtags = re.findall(HASHTAG_REGEX, content)
    hashtags = list(set(hashtags))  # unique tags
    hashtags.sort()
    hashtags.reverse()  # replace longest tag first
    for hashtag in hashtags:
        tag = hashtag[1:]
        link = f'<a href="{base_url}/tags/{tag}" class="mention hashtag" rel="tag">#<span>{tag}</span></a>'
        tags.append(dict(href=f"{base_url}/tags/{tag}", name=hashtag, type="Hashtag"))
        content = content.replace(hashtag, link)
    return content, tags


def mentionify(
    content: str, hide_domain: bool = False
) -> Tuple[str, List[Dict[str, str]]]:
    tags = []
    for mention in re.findall(MENTION_REGEX, content):
        _, username, domain = mention.split("@")
        actor_url = get_actor_url(mention)
        if not actor_url:
            # FIXME(tsileo): raise an error?
            continue
        p = get_backend().fetch_iri(actor_url)
        tags.append(dict(type="Mention", href=p["id"], name=mention))

        d = f"@{domain}"
        if hide_domain:
            d = ""

        link = f'<span class="h-card"><a href="{p["url"]}" class="u-url mention">@<span>{username}</span>{d}</a></span>'
        content = content.replace(mention, link)
    return content, tags


def parse_markdown(content: str) -> Tuple[str, List[Dict[str, str]]]:
    tags = []
    content, hashtag_tags = hashtagify(content)
    tags.extend(hashtag_tags)
    content, mention_tags = mentionify(content)
    tags.extend(mention_tags)
    content = markdown(content, extensions=["mdx_linkify"])
    return content, tags
