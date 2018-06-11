from unittest import mock

from little_boxes import activitypub as ap

def _assert_eq(val, other):
    assert val == other


def test_little_boxes_follow():
    back = ap.BaseBackend()
    ap.use_backend(back)

    me = back.setup_actor('Thomas', 'tom')

    other = back.setup_actor('Thomas', 'tom2')

    outbox = ap.Outbox(me)
    f = ap.Follow(
        actor=me.id,
        object=other.id,
    )

    outbox.post(f)

    back.assert_called_methods(
            ('outbox_new', lambda x: _assert_eq(x.id, f.id)),
            ('post_to_remote_inbox', lambda x: None, lambda x: other.id+'/inbox'),
            ('outbox_is_blocked', lambda x: other.id, lambda x: me.id),
            # FIXME(tsileo): finish this
            # ('new_following', lambda x: _assert_eq(x, me.id), lambda x: _assert_eq(x.id, f.id)),
    )

    assert back.followers(other) == [me.id]
    assert back.following(other) == []

    assert back.followers(me) == []
    assert back.following(me) == [other.id]


def test_little_boxes_follow_unfollow():
    back = ap.BaseBackend()
    ap.use_backend(back)

    me = back.setup_actor('Thomas', 'tom')

    other = back.setup_actor('Thomas', 'tom2')

    outbox = ap.Outbox(me)
    f = ap.Follow(
        actor=me.id,
        object=other.id,
    )

    outbox.post(f)

    assert back.followers(other) == [me.id]
    assert back.following(other) == []

    assert back.followers(me) == []
    assert back.following(me) == [other.id]

    outbox.post(f.build_undo())

    # assert back.followers(other) == []
    # assert back.following(other) == []

    # assert back.followers(me) == []
    # assert back.following(me) == [] 
