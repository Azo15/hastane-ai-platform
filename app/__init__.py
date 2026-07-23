"""
app/__init__.py — Flask Application Factory
Blueprintleri ve uzantıları kayıt eder.
"""

from __future__ import annotations

import os
from typing import Optional
from flask import Flask
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from .database import db, init_db

load_dotenv()

csrf = CSRFProtect()


def create_app(test_config: Optional[dict] = None):
    """Flask uygulama fabrikası — tüm Blueprint ve uzantıları başlatır.

    test_config verilirse (pytest için) varsayılan ayarların üzerine yazılır.
    """
    app = Flask(__name__)

    # Uygulama konfigürasyonu
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "varsayilan-gizli-anahtar")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URI", "sqlite:///tickets.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    # SQLAlchemy'yi uygulamaya bağla
    db.init_app(app)
    # CSRF koruması — tüm POST/PUT/DELETE istekleri için token zorunlu kılar
    csrf.init_app(app)

    # Blueprint'leri kayıt et
    from .modules.no_show import no_show_bp
    from .modules.chatbot import chatbot_bp

    app.register_blueprint(no_show_bp, url_prefix="/no-show")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")

    # Ana sayfa rotasını kayıt et
    from .main_routes import main_bp, load_settings
    app.register_blueprint(main_bp)

    # Şablonlarda dinamik hastane adını göstermek için global ayar enjektörü
    @app.context_processor
    def inject_settings():
        return dict(system_settings=load_settings())

    # Veritabanı tablolarını oluştur ve makine öğrenmesi modelini ön yükle (yoksa eğitir)
    with app.app_context():
        init_db(app)
        try:
            from .modules.no_show.model_utils import load_model
            load_model()
        except Exception as e:
            app.logger.warning(f"Model ön yükleme hatası: {e}")

    return app
