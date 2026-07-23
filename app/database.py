"""
app/database.py — SQLAlchemy Veritabanı Katmanı

Ticket, Conversation, User ve Appointment modellerini ve veritabanı
başlatma fonksiyonunu içerir.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

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


class User(db.Model):
    """Sistem kullanıcısı — kimlik doğrulama ve rol bilgisi (hash'li şifre)."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100), nullable=False)          # Görüntülenen rol adı
    role_code = db.Column(db.String(50), nullable=False)      # 'admin' | 'sekreter'
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
            "role_code": self.role_code,
            "is_active": self.is_active,
            "date_created": self.date_created.strftime("%d.%m.%Y %H:%M"),
        }


class Appointment(db.Model):
    """Gerçekleştirilen bir no-show risk tahmininin kalıcı kaydı.

    Dashboard'daki 'yüksek riskli randevular' tablosu ve ana sayfa/rapor
    istatistikleri artık bu tablodan okunur — sabit/mock veri kullanılmaz.
    """
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_name = db.Column(db.String(150), nullable=False, default="İsimsiz Hasta")
    poliklinik = db.Column(db.String(100), nullable=True)
    age = db.Column(db.Integer, nullable=False, default=0)
    scholarship = db.Column(db.Integer, nullable=False, default=0)
    hipertension = db.Column(db.Integer, nullable=False, default=0)
    diabetes = db.Column(db.Integer, nullable=False, default=0)
    alcoholism = db.Column(db.Integer, nullable=False, default=0)
    handcap = db.Column(db.Integer, nullable=False, default=0)
    sms_received = db.Column(db.Integer, nullable=False, default=0)
    days_waiting = db.Column(db.Integer, nullable=False, default=0)
    previous_noshow = db.Column(db.Integer, nullable=False, default=0)

    prediction = db.Column(db.Integer, nullable=False)
    probability = db.Column(db.Float, nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(50), nullable=False)
    risk_color = db.Column(db.String(20), nullable=False)

    created_by = db.Column(db.String(100), nullable=True, default="admin")
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "poliklinik": self.poliklinik,
            "age": self.age,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_color": self.risk_color,
            "previous_noshow": self.previous_noshow,
            "sms_received": self.sms_received,
            "date_created": self.date_created.strftime("%d.%m.%Y %H:%M"),
        }


def get_visible_tickets_query(role, username, status=None, search=None):
    """Rol bazlı görünürlük kuralını tek yerde uygular.

    admin tüm biletleri görür; diğer roller sadece kendi oluşturduklarını görür.
    main_routes, chatbot.index ve chatbot.get_tickets bu fonksiyonu paylaşır —
    aksi halde aynı filtre mantığının kopyalanması IDOR/tutarsızlık riski taşır.
    """
    query = Ticket.query
    if role != "admin":
        query = query.filter_by(created_by=username)
    if status:
        query = query.filter_by(status=status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Ticket.problem_description.ilike(like),
                Ticket.user_message.ilike(like),
            )
        )
    return query.order_by(Ticket.date_created.desc())


def seed_default_users():
    """İlk çalıştırmada demo kullanıcılarını (hash'li şifreyle) oluşturur."""
    if User.query.first() is not None:
        return

    defaults = [
        User(
            username="sekreter",
            password_hash=generate_password_hash("123"),
            name="HBYS Personeli",
            role="HBYS Kullanıcısı",
            role_code="sekreter",
        ),
        User(
            username="admin",
            password_hash=generate_password_hash("123"),
            name="Bilgi İşlem",
            role="Bilgi İşlem Sorumlusu",
            role_code="admin",
        ),
    ]
    db.session.add_all(defaults)
    db.session.commit()


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

        seed_default_users()

        app.logger.info("Veritabanı tabloları başarıyla hazırlandı.")
