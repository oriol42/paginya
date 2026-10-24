import time

import pytest

from app import accounts, admin, config, db, support
from tests.test_api import SVG, client  # noqa: F401  (fixture)

USERS = {"t-client": ("g-1", "client@gmail.com"), "t-chef": ("g-2", "chef@gmail.com"), "t-camarade": ("g-3", "camarade@gmail.com")}


@pytest.fixture()
def signed(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(admin, "google_identity", lambda credential: USERS[credential])  # Google is not called in tests
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "ACCOUNT_SECRET", "s3cret")
    monkeypatch.setattr(config, "ADMIN_SECRET", "s3cret")
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"chef@gmail.com", "camarade@gmail.com"})
    return lambda who: client.post("/account/google", json={"credential": who}).json()["token"]


def buy(client, token, plan):  # noqa: F811
    p = client.post("/account/pass", json={"token": token, "plan": plan}).json()
    client.post(f"/orders/{p['id']}/pay", json={"phone": "670000000"})
    assert client.get(f"/orders/{p['id']}").json()["status"] == "PAID"
    return client.post("/account/me", json={"token": token}).json()


def new_doc(client):  # noqa: F811
    return client.post("/orders", json={"svg": SVG, "form": {}}).json()["id"]


def test_prices_one_document_and_two_passes(client):  # noqa: F811
    prices = client.get("/prices").json()
    assert {prices[k]["amount"] for k in ("page_de_garde", "lettre", "epreuve", "memoire", "rapport")} == {550}
    assert prices["pass_essentiel"] == {"label": "Pass Essentiel 30 jours", "amount": 3000, "per_day": 10}
    assert prices["pass_pro"]["amount"] == 5000 and "pass_30j" not in prices
    # a pass is bought from an account only, never as a document
    assert client.post("/orders", json={"svg": SVG, "product": "pass_pro"}).status_code == 400


def test_essentiel_pass_has_a_daily_limit_and_never_counts_a_download_twice(client, signed, monkeypatch):  # noqa: F811
    token = signed("t-client")
    me = buy(client, token, "essentiel")
    assert (me["plan"], me["per_day"], me["used_today"], me["pass_days"]) == ("essentiel", 10, 0, 30)
    docs = [new_doc(client) for _ in range(11)]
    for d in docs[:10]:
        assert client.post(f"/orders/{d}/unlock", json={"token": token}).json()["status"] == "PAID"
    assert client.post(f"/orders/{docs[0]}/unlock", json={"token": token}).status_code == 200  # again: free, not counted
    r = client.post(f"/orders/{docs[10]}/unlock", json={"token": token})
    assert r.status_code == 429 and "10 documents du jour" in r.json()["detail"]
    assert client.post("/account/me", json={"token": token}).json()["used_today"] == 10
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 86400)  # tomorrow
    assert client.post(f"/orders/{docs[10]}/unlock", json={"token": token}).json()["status"] == "PAID"
    monkeypatch.setattr(time, "time", lambda: real() + 31 * 86400)  # no automatic renewal
    assert client.post(f"/orders/{new_doc(client)}/unlock", json={"token": token}).status_code == 402
    assert client.post("/account/me", json={"token": token}).json()["plan"] == ""


def test_changing_plan_keeps_the_value_of_the_days_left(client, signed):  # noqa: F811
    token = signed("t-client")
    buy(client, token, "essentiel")
    me = buy(client, token, "essentiel")
    assert me["pass_days"] == 60  # same plan: 30 more days
    me = buy(client, token, "pro")
    assert me["plan"] == "pro" and me["per_day"] == 0  # unlimited
    for _ in range(60):
        assert client.post(f"/orders/{new_doc(client)}/unlock", json={"token": token}).json()["status"] == "PAID"
    assert me["pass_days"] == 30 + 36  # 60 Essentiel days (6 000 F) = 36 Pro days


def test_both_team_members_never_pay_and_have_no_limit(client, signed):  # noqa: F811
    for who in ("t-chef", "t-camarade"):
        token = signed(who)
        assert client.post("/account/me", json={"token": token}).json()["team"] is True
        for _ in range(45):
            assert client.post(f"/orders/{new_doc(client)}/unlock", json={"token": token}).json()["status"] == "PAID"
    # the team page signs the account in too
    out = client.post("/admin/login", json={"credential": "t-camarade"}).json()
    assert out["email"] == "camarade@gmail.com" and out["account"]["team"] is True
    assert client.post("/admin/login", json={"credential": "t-client"}).status_code == 403


def test_support_reaches_both_team_members_and_the_customer_reads_the_answer(client, signed, monkeypatch):  # noqa: F811
    rung = []
    monkeypatch.setattr(support, "notify", lambda title, text: rung.append(title))
    assert client.post("/support", json={"message": "Bonjour, j'ai payé"}).status_code == 400  # no way to answer
    order = new_doc(client)
    t = client.post("/support", json={"message": "J'ai payé mais rien", "name": "Awa", "contact": "690000000", "order_id": order}).json()
    assert t["status"] == "NEW" and t["messages"][0]["from"] == "toi" and rung == ["Paginya : nouveau message"]

    chef = client.post("/admin/login", json={"credential": "t-chef"}).json()["token"]
    camarade = client.post("/admin/login", json={"credential": "t-camarade"}).json()["token"]
    assert client.post("/admin/support", json={"token": "faux"}).status_code == 403
    for token in (chef, camarade):  # both see the same inbox
        box = client.post("/admin/support", json={"token": token}).json()
        assert box["waiting"] == 1 and box["tickets"][0]["name"] == "Awa"
    full = client.post(f"/admin/support/{t['id']}", json={"token": camarade}).json()
    assert full["contact"] == "690000000" and full["order"]["id"] == order and full["order"]["status"] == "DRAFT"

    client.post(f"/orders/{order}/admin", json={"token": chef})  # solved: unlocked
    full = client.post(f"/admin/support/{t['id']}/reply", json={"token": chef, "message": "C'est débloqué !"}).json()
    assert full["status"] == "ANSWERED" and full["messages"][-1]["author"] == "chef@gmail.com"  # the other one knows who answered
    seen = client.get(f"/support/{t['id']}").json()
    assert seen["messages"][-1] == {**seen["messages"][-1], "from": "paginya", "body": "C'est débloqué !"}
    assert "chef@gmail.com" not in str(seen)

    client.post(f"/support/{t['id']}/messages", json={"message": "Merci !"})
    assert client.post("/admin/support", json={"token": camarade}).json()["waiting"] == 1 and len(rung) == 2
    assert client.post(f"/admin/support/{t['id']}/status", json={"token": camarade, "status": "CLOSED"}).json()["status"] == "CLOSED"
    assert client.get("/support/" + "0" * 32).status_code == 404


def test_signed_in_customer_finds_their_conversations_and_the_team_can_offer_days(client, signed, monkeypatch):  # noqa: F811
    monkeypatch.setattr(support, "notify", lambda title, text: None)
    token = signed("t-client")
    t = client.post("/support", json={"message": "Mon pass n'apparaît pas", "token": token}).json()  # the account's e-mail is the contact
    assert [x["id"] for x in client.post("/account/tickets", json={"token": token}).json()] == [t["id"]]
    chef = client.post("/admin/login", json={"credential": "t-chef"}).json()["token"]
    full = client.post(f"/admin/support/{t['id']}", json={"token": chef}).json()
    assert full["contact"] == "client@gmail.com" and full["account"]["plan"] == ""
    assert client.post("/admin/gift", json={"token": chef, "email": "inconnu@gmail.com"}).status_code == 404
    out = client.post("/admin/gift", json={"token": chef, "email": "client@gmail.com", "plan": "essentiel", "days": 30}).json()
    assert out["plan"] == "essentiel" and out["pass_days"] == 30
    assert client.post("/admin/gift", json={"token": token, "email": "client@gmail.com"}).status_code == 403


def test_tickets_are_deleted_after_a_year(client):  # noqa: F811
    db.create_ticket(None, "", "x@y.z", None, "vieux")
    db.purge_tickets(now=time.time() + 366 * 86400)
    assert db.list_tickets() == []


def test_old_5000_pass_counts_as_pro(client, signed):  # noqa: F811
    token = signed("t-client")
    with db.connect() as c:
        c.execute("UPDATE accounts SET pass_until = ? WHERE sub = 'g-1'", (time.time() + 10 * 86400,))
    me = client.post("/account/me", json={"token": token}).json()
    assert me["plan"] == "pro" and me["per_day"] == 0
    assert accounts.account_of(token)["plan"] == ""
