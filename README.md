# Little Boxes


<a href="https://travis-ci.org/tsileo/little-boxes"><img src="https://travis-ci.org/tsileo/little-boxes.svg?branch=master" alt="Build Status"></a>
<a href="https://github.com/tsileo/little-boxes/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-ISC-blue.svg?style=flat" alt="License"></a>

Tiny [ActivityPub](https://activitypub.rocks/) framework written in Python, both database and server agnostic.

## Getting Started

```python
from little_boxes import activitypub as ap

from mydb import db_client


class MyBackend(BaseBackend):

    def __init__(self, db_connection):
        self.db_connection = db_connection    

    def inbox_new(self, as_actor, activity):
        # Save activity as "as_actor"
        # [...]

    def post_to_remote_inbox(self, as_actor, payload, recipient):
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
