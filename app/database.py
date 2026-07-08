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
    created_by = db.Column(db.String(100), nullable=True, default='admin') # Bileti oluşturan kullanıcı adı

    def to_dict(self):
        """Ticket nesnesini JSON serileştirilebilir dict'e dönüştür."""
        return {
            "id": self.id,
            "problem_description": self.problem_description,
            "date_created": self.date_created.strftime("%d.%m.%Y %H:%M"),
            "status": self.status,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<Ticket #{self.id} — {self.status}>"


class Conversation(db.Model):
    """Chatbot Geçmiş Konuşmaları Modeli."""
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    messages_json = db.Column(db.Text, nullable=False)  # JSON dizisi olarak saklanan konuşma geçmişi
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        import json
        try:
            msgs = json.loads(self.messages_json)
        except Exception:
            msgs = []
        return {
            "id": self.id,
            "username": self.username,
            "title": self.title,
            "messages": msgs,
            "date_created": self.date_created.strftime("%d.%m.%Y %H:%M")
        }


def init_db(app):
    """Veritabanı tablolarını oluşturur ve gerekirse şema güncellemesi (migration) yapar."""
    with app.app_context():
        db.create_all()
        
        # SQLite için created_by kolonunu dinamik ekle (migration)
        try:
            # created_by kolonu var mı kontrol et
            db.session.execute(db.text("SELECT created_by FROM tickets LIMIT 1"))
        except Exception:
            # Hata verdiyse kolon yok demektir, ALTER TABLE ile ekleyelim
            db.session.rollback()
            try:
                db.session.execute(db.text("ALTER TABLE tickets ADD COLUMN created_by VARCHAR(100) DEFAULT 'admin'"))
                db.session.commit()
                app.logger.info("tickets tablosuna created_by kolonu başarıyla eklendi.")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"tickets tablosuna created_by kolonu eklenirken hata: {e}")
        
        app.logger.info("Veritabanı tabloları başarıyla hazırlandı.")
