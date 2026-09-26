"""One Fapshi service shared by Paginya (PG-) and Affichya (AF-)."""
from app import config, fapshi


def test_prefix_and_forward(monkeypatch):
    monkeypatch.setattr(config, "FAPSHI_PREFIX", "PG")
    monkeypatch.setattr(config, "FAPSHI_FORWARD", {"AF": "https://affichya/webhooks/fapshi"})
    assert fapshi.external_id("abc") == "PG-abc"
    assert fapshi.order_id_of("PG-abc") == "abc" and fapshi.order_id_of("abc") == "abc"
    assert fapshi.forward_target("AF-xyz") == "https://affichya/webhooks/fapshi"
    assert fapshi.forward_target("PG-abc") is None and fapshi.forward_target("abc") is None
    order = {"id": "abc", "amount": 500}
    assert fapshi.matches({"amount": 500, "externalId": "PG-abc"}, order)
    assert fapshi.matches({"amount": 500, "externalId": "abc"}, order)  # orders made before the prefix
    assert not fapshi.matches({"amount": 500, "externalId": "AF-abc"}, order)
    assert not fapshi.matches({"amount": 100, "externalId": "PG-abc"}, order)


def test_payment_page_while_direct_pay_is_not_activated(monkeypatch):
    def refused(*a, **k):
        raise fapshi.DirectPayDisabled("Forbidden request")
    monkeypatch.setattr(fapshi, "direct_pay", refused)
    monkeypatch.setattr(fapshi, "initiate_pay", lambda amount, ext, msg, url: ("t1", "https://checkout.fapshi.com/x"))
    monkeypatch.setattr(config, "FAPSHI_PAY_METHOD", "auto")
    assert fapshi.start(500, "670000000", "PG-a", "m", "https://site/paiement/") == ("t1", "https://checkout.fapshi.com/x")
    monkeypatch.setattr(config, "FAPSHI_PAY_METHOD", "direct")
    try:
        fapshi.start(500, "670000000", "PG-a", "m", "https://site/paiement/")
        raise AssertionError("direct only must not fall back")
    except fapshi.DirectPayDisabled:
        pass
