"""Pytest fixtures — her test için izole, dosya tabanlı bir SQLite veritabanı kurar.

(":memory:" kullanılmıyor çünkü Flask-SQLAlchemy'nin bağlantı havuzu farklı
istekler için farklı bağlantılar açabilir; SQLite'ın bellek-içi modu bu durumda
her bağlantıda ayrı/boş bir veritabanına yol açar.)
"""
import os
import tempfile

import pytest

from app import create_app
from app.database import db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
    })

    yield application

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username="admin", password="123"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
