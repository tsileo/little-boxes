# Little Boxes

<a href="https://travis-ci.org/tsileo/little-boxes"><img src="https://travis-ci.org/tsileo/little-boxes.svg?branch=master" alt="Build Status"></a>
<img src="https://img.shields.io/pypi/pyversions/little-boxes.svg" />
<a href="https://github.com/tsileo/little-boxes/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-ISC-red.svg?style=flat" alt="License"></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

Tiny [ActivityPub](https://activitypub.rocks/) framework written in Python, both database and server agnostic.

**Still in early development, and not published on PyPI yet.**


## Features

 - Database and server agnostic
   - You need to implement a backend that respond to activiy side-effects
   - This also need you're responsible for serving the activities/collections and receiving them
 - ActivityStreams helper classes
   - with Outbox/Inbox abstractions
 - Content helper using Mardown
   - with helpers for parsing hashtags and linkify content
 - Key (RSA) helper
 - HTTP signature helper
 - JSON-LD signature helper
 - Webfinger helper


## Getting Started

```python
from little_boxes import activitypub as ap

from mydb import db_client


class MyBackend(ap.Backend):

    def __init__(self, db_connection):
        self.db_connection = db_connection    

    def inbox_new(self, as_actor: ap.Person, activity: ap.Activity) -> None:
        # Save activity as "as_actor"
        # [...]

    def post_to_remote_inbox(self, as_actor: ap.Person, payload: ap.ObjectType, recipient: str) -> None:
        # Send the activity to the remote actor
        # [...]


db_con = db_client()
my_backend = MyBackend(db_con)

ap.use_backend(my_backend)

me = ap.Person({})  # Init an actor
outbox = ap.Outbox(me)

follow = ap.Follow(actor=me, object='http://iri-i-want-follow')
outbox.post(follow)
```


## Projects using Little Boxes

 - [microblog.pub](http://github.com/tsileo/microblog.pub) (using MongoDB as a backend)


## Contributions

TODO: document Mypy, flake8 and black.

PRs are welcome, please open an issue to start a discussion before your start any work.


## License

ISC, see the LICENSE file.
