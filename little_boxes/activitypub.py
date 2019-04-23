"""Core ActivityPub classes."""
import logging
import weakref
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from .backend import Backend
from .errors import ActivityGoneError
from .errors import ActivityNotFoundError
from .errors import ActivityUnavailableError
from .errors import BadActivityError
from .errors import NotAnActivityError
from .errors import Error
from .errors import UnexpectedActivityTypeError
from .key import Key

logger = logging.getLogger(__name__)

UninitializedBackendError = Error("a backend must be initialized")

# Helper/shortcut for typing
ObjectType = Dict[str, Any]
ActorType = Union["Person", "Application", "Group", "Organization", "Service"]
ObjectOrIDType = Union[str, ObjectType]

CTX_AS = "https://www.w3.org/ns/activitystreams"
CTX_SECURITY = "https://w3id.org/security/v1"
AS_PUBLIC = "https://www.w3.org/ns/activitystreams#Public"

DEFAULT_CTX = COLLECTION_CTX = [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
        # AS ext
        "Hashtag": "as:Hashtag",
        "sensitive": "as:sensitive",
        "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
        # toot
        "toot": "http://joinmastodon.org/ns#",
        "featured": "toot:featured",
        # schema
        "schema": "http://schema.org#",
        "PropertyValue": "schema:PropertyValue",
        "value": "schema:value",
    },
]

# Will be used to keep track of all the defined activities
_ACTIVITY_CLS: Dict["ActivityType", Type["BaseActivity"]] = {}

BACKEND: Optional[Backend] = None


def get_backend() -> Backend:
    if BACKEND is None:
        raise UninitializedBackendError
    return BACKEND


def use_backend(backend_instance):
    global BACKEND
    BACKEND = backend_instance


def format_datetime(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be tz aware")

    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


class ActivityType(Enum):
    """Supported activity `type`."""

    ANNOUNCE = "Announce"
    BLOCK = "Block"
    LIKE = "Like"
    CREATE = "Create"
    UPDATE = "Update"

    ORDERED_COLLECTION = "OrderedCollection"
    ORDERED_COLLECTION_PAGE = "OrderedCollectionPage"
    COLLECTION_PAGE = "CollectionPage"
    COLLECTION = "Collection"

    NOTE = "Note"
    ARTICLE = "Article"
    VIDEO = "Video"
    AUDIO = "Audio"
    DOCUMENT = "Document"

    ACCEPT = "Accept"
    REJECT = "Reject"
    FOLLOW = "Follow"

    DELETE = "Delete"
    UNDO = "Undo"

    IMAGE = "Image"
    TOMBSTONE = "Tombstone"

    # Actor types
    PERSON = "Person"
    APPLICATION = "Application"
    GROUP = "Group"
    ORGANIZATION = "Organization"
    SERVICE = "Service"

    # Others
    MENTION = "Mention"

    # Mastodon specific?
    QUESTION = "Question"

    # Used by Prismo
    PAGE = "Page"

    # Misskey uses standalone Key object
    KEY = "Key"


ACTOR_TYPES = [
    ActivityType.PERSON,
    ActivityType.APPLICATION,
    ActivityType.GROUP,
    ActivityType.ORGANIZATION,
    ActivityType.SERVICE,
    ActivityType.QUESTION,  # Mastodon notoft the end of a question with an update from that question
]

CREATE_TYPES = [
    ActivityType.NOTE,
    ActivityType.ARTICLE,
    ActivityType.VIDEO,
    ActivityType.AUDIO,
    ActivityType.QUESTION,
    ActivityType.DOCUMENT,
    ActivityType.PAGE,
]

COLLECTION_TYPES = [ActivityType.COLLECTION, ActivityType.ORDERED_COLLECTION]


def parse_activity(
    payload: ObjectType, expected: Optional[ActivityType] = None
) -> "BaseActivity":
    if "type" not in payload:
        raise BadActivityError(f"the payload has no type: {payload!r}")

    t = ActivityType(_to_list(payload["type"])[0])

    if expected and t != expected:
        raise UnexpectedActivityTypeError(
            f'expected a {expected.name} activity, got a {payload["type"]}: {payload}'
        )

    if t not in _ACTIVITY_CLS:
        raise BadActivityError(
            f'unsupported activity type {payload["type"]}: {payload}'
        )

    activity = _ACTIVITY_CLS[t](**payload)

    return activity


def _to_list(data: Union[List[Any], Any]) -> List[Any]:
    """Helper to convert fields that can be either an object or a list of objects to a
    list of object."""
    if isinstance(data, list):
        return data
    return [data]


def clean_activity(activity: ObjectType) -> Dict[str, Any]:
    """Clean the activity before rendering it.
     - Remove the hidden bco and bcc field
    """
    for field in ["bto", "bcc", "source"]:
        if field in activity:
            del activity[field]
        if activity["type"] == "Create" and field in activity["object"]:
            del activity["object"][field]
    return activity


def _get_actor_id(actor: ObjectOrIDType) -> str:
    """Helper for retrieving an actor `id`."""
    if isinstance(actor, dict):
        return actor["id"]
    return actor


def _get_id(obj) -> Optional[str]:
    if obj is None:
        return None
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, dict):
        try:
            return obj["id"]
        except KeyError:
            raise ValueError(f"object is missing ID: {obj!r}")
    else:
        raise ValueError(f"unexpected object: {obj!r}")


def _has_type(
    obj_type: Union[str, List[str]],
    _types: Union[ActivityType, str, List[Union[ActivityType, str]]],
):
    """Returns `True` if one of `obj_type` equals one of `_types`."""
    types_str = [
        _type.value if isinstance(_type, ActivityType) else _type
        for _type in _to_list(_types)
    ]
    for _type in _to_list(obj_type):
        if _type in types_str:
            return True
    return False


class _ActivityMeta(type):
    """Metaclass for keeping track of subclass."""

    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)

        # Ensure the class has an activity type defined
        if name != "BaseActivity" and not cls.ACTIVITY_TYPE:
            raise ValueError(f"class {name} has no ACTIVITY_TYPE")

        # Register it
        _ACTIVITY_CLS[cls.ACTIVITY_TYPE] = cls
        return cls


class BaseActivity(object, metaclass=_ActivityMeta):
    """Base class for ActivityPub activities."""

    ACTIVITY_TYPE: Optional[
        ActivityType
    ] = None  # the ActivityTypeEnum the class will represent
    OBJECT_REQUIRED = False  # Whether the object field is required or note
    ALLOWED_OBJECT_TYPES: List[ActivityType] = []
    ACTOR_REQUIRED = (
        True
    )  # Most of the object requires an actor, so this flag in on by default

    def __init__(self, **kwargs) -> None:  # noqa: C901
        if not self.ACTIVITY_TYPE:
            raise Error("should never happen")

        # Initialize the dict that will contains all the activity fields
        self._data: Dict[str, Any] = {}

        if not kwargs.get("type"):
            self._data["type"] = self.ACTIVITY_TYPE.value
        else:
            atype = kwargs.pop("type")
            if self.ACTIVITY_TYPE.value not in _to_list(atype):
                raise UnexpectedActivityTypeError(
                    f"Expect the type to be {self.ACTIVITY_TYPE.value!r}"
                )
            self._data["type"] = atype

        logger.debug(f"initializing a {self.ACTIVITY_TYPE.value} activity: {kwargs!r}")

        # A place to set ephemeral data
        self.__ctx: Any = {}

        self.__obj: Optional["BaseActivity"] = None
        self.__actor: Optional[List[ActorType]] = None

        # The id may not be present for new activities
        if "id" in kwargs:
            self._data["id"] = kwargs.pop("id")

        if self.ACTIVITY_TYPE not in ACTOR_TYPES and self.ACTOR_REQUIRED:
            actor = kwargs.get("actor")
            if actor:
                kwargs.pop("actor")
                actor = self._validate_actor(actor)
                self._data["actor"] = actor
            elif self.ACTIVITY_TYPE in CREATE_TYPES:
                if "attributedTo" not in kwargs:
                    raise BadActivityError(f"Note is missing attributedTo")
            else:
                raise BadActivityError("missing actor")

        if self.OBJECT_REQUIRED and "object" in kwargs:
            obj = kwargs.pop("object")
            if isinstance(obj, str):
                # The object is a just a reference the its ID/IRI
                # FIXME(tsileo): fetch the ref
                self._data["object"] = obj
            elif isinstance(obj, dict):
                if not self.ALLOWED_OBJECT_TYPES:
                    raise UnexpectedActivityTypeError("unexpected object")
                if "type" not in obj or (
                    self.ACTIVITY_TYPE != ActivityType.CREATE and "id" not in obj
                ):
                    raise BadActivityError("invalid object, missing type")
                if not _has_type(  # type: ignore  # XXX too complicated
                    obj["type"], self.ALLOWED_OBJECT_TYPES
                ):
                    raise UnexpectedActivityTypeError(
                        f'unexpected object type {obj["type"]} (allowed={self.ALLOWED_OBJECT_TYPES!r})'
                    )
                self._data["object"] = obj
            else:
                raise BadActivityError(
                    f"invalid object type ({type(obj).__qualname__}): {obj!r}"
                )

        if "@context" not in kwargs:
            self._data["@context"] = CTX_AS
        else:
            self._data["@context"] = kwargs.pop("@context")

        # @context check
        if not isinstance(self._data["@context"], list):
            self._data["@context"] = [self._data["@context"]]
        if CTX_SECURITY not in self._data["@context"]:
            self._data["@context"].append(CTX_SECURITY)
        if isinstance(self._data["@context"][-1], dict):
            self._data["@context"][-1]["Hashtag"] = "as:Hashtag"
            self._data["@context"][-1]["sensitive"] = "as:sensitive"
            self._data["@context"][-1]["toot"] = "http://joinmastodon.org/ns#"
            self._data["@context"][-1]["featured"] = "toot:featured"
        else:
            self._data["@context"].append(
                {
                    "Hashtag": "as:Hashtag",
                    "sensitive": "as:sensitive",
                    "toot": "http://joinmastodon.org/ns#",
                    "featured": "toot:featured",
                }
            )

        # Remove keys with `None` value
        valid_kwargs = {}
        for k, v in kwargs.items():
            if v is None:
                continue
            valid_kwargs[k] = v
        self._data.update(**valid_kwargs)

        try:
            self._init()
        except NotImplementedError:
            pass

    def _init(self) -> None:
        """Optional init callback."""
        raise NotImplementedError

    def has_type(
        self, _types: Union[ActivityType, str, List[Union[ActivityType, str]]]
    ):
        """Return True if the activity has the given type."""
        return _has_type(self._data["type"], _types)

    def get_url(self, preferred_mimetype: str = "text/html") -> str:
        """Returns the url attributes as a str.

        Returns the URL if it's a str, or the href of the first link.

        """
        if isinstance(self.url, str):
            return self.url
        elif isinstance(self.url, dict):
            if self.url.get("type") != "Link":
                raise BadActivityError(f"invalid type {self.url}")
            return str(self.url.get("href"))
        elif isinstance(self.url, list):
            last_link = None
            for link in self.url:
                last_link = link
                if link.get("type") != "Link":
                    raise BadActivityError(f"invalid type {link}")
                if link.get("mimeType").startswith(preferred_mimetype):
                    return link.get("href")
            if not last_link:
                raise BadActivityError(f"invalid type for {self.url}")
            return last_link
        else:
            raise BadActivityError(f"invalid type for {self.url}")

    def ctx(self) -> Any:
        if self.__ctx:
            return self.__ctx()

    def set_ctx(self, ctx: Any) -> None:
        # FIXME(tsileo): does not use the ctx to set the id to the "parent" when building  delete
        self.__ctx = weakref.ref(ctx)

    def __repr__(self) -> str:
        """Pretty repr."""
        return "{}({!r})".format(self.__class__.__qualname__, self._data.get("id"))

    def __str__(self) -> str:
        """Returns the ID/IRI when castign to str."""
        return str(self._data.get("id", f"[new {self.ACTIVITY_TYPE} activity]"))

    def __getattr__(self, name: str) -> Any:
        """Allow to access the object field as regular attributes."""
        if self._data.get(name):
            return self._data.get(name)

    def _set_id(self, uri: str, obj_id: str) -> None:
        """Optional callback for subclasses to so something with a newly generated ID (for outbox activities)."""
        raise NotImplementedError

    def set_id(self, uri: str, obj_id: str) -> None:
        """Set the ID for a new activity."""
        logger.debug(f"setting ID {uri} / {obj_id}")
        self._data["id"] = uri
        try:
            self._set_id(uri, obj_id)
        except NotImplementedError:
            pass

    def _actor_id(self, obj: ObjectOrIDType) -> str:
        if isinstance(obj, dict) and _has_type(  # type: ignore
            obj["type"], ACTOR_TYPES
        ):
            obj_id = obj.get("id")
            if not obj_id:
                raise BadActivityError(f"missing object id: {obj!r}")
            return obj_id
        elif isinstance(obj, str):
            return obj
        else:
            raise BadActivityError(f'invalid "actor" field: {obj!r}')

    def _validate_actor(self, obj: ObjectOrIDType) -> str:
        if BACKEND is None:
            raise UninitializedBackendError

        obj_id = self._actor_id(obj)
        try:
            actor = BACKEND.fetch_iri(obj_id)
        except (ActivityGoneError, ActivityNotFoundError):
            raise
        except Exception:
            raise BadActivityError(f"failed to validate actor {obj!r}")

        if not actor or "id" not in actor:
            raise BadActivityError(f"invalid actor {actor}")

        if not _has_type(  # type: ignore  # XXX: too complicated
            actor["type"], ACTOR_TYPES
        ):
            raise UnexpectedActivityTypeError(f'actor has wrong type {actor["type"]!r}')

        return actor["id"]

    def get_object_id(self) -> str:
        if BACKEND is None:
            raise UninitializedBackendError

        if self.__obj:
            return self.__obj.id
        if isinstance(self._data["object"], dict):
            return self._data["object"]["id"]
        elif isinstance(self._data["object"], str):
            return self._data["object"]
        else:
            raise ValueError(f"invalid object {self._data['object']}")

    def get_object(self) -> "BaseActivity":
        """Returns the object as a BaseActivity instance."""
        if BACKEND is None:
            raise UninitializedBackendError

        if self.__obj:
            return self.__obj
        if isinstance(self._data["object"], dict):
            p = parse_activity(self._data["object"])
        else:
            obj = BACKEND.fetch_iri(self._data["object"])
            if ActivityType(obj.get("type")) not in self.ALLOWED_OBJECT_TYPES:
                raise UnexpectedActivityTypeError(
                    f'invalid object type {obj.get("type")!r}'
                )
            p = parse_activity(obj)

        self.__obj = p
        return p

    def reset_object_cache(self) -> None:
        self.__obj = None

    def to_dict(
        self, embed: bool = False, embed_object_id_only: bool = False
    ) -> ObjectType:
        """Serializes the activity back to a dict, ready to be JSON serialized."""
        data = dict(self._data)
        if embed:
            for k in ["@context", "signature"]:
                if k in data:
                    del data[k]
        if (
            data.get("object")
            and embed_object_id_only
            and isinstance(data["object"], dict)
        ):
            try:
                data["object"] = data["object"]["id"]
            except KeyError:
                raise BadActivityError(
                    f'embedded object {data["object"]!r} should have an id'
                )

        return data

    def get_actor(self) -> ActorType:
        if BACKEND is None:
            raise UninitializedBackendError

        if self.__actor:
            return self.__actor[0]

        actor = self._data.get("actor")
        if not actor and self.ACTOR_REQUIRED:
            # Quick hack for Note objects
            if self.ACTIVITY_TYPE in CREATE_TYPES:
                actor = self._data.get("attributedTo")
                if not actor:
                    raise BadActivityError(f"missing attributedTo")
            else:
                raise BadActivityError(f"failed to fetch actor: {self._data!r}")

        self.__actor: List[ActorType] = []
        for item in _to_list(actor):
            if not isinstance(item, (str, dict)):
                raise BadActivityError(f"invalid actor: {self._data!r}")

            actor_id = self._actor_id(item)

            p = parse_activity(BACKEND.fetch_iri(actor_id))
            if not p.has_type(ACTOR_TYPES):  # type: ignore
                raise UnexpectedActivityTypeError(f"{p!r} is not an actor")
            self.__actor.append(p)  # type: ignore

        return self.__actor[0]

    def _recipients(self) -> List[str]:
        return []

    def recipients(self) -> List[str]:  # noqa: C901
        if BACKEND is None:
            raise UninitializedBackendError

        recipients = self._recipients()
        actor_id = self.get_actor().id

        out: List[str] = []
        if self.type == ActivityType.CREATE.value:
            out = BACKEND.extra_inboxes()

        for recipient in recipients:
            if recipient in [actor_id, AS_PUBLIC, None]:
                continue

            try:
                actor = fetch_remote_activity(recipient)
            except (ActivityGoneError, ActivityNotFoundError, NotAnActivityError):
                logger.info(f"{recipient} is gone")
                continue
            except ActivityUnavailableError:
                # TODO(tsileo): retry separately?
                logger.info(f"failed {recipient} to fetch recipient")
                continue

            if actor.ACTIVITY_TYPE in ACTOR_TYPES:
                if actor.endpoints:
                    shared_inbox = actor.endpoints.get("sharedInbox")
                    if shared_inbox:
                        if shared_inbox not in out:
                            out.append(shared_inbox)
                        continue

                if actor.inbox and actor.inbox not in out:
                    out.append(actor.inbox)

            # Is the activity a `Collection`/`OrderedCollection`?
            elif actor.ACTIVITY_TYPE in COLLECTION_TYPES:
                for item in BACKEND.parse_collection(actor.to_dict()):
                    # XXX(tsileo): is nested collection support needed here?

                    if item in [actor_id, AS_PUBLIC]:
                        continue

                    try:
                        col_actor = fetch_remote_activity(item)
                    except ActivityUnavailableError:
                        # TODO(tsileo): retry separately?
                        logger.info(f"failed {recipient} to fetch recipient")
                        continue
                    except (
                        ActivityGoneError,
                        ActivityNotFoundError,
                        NotAnActivityError,
                    ):
                        logger.info(f"{item} is gone")
                        continue

                    if col_actor.endpoints:
                        shared_inbox = col_actor.endpoints.get("sharedInbox")
                        if shared_inbox:
                            if shared_inbox not in out:
                                out.append(shared_inbox)
                            continue

                    if col_actor.inbox and col_actor.inbox not in out:
                        out.append(col_actor.inbox)
            else:
                raise BadActivityError(f"failed to parse {recipient}")

        return out


class Person(BaseActivity):
    ACTIVITY_TYPE = ActivityType.PERSON
    OBJECT_REQUIRED = False
    ACTOR_REQUIRED = False

    def get_key(self) -> Key:
        return Key.from_dict(self.publicKey)


class Service(Person):
    ACTIVITY_TYPE = ActivityType.SERVICE


class Application(Person):
    ACTIVITY_TYPE = ActivityType.APPLICATION


class Group(Person):
    ACTIVITY_TYPE = ActivityType.GROUP


class Organization(Person):
    ACTIVITY_TYPE = ActivityType.ORGANIZATION


class Block(BaseActivity):
    ACTIVITY_TYPE = ActivityType.BLOCK
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True


class Collection(BaseActivity):
    ACTIVITY_TYPE = ActivityType.COLLECTION
    OBJECT_REQUIRED = False
    ACTOR_REQUIRED = False


class OerderedCollection(BaseActivity):
    ACTIVITY_TYPE = ActivityType.ORDERED_COLLECTION
    OBJECT_REQUIRED = False
    ACTOR_REQUIRED = False


class Image(BaseActivity):
    ACTIVITY_TYPE = ActivityType.IMAGE
    OBJECT_REQUIRED = False
    ACTOR_REQUIRED = False

    def __repr__(self):
        return "Image({!r})".format(self._data.get("url"))


class Follow(BaseActivity):
    ACTIVITY_TYPE = ActivityType.FOLLOW
    ALLOWED_OBJECT_TYPES = ACTOR_TYPES
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        return [self.get_object().id]

    def build_undo(self) -> BaseActivity:
        return Undo(object=self.to_dict(embed=True), actor=self.get_actor().id)


class Accept(BaseActivity):
    ACTIVITY_TYPE = ActivityType.ACCEPT
    ALLOWED_OBJECT_TYPES = [ActivityType.FOLLOW]
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        return [self.get_object().get_actor().id]


class Undo(BaseActivity):
    ACTIVITY_TYPE = ActivityType.UNDO
    ALLOWED_OBJECT_TYPES = [
        ActivityType.FOLLOW,
        ActivityType.LIKE,
        ActivityType.ANNOUNCE,
        ActivityType.BLOCK,
    ]
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        obj = self.get_object()
        if obj.ACTIVITY_TYPE == ActivityType.FOLLOW:
            return [obj.get_object().id]
        else:
            return [obj.get_object().get_actor().id]


class Like(BaseActivity):
    ACTIVITY_TYPE = ActivityType.LIKE
    ALLOWED_OBJECT_TYPES = CREATE_TYPES
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        return [self.get_object().get_actor().id]

    def build_undo(self) -> BaseActivity:
        return Undo(
            object=self.to_dict(embed=True, embed_object_id_only=True),
            actor=self.get_actor().id,
        )


class Announce(BaseActivity):
    ACTIVITY_TYPE = ActivityType.ANNOUNCE
    ALLOWED_OBJECT_TYPES = CREATE_TYPES
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        recipients = [self.get_object().get_actor().id]

        for field in ["to", "cc"]:
            if field in self._data:
                recipients.extend(_to_list(self._data[field]))

        return list(set(recipients))

    def build_undo(self) -> BaseActivity:
        return Undo(actor=self.get_actor().id, object=self.to_dict(embed=True))


class Delete(BaseActivity):
    ACTIVITY_TYPE = ActivityType.DELETE
    ALLOWED_OBJECT_TYPES = CREATE_TYPES + ACTOR_TYPES + [ActivityType.TOMBSTONE]
    OBJECT_REQUIRED = True

    def _get_actual_object(self) -> BaseActivity:
        if BACKEND is None:
            raise UninitializedBackendError

        # XXX(tsileo): overrides get_object instead?
        obj = self.get_object()
        if (
            obj.id.startswith(BACKEND.base_url())
            and obj.ACTIVITY_TYPE == ActivityType.TOMBSTONE
        ):
            obj = parse_activity(BACKEND.fetch_iri(obj.id))
        if obj.ACTIVITY_TYPE == ActivityType.TOMBSTONE:
            # If we already received it, we may be able to get a copy
            better_obj = BACKEND.fetch_iri(obj.id)
            if better_obj:
                return parse_activity(better_obj)
        return obj

    def _recipients(self) -> List[str]:
        obj = self._get_actual_object()
        return obj._recipients()


class Update(BaseActivity):
    ACTIVITY_TYPE = ActivityType.UPDATE
    ALLOWED_OBJECT_TYPES = CREATE_TYPES + ACTOR_TYPES
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def _recipients(self) -> List[str]:
        # TODO(tsileo): audience support?
        recipients = []
        for field in ["to", "cc", "bto", "bcc"]:
            if field in self._data:
                recipients.extend(_to_list(self._data[field]))

        recipients.extend(self.get_object()._recipients())

        return recipients


class Create(BaseActivity):
    ACTIVITY_TYPE = ActivityType.CREATE
    ALLOWED_OBJECT_TYPES = CREATE_TYPES
    OBJECT_REQUIRED = True
    ACTOR_REQUIRED = True

    def is_public(self) -> bool:
        """Returns True if the activity is addressed to the special "public" collection."""
        for field in ["to", "cc", "bto", "bcc"]:
            if field in self._data:
                if AS_PUBLIC in _to_list(self._data[field]):
                    return True

        return False

    def _set_id(self, uri: str, obj_id: str) -> None:
        if BACKEND is None:
            raise UninitializedBackendError

        # FIXME(tsileo): add a BACKEND.note_activity_url, and pass the actor to both
        self._data["object"]["id"] = uri + "/activity"
        if "url" not in self._data["object"]:
            self._data["object"]["url"] = BACKEND.note_url(obj_id)
        if isinstance(self.ctx(), Note):
            try:
                self.ctx().id = self._data["object"]["id"]
            except NotImplementedError:
                pass
        self.reset_object_cache()

    def _init(self) -> None:
        obj = self.get_object()
        if not obj.attributedTo:
            self._data["object"]["attributedTo"] = self.get_actor().id
        if not obj.published:
            if self.published:
                self._data["object"]["published"] = self.published
            else:
                now = format_datetime(datetime.now().astimezone())
                self._data["published"] = now
                self._data["object"]["published"] = now

    def _recipients(self) -> List[str]:
        # TODO(tsileo): audience support?
        recipients = []
        for field in ["to", "cc", "bto", "bcc"]:
            if field in self._data:
                recipients.extend(_to_list(self._data[field]))

        recipients.extend(self.get_object()._recipients())

        return recipients

    def get_tombstone(self, deleted: Optional[str] = None) -> BaseActivity:
        return Tombstone(
            id=self.id,
            published=self.get_object().published,
            deleted=deleted,
            updated=deleted,
        )


class Tombstone(BaseActivity):
    ACTIVITY_TYPE = ActivityType.TOMBSTONE
    ACTOR_REQUIRED = False
    OBJECT_REQUIRED = False


class Note(BaseActivity):
    ACTIVITY_TYPE = ActivityType.NOTE
    ACTOR_REQUIRED = True
    OBJECT_REQURIED = False

    def _init(self) -> None:
        if "sensitive" not in self._data:
            self._data["sensitive"] = False

    def _recipients(self) -> List[str]:
        # TODO(tsileo): audience support?
        recipients: List[str] = []

        for field in ["to", "cc", "bto", "bcc"]:
            if field in self._data:
                recipients.extend(_to_list(self._data[field]))

        return recipients

    def build_create(self) -> BaseActivity:
        """Wraps an activity in a Create activity."""
        create_payload = {
            "object": self.to_dict(embed=True),
            "actor": self.attributedTo,
        }
        for field in ["published", "to", "bto", "cc", "bcc", "audience"]:
            if field in self._data:
                create_payload[field] = self._data[field]

        create = Create(**create_payload)
        create.set_ctx(self)

        return create

    def build_like(self, as_actor: ActorType) -> BaseActivity:
        return Like(object=self.id, actor=as_actor.id)

    def build_announce(self, as_actor: ActorType) -> BaseActivity:
        return Announce(
            actor=as_actor.id,
            object=self.id,
            to=[AS_PUBLIC],
            cc=[as_actor.followers, self.attributedTo],
            published=format_datetime(datetime.now().astimezone()),
        )

    def has_mention(self, actor_id: str) -> bool:
        if self.tag is not None:
            for tag in self.tag:
                try:
                    if tag["type"] == ActivityType.MENTION.value:
                        if tag["href"] == actor_id:
                            return True
                except Exception:
                    logger.exception(f"invalid tag {tag!r}")

        return False

    def get_in_reply_to(self) -> Optional[str]:
        return _get_id(self.inReplyTo)


class Question(Note):
    ACTIVITY_TYPE = ActivityType.QUESTION
    ACTOR_REQUIRED = True
    OBJECT_REQURIED = False

    def one_of(self) -> List[Dict[str, Any]]:
        return self._data.get("oneOf", [])


class Article(Note):
    ACTIVITY_TYPE = ActivityType.ARTICLE
    ACTOR_REQUIRED = True
    OBJECT_REQURIED = False


class Page(Note):
    ACTIVITY_TYPE = ActivityType.PAGE
    ACTOR_REQUIRED = True
    OBJECT_REQURIED = False


class Video(Note):
    ACTIVITY_TYPE = ActivityType.VIDEO
    ACTOR_REQUIRED = True
    OBJECT_REQURIED = False


class Document(Note):
    ACTIVITY_TYPE = ActivityType.DOCUMENT
    ACTOR_REQUIRED = True
    OBJECT_REQUIRED = False


class Audio(Note):
    ACTIVITY_TYPE = ActivityType.AUDIO
    ACTOR_REQUIRED = True
    OBJECT_REQUIRED = False


def fetch_remote_activity(
    iri: str, expected: Optional[ActivityType] = None
) -> BaseActivity:
    return parse_activity(get_backend().fetch_iri(iri), expected=expected)
