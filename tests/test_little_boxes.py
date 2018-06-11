from unittest import mock

from little_boxes import activitypub as ap


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

    assert back.followers(other) == [me.id]
    assert back.following(other) == []

    assert back.followers(me) == []
    assert back.following(me) == [other.id]
