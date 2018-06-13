from little_boxes.key import Key


def test_key_new_load():
    owner = "http://lol.com"
    k = Key(owner)
    k.new()

    assert k.to_dict() == {
        "id": f"{owner}#main-key",
        "owner": owner,
        "publicKeyPem": k.pubkey_pem,
    }

    k2 = Key(owner)
    k2.load(k.privkey_pem)

    assert k2.to_dict() == k.to_dict()
