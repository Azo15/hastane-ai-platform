"""
app/database.py — SQLAlchemy Veritabanı Katmanı

Ticket modeli ve veritabanı başlatma fonksiyonunu içerir.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Ticket(db.Model):
    """IT Destek Talebi (Ticket) Modeli."""

    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    problem_description = db.Column(db.Text, nullable=False)
    date_created = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
    status = db.Column(db.String(50), nullable=False, default="Açık")
    # Ek bilgi alanları
    user_message = db.Column(db.Text, nullable=True)  # Kullanıcının orijinal mesajı
    ai_response = db.Column(db.Text, nullable=True)   # Claude'un yanıtı

    def to_dict(self):
        """Ticket nesnesini JSON serileştirilebilir dict'e dönüştür."""
        return {
            "id": self.id,
            "problem_description": self.problem_description,
            "date_created": self.date_created.strftime("%d.%m.%Y %H:%M"),
            "status": self.status,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
        }

    def __repr__(self):
        return f"<Ticket #{self.id} — {self.status}>"


def init_db(app):
    """Veritabanı tablolarını oluşturur (eğer yoksa)."""
    with app.app_context():
        db.create_all()
        app.logger.info("Veritabanı tabloları başarıyla oluşturuldu.")
