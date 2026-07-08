"""
app/__init__.py — Flask Application Factory
Blueprintleri ve uzantıları kayıt eder.
"""

import os
from flask import Flask
from dotenv import load_dotenv
from .database import db, init_db

load_dotenv()


def create_app():
    """Flask uygulama fabrikası — tüm Blueprint ve uzantıları başlatır."""
    app = Flask(__name__)

    # Uygulama konfigürasyonu
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "varsayilan-gizli-anahtar")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URI", "sqlite:///tickets.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # SQLAlchemy'yi uygulamaya bağla
    db.init_app(app)

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

    # Veritabanı tablolarını oluştur
    with app.app_context():
        init_db(app)

    return app
