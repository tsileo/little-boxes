import logging

from little_boxes import activitypub as ap
from test_backend import InMemBackend

logging.basicConfig(level=logging.DEBUG)


def _assert_eq(val, other):
    assert val == other


def test_little_boxes_follow():
    back = InMemBackend()
    ap.use_backend(back)

    me = back.setup_actor("Thomas", "tom")

    other = back.setup_actor("Thomas", "tom2")

    outbox = ap.Outbox(me)
    f = ap.Follow(actor=me.id, object=other.id)

    outbox.post(f)

    back.assert_called_methods(
        me,
        (
            "follow is saved in the actor inbox",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, f.id),
        ),
        (
            "follow is sent to the remote followee inbox",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
        (
            "receiving an accept, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda remote_actor: _assert_eq(remote_actor, other.id),
        ),
        (
            "receiving the accept response from the follow",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.get_object().id, f.id),
        ),
        (
            "the new_following hook is called",
            "new_following",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, f.id),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the follow, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the follow activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, f.id),
        ),
        (
            "posting an accept in response to the follow",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.get_object().id, f.id),
        ),
        (
            "post the accept to the remote follower inbox",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, me.inbox),
        ),
        (
            "the new_follower hook is called",
            "new_follower",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, f.id),
        ),
    )

    assert back.followers(other) == [me.id]
    assert back.following(other) == []

    assert back.followers(me) == []
    assert back.following(me) == [other.id]

    return back, f


def test_little_boxes_follow_unfollow():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")

    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    undo = f.build_undo()
    outbox.post(undo)

    back.assert_called_methods(
        me,
        (
            "an Undo activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"undo_new_following" hook is called',
            "undo_new_following",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda follow: _assert_eq(follow.id, f.id),
        ),
        (
            "the Undo activity is posted to the followee",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Undo activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"undo_new_follower" hook is called',
            "undo_new_follower",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda follow: _assert_eq(follow.id, f.id),
        ),
    )

    assert back.followers(other) == []
    assert back.following(other) == []

    assert back.followers(me) == []
    assert back.following(me) == []


def test_little_boxes_follow_and_new_note_public_only():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    note = ap.Note(to=[ap.AS_PUBLIC], cc=[], attributedTo=me.id, content="Hello")
    outbox.post(note)

    back.assert_called_methods(
        me,
        (
            "an Create activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_create",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
    )

    back.assert_called_methods(other)


def test_little_boxes_follow_and_new_note_to_single_actor():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    note = ap.Note(
        to=[ap.AS_PUBLIC], cc=[other.id], attributedTo=me.id, content="Hello"
    )
    outbox.post(note)

    back.assert_called_methods(
        me,
        (
            "an Create activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_create",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
        (
            "the Undo activity is posted to the followee",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Create activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"inbox_create" hook is called',
            "inbox_create",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
    )


def test_little_boxes_follow_and_new_note_to_followers_only():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(other)

    note = ap.Note(
        to=[ap.AS_PUBLIC], cc=[other.followers], attributedTo=other.id, content="Hello"
    )
    outbox.post(note)

    back.assert_called_methods(
        other,
        (
            "an Create activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_create",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
        (
            "the Undo activity is posted to the followee",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, me.inbox),
        ),
    )

    back.assert_called_methods(
        me,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda remote_actor: _assert_eq(remote_actor, other.id),
        ),
        (
            "receiving the Create activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"inbox_create" hook is called',
            "inbox_create",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
    )


def test_little_boxes_follow_and_new_note_to_followers_and_single_actor_dedup():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(other)

    note = ap.Note(
        to=[ap.AS_PUBLIC],
        cc=[me.id, other.followers],
        attributedTo=other.id,
        content="Hello",
    )
    outbox.post(note)

    back.assert_called_methods(
        other,
        (
            "an Create activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_create",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
        (
            "the Undo activity is posted to the followee",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, me.inbox),
        ),
    )

    back.assert_called_methods(
        me,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda remote_actor: _assert_eq(remote_actor, other.id),
        ),
        (
            "receiving the Create activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.get_object().id, note.id),
        ),
        (
            '"inbox_create" hook is called',
            "inbox_create",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda create: _assert_eq(create.get_object().id, note.id),
        ),
    )


def test_little_boxes_follow_and_new_create_note():
    back, f = test_little_boxes_follow()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(other)

    note = ap.Note(
        to=[ap.AS_PUBLIC], cc=[other.followers], attributedTo=other.id, content="Hello"
    )
    create = note.build_create()
    outbox.post(create)

    back.assert_called_methods(
        other,
        (
            "an Create activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, create.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_create",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _create: _assert_eq(_create.id, create.id),
        ),
        (
            "the Undo activity is posted to the followee",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, me.inbox),
        ),
    )

    back.assert_called_methods(
        me,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda remote_actor: _assert_eq(remote_actor, other.id),
        ),
        (
            "receiving the Create activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, create.id),
        ),
        (
            '"inbox_create" hook is called',
            "inbox_create",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _create: _assert_eq(_create.id, create.id),
        ),
    )

    return back, create


def test_little_boxes_follow_and_new_create_note_and_delete():
    back, create = test_little_boxes_follow_and_new_create_note()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(other)

    delete = create.get_object().build_delete()
    outbox.post(delete)

    back.assert_called_methods(
        other,
        (
            "an Delete activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, delete.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_delete",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _delete: _assert_eq(_delete.id, delete.id),
        ),
        (
            "the Delete activity is posted to the followers",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, me.inbox),
        ),
    )

    back.assert_called_methods(
        me,
        (
            "receiving the Delete, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda remote_actor: _assert_eq(remote_actor, other.id),
        ),
        (
            "receiving the Delete activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, delete.id),
        ),
        (
            '"inbox_delete" hook is called',
            "inbox_delete",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _delete: _assert_eq(_delete.id, delete.id),
        ),
    )


def test_little_boxes_follow_and_new_create_note_and_update():
    back, create = test_little_boxes_follow_and_new_create_note()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(other)

    update = ap.Update(
        actor=other.id,
        object={
            "content": "Hello2",
            "id": create.get_object().id,
            "type": "Note",
            "attributedTo": other.id,
        },
    )
    outbox.post(update)

    back.assert_called_methods(
        other,
        (
            "an Delete activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, update.id),
        ),
        (
            '"outbox_update" hook is called',
            "outbox_update",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _update: _assert_eq(_update.id, update.id),
        ),
    )

    back.assert_called_methods(me)


def test_little_boxes_follow_and_new_create_note_and_like():
    back, create = test_little_boxes_follow_and_new_create_note()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    like = create.get_object().build_like(me)
    outbox.post(like)

    back.assert_called_methods(
        me,
        (
            "a Like activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, like.id),
        ),
        (
            '"outbox_create" hook is called',
            "outbox_like",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _like: _assert_eq(_like.id, like.id),
        ),
        (
            "the Delete activity is posted to the note creator",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Like, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Like activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, like.id),
        ),
        (
            '"inbox_like" hook is called',
            "inbox_like",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _like: _assert_eq(_like.id, like.id),
        ),
    )

    return back, like


def test_little_boxes_follow_and_new_create_note_and_like_and_undo_like():
    back, like = test_little_boxes_follow_and_new_create_note_and_like()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    undo = like.build_undo()
    outbox.post(undo)

    back.assert_called_methods(
        me,
        (
            "an Undo activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"outbox_undo_like" hook is called',
            "outbox_undo_like",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _like: _assert_eq(_like.id, undo.get_object().id),
        ),
        (
            "the Undo activity is posted to the original recipients",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Like, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Undo activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"inbox_undo_like" hook is called',
            "inbox_undo_like",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _like: _assert_eq(_like.id, undo.get_object().id),
        ),
    )


def test_little_boxes_follow_and_new_create_note_and_announce():
    back, create = test_little_boxes_follow_and_new_create_note()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    announce = ap.Announce(actor=me.id, object=create.get_object().id)
    outbox.post(announce)

    back.assert_called_methods(
        me,
        (
            "an Announce activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, announce.id),
        ),
        (
            '"outbox_announce" hook is called',
            "outbox_announce",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _announce: _assert_eq(_announce.id, announce.id),
        ),
        (
            "the Announce activity is posted to the note creator",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Announce, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Announce activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, announce.id),
        ),
        (
            '"inbox_announce" hook is called',
            "inbox_announce",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _announce: _assert_eq(_announce.id, announce.id),
        ),
    )

    return back, announce


def test_little_boxes_follow_and_new_create_note_and_like_and_undo_announce():
    back, announce = test_little_boxes_follow_and_new_create_note_and_announce()

    me = back.get_user("tom")
    other = back.get_user("tom2")

    outbox = ap.Outbox(me)

    undo = announce.build_undo()
    outbox.post(undo)

    back.assert_called_methods(
        me,
        (
            "an Undo activity is published",
            "outbox_new",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"outbox_undo_announce" hook is called',
            "outbox_undo_announce",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda _announce: _assert_eq(_announce.id, undo.get_object().id),
        ),
        (
            "the Undo activity is posted to the original recipients",
            "post_to_remote_inbox",
            lambda as_actor: _assert_eq(as_actor.id, me.id),
            lambda payload: None,
            lambda recipient: _assert_eq(recipient, other.inbox),
        ),
    )

    back.assert_called_methods(
        other,
        (
            "receiving the Undo, ensure we check the actor is not blocked",
            "outbox_is_blocked",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda remote_actor: _assert_eq(remote_actor, me.id),
        ),
        (
            "receiving the Undo activity",
            "inbox_new",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda activity: _assert_eq(activity.id, undo.id),
        ),
        (
            '"inbox_undo_announce" hook is called',
            "inbox_undo_announce",
            lambda as_actor: _assert_eq(as_actor.id, other.id),
            lambda _announce: _assert_eq(_announce.id, undo.get_object().id),
        ),
    )
