import binascii
import os
import json
from typing import Optional
from typing import List

from little_boxes.backend import Backend
import little_boxes.activitypub as ap


def track_call(f):
    """Method decorator used to track the events fired during tests."""
    fname = f.__name__

    def wrapper(*args, **kwargs):
        args[0]._METHOD_CALLS[args[1].id].append((fname, args, kwargs))
        return f(*args, **kwargs)

    return wrapper


class InMemBackend(Backend):
    """In-memory backend meant to be used for the test suite."""

    DB = {}
    USERS = {}
    FETCH_MOCK = {}
    INBOX_IDX = {}
    OUTBOX_IDX = {}
    FOLLOWERS = {}
    FOLLOWING = {}

    # For tests purposes only
    _METHOD_CALLS = {}

    def called_methods(self, p: ap.Person) -> List[str]:
        data = list(self._METHOD_CALLS[p.id])
        self._METHOD_CALLS[p.id] = []
        return data

    def assert_called_methods(self, p: ap.Person, *asserts) -> List[str]:
        calls = self.called_methods(p)
        for i, assert_data in enumerate(asserts):
            if len(calls) < i + 1:
                raise ValueError(f"no methods called at step #{i}")
            error_msg, name, *funcs = assert_data
            if name != calls[i][0]:
                raise ValueError(
                    f"expected method {name} to be called at step #{i}, but got {calls[i][0]}"
                )
            if len(funcs) < len(calls[i][1]) - 1:
                raise ValueError(f"args left unchecked for method {name} at step #{i}")
            for z, f in enumerate(funcs):
                if len(calls[i][1]) < z + 2:  # XXX(tsileo): 0 will be self
                    raise ValueError(f"method {name} has no args at index {z}")
                try:
                    f(calls[i][1][z + 1])
                except AssertionError as ae:
                    ae.args = ((error_msg),)
                    raise ae

        if len(asserts) < len(calls):
            raise ValueError(
                f"expecting {len(calls)} assertion, only got {len(asserts)},"
                f"leftover: {calls[len(asserts):]!r}"
            )

        return calls

    def random_object_id(self) -> str:
        """Generates a random object ID."""
        return binascii.hexlify(os.urandom(8)).decode("utf-8")

    def setup_actor(self, name, pusername):
        """Create a new actor in this backend."""
        p = ap.Person(
            name=name,
            preferredUsername=pusername,
            summary="Hello",
            id=f"https://lol.com/{pusername}",
            inbox=f"https://lol.com/{pusername}/inbox",
            followers=f"https://lol.com/{pusername}/followers",
            following=f"https://lol.com/{pusername}/following",
        )

        self.USERS[p.preferredUsername] = p
        self.DB[p.id] = {"inbox": [], "outbox": []}
        self.INBOX_IDX[p.id] = {}
        self.OUTBOX_IDX[p.id] = {}
        self.FOLLOWERS[p.id] = []
        self.FOLLOWING[p.id] = []
        self.FETCH_MOCK[p.id] = p.to_dict()
        self._METHOD_CALLS[p.id] = []
        return p

    def fetch_iri(self, iri: str) -> ap.ObjectType:
        if iri.endswith("/followers"):
            data = self.FOLLOWERS[iri.replace("/followers", "")]
            return {
                "id": iri,
                "type": ap.ActivityType.ORDERED_COLLECTION.value,
                "totalItems": len(data),
                "orderedItems": data,
            }
        if iri.endswith("/following"):
            data = self.FOLLOWING[iri.replace("/following", "")]
            return {
                "id": iri,
                "type": ap.ActivityType.ORDERED_COLLECTION.value,
                "totalItems": len(data),
                "orderedItems": data,
            }
        return self.FETCH_MOCK[iri]

    def get_user(self, username: str) -> ap.Person:
        if username in self.USERS:
            return self.USERS[username]
        else:
            raise ValueError(f"bad username {username}")

    @track_call
    def outbox_is_blocked(self, as_actor: ap.Person, actor_id: str) -> bool:
        """Returns True if `as_actor` has blocked `actor_id`."""
        for activity in self.DB[as_actor.id]["outbox"]:
            if activity.ACTIVITY_TYPE == ap.ActivityType.BLOCK:
                return True
        return False

    def inbox_get_by_iri(
        self, as_actor: ap.Person, iri: str
    ) -> Optional[ap.BaseActivity]:
        for activity in self.DB[as_actor.id]["inbox"]:
            if activity.id == iri:
                return activity

        return None

    @track_call
    def inbox_new(self, as_actor: ap.Person, activity: ap.BaseActivity) -> None:
        if activity.id in self.INBOX_IDX[as_actor.id]:
            return
        self.DB[as_actor.id]["inbox"].append(activity)
        self.INBOX_IDX[as_actor.id][activity.id] = activity

    def activity_url(self, obj_id: str) -> str:
        # from the random hex ID
        return f"todo/{obj_id}"

    @track_call
    def outbox_new(self, as_actor: ap.Person, activity: ap.BaseActivity) -> None:
        print(f"saving {activity!r} to DB")
        actor_id = activity.get_actor().id
        if activity.id in self.OUTBOX_IDX[actor_id]:
            return
        self.DB[actor_id]["outbox"].append(activity)
        self.OUTBOX_IDX[actor_id][activity.id] = activity
        self.FETCH_MOCK[activity.id] = activity.to_dict()
        if isinstance(activity, ap.Create):
            self.FETCH_MOCK[activity.get_object().id] = activity.get_object().to_dict()

    @track_call
    def new_follower(self, as_actor: ap.Person, follow: ap.Follow) -> None:
        self.FOLLOWERS[follow.get_object().id].append(follow.get_actor().id)

    @track_call
    def undo_new_follower(self, as_actor: ap.Person, follow: ap.Follow) -> None:
        self.FOLLOWERS[follow.get_object().id].remove(follow.get_actor().id)

    @track_call
    def new_following(self, as_actor: ap.Person, follow: ap.Follow) -> None:
        print(f"new following {follow!r}")
        self.FOLLOWING[as_actor.id].append(follow.get_object().id)

    @track_call
    def undo_new_following(self, as_actor: ap.Person, follow: ap.Follow) -> None:
        self.FOLLOWING[as_actor.id].remove(follow.get_object().id)

    def followers(self, as_actor: ap.Person) -> List[str]:
        return self.FOLLOWERS[as_actor.id]

    def following(self, as_actor: ap.Person) -> List[str]:
        return self.FOLLOWING[as_actor.id]

    @track_call
    def post_to_remote_inbox(
        self, as_actor: ap.Person, payload_encoded: str, recp: str
    ) -> None:
        payload = json.loads(payload_encoded)
        print(f"post_to_remote_inbox {payload} {recp}")
        act = ap.parse_activity(payload)
        as_actor = ap.parse_activity(self.fetch_iri(recp.replace("/inbox", "")))
        act.process_from_inbox(as_actor)

    def is_from_outbox(self, activity: ap.BaseActivity) -> bool:
        # return as_actor.id == activity.get_actor().id
        return True  # FIXME(tsileo): implement this

    def inbox_like(self, activity: ap.Like) -> None:
        pass

    def inbox_undo_like(self, activity: ap.Like) -> None:
        pass

    def outbox_like(self, activity: ap.Like) -> None:
        pass

    def outbox_undo_like(self, activity: ap.Like) -> None:
        pass

    def inbox_announce(self, activity: ap.Announce) -> None:
        pass

    def inbox_undo_announce(self, activity: ap.Announce) -> None:
        pass

    def outbox_announce(self, activity: ap.Announce) -> None:
        pass

    def outbox_undo_announce(self, activity: ap.Announce) -> None:
        pass

    @track_call
    def inbox_delete(self, as_actor: ap.Person, activity: ap.Delete) -> None:
        pass

    @track_call
    def outbox_delete(self, as_actor: ap.Person, activity: ap.Delete) -> None:
        pass

    def inbox_update(self, as_actor: ap.Person, activity: ap.Update) -> None:
        pass

    def outbox_update(self, activity: ap.Update) -> None:
        pass

    @track_call
    def inbox_create(self, as_actor: ap.Person, activity: ap.Create) -> None:
        pass

    @track_call
    def outbox_create(self, as_actor: ap.Person, activity: ap.Create) -> None:
        pass
