"""
tests/test_app.py — Kimlik doğrulama, yetkilendirme (IDOR) ve ticket akışı testleri.

Çalıştırmak için: pytest
"""
from werkzeug.security import generate_password_hash

from app.database import db, User, Ticket
from .conftest import login


def test_login_with_valid_credentials_succeeds(client):
    resp = login(client, "admin", "123")
    assert resp.status_code == 200
    assert "Kontrol Paneli".encode("utf-8") in resp.data or b"Hastane AI" in resp.data


def test_login_with_invalid_credentials_fails(client):
    resp = login(client, "admin", "yanlis-sifre")
    assert b"Ge\xc3\xa7ersiz kullan\xc4\xb1c\xc4\xb1 ad\xc4\xb1 veya \xc5\x9fifre" in resp.data


def test_login_with_inactive_user_fails(app, client):
    with app.app_context():
        user = User(
            username="pasifkullanici",
            password_hash=generate_password_hash("123"),
            name="Pasif Kullanıcı",
            role="HBYS Kullanıcısı",
            role_code="sekreter",
            is_active=False,
        )
        db.session.add(user)
        db.session.commit()

    resp = login(client, "pasifkullanici", "123")
    # Aktif olmayan kullanıcı giriş yapamamalı — ana sayfaya değil login'e geri döner.
    assert b"Kontrol Paneli" not in resp.data


def test_protected_route_redirects_to_login_when_not_authenticated(client):
    resp = client.get("/chatbot/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_manual_ticket_creation_flow(client):
    login(client, "admin", "123")
    resp = client.post(
        "/chatbot/create-ticket",
        json={"description": "Yazıcı çalışmıyor", "user_message": "Yazıcı çalışmıyor"},
    )
    data = resp.get_json()
    assert data["success"] is True
    assert data["ticket"]["status"] == "Açık"
    assert data["ticket"]["created_by"] == "admin"


def test_non_owner_cannot_close_other_users_ticket(app, client):
    """IDOR regresyon testi: bir sekreter kullanıcısı başka bir kullanıcının biletini kapatamamalı."""
    with app.app_context():
        db.session.add(User(
            username="sekreter2",
            password_hash=generate_password_hash("123"),
            name="İkinci Sekreter",
            role="HBYS Kullanıcısı",
            role_code="sekreter",
        ))
        db.session.commit()

    # "sekreter" kullanıcısı bir bilet oluşturuyor.
    login(client, "sekreter", "123")
    create_resp = client.post(
        "/chatbot/create-ticket",
        json={"description": "HBYS'ye giremiyorum"},
    )
    ticket_id = create_resp.get_json()["ticket"]["id"]
    client.get("/logout")

    # "sekreter2" başka bir kullanıcının biletini kapatmaya çalışıyor — 403 bekleniyor.
    login(client, "sekreter2", "123")
    close_resp = client.post(f"/chatbot/ticket/{ticket_id}/close")
    assert close_resp.status_code == 403

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        assert ticket.status == "Açık"


def test_owner_can_close_own_ticket(client):
    login(client, "sekreter", "123")
    create_resp = client.post("/chatbot/create-ticket", json={"description": "Internet yok"})
    ticket_id = create_resp.get_json()["ticket"]["id"]

    close_resp = client.post(f"/chatbot/ticket/{ticket_id}/close")
    assert close_resp.status_code == 200
    assert close_resp.get_json()["success"] is True


def test_admin_can_close_any_ticket(client):
    login(client, "sekreter", "123")
    create_resp = client.post("/chatbot/create-ticket", json={"description": "Bilgisayar açılmıyor"})
    ticket_id = create_resp.get_json()["ticket"]["id"]
    client.get("/logout")

    login(client, "admin", "123")
    close_resp = client.post(f"/chatbot/ticket/{ticket_id}/close")
    assert close_resp.status_code == 200


def test_non_admin_cannot_access_settings(client):
    login(client, "sekreter", "123")
    resp = client.get("/settings")
    assert resp.status_code == 403


def test_admin_can_add_new_user(client):
    login(client, "admin", "123")
    resp = client.post(
        "/settings/users/add",
        data={
            "username": "yenipersonel",
            "name": "Yeni Personel",
            "password": "guvenli123",
            "role_code": "sekreter",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    client.get("/logout")

    # Yeni kullanıcı gerçekten oluşturulmuş ve giriş yapabiliyor mu?
    login_resp = login(client, "yenipersonel", "guvenli123")
    assert b"Kontrol Paneli" in login_resp.data
