"""
app/modules/chatbot/routes.py — IT Destek Chatbot Rotaları

/chatbot/              → Chat arayüzü + aktif ticket listesi
/chatbot/send          → POST: Mesaj gönder, Claude yanıtı al, ticket kontrol et
/chatbot/create-ticket → POST: Manuel ticket oluştur (buton tıklaması)
/chatbot/tickets       → GET: Tüm aktif ticketları JSON olarak döndür
/chatbot/ticket/<id>/close → POST: Ticket'ı kapat
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from flask import render_template, request, jsonify
from . import chatbot_bp
from .claude_client import chat_with_claude
from ...database import db, Ticket


@chatbot_bp.route("/", methods=["GET"])
def index():
    """Chat arayüzü ve aktif ticket listesi."""
    tickets = (
        Ticket.query.order_by(Ticket.date_created.desc()).limit(20).all()
    )
    return render_template("chatbot.html", tickets=tickets)


@chatbot_bp.route("/send", methods=["POST"])
def send_message():
    """
    Kullanıcının mesajını Claude'a iletir.
    Yanıtta ticket tetikleyici varsa otomatik SQLite kaydı oluşturur.

    Request JSON:
        {
            "message": "Yazıcım bağlantı vermiyor",
            "history": [...]  # Opsiyonel sohbet geçmişi
        }

    Response JSON:
        {
            "success": bool,
            "response": str,
            "ticket_created": bool,
            "ticket": {...} | null,
        }
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "Mesaj boş olamaz."}), 400

    user_message = data.get("message", "").strip()
    conversation_history = data.get("history", [])

    if not user_message:
        return jsonify({"success": False, "error": "Mesaj boş olamaz."}), 400

    # Claude API'ye gönder
    claude_result = chat_with_claude(user_message, conversation_history)
    ticket_data = None

    # Ticket tetikleyici kontrolü
    if claude_result["should_create_ticket"]:
        ticket = _create_ticket(
            problem_description=f"Otomatik oluşturuldu — {user_message[:200]}",
            user_message=user_message,
            ai_response=claude_result["response"],
        )
        ticket_data = ticket.to_dict() if ticket else None

    return jsonify(
        {
            "success": claude_result["success"],
            "response": claude_result["response"],
            "ticket_created": claude_result["should_create_ticket"],
            "ticket": ticket_data,
        }
    )


@chatbot_bp.route("/create-ticket", methods=["POST"])
def create_ticket_manual():
    """
    Kullanıcı "Destek Talebi (Ticket) Aç" butonuna tıkladığında
    manuel olarak ticket oluşturur.

    Request JSON:
        {
            "description": "Sorun açıklaması",
            "user_message": "Kullanıcı mesajı"  # Opsiyonel
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Veri gönderilmedi."}), 400

    description = data.get("description", "Manuel destek talebi").strip()
    user_message = data.get("user_message", "")

    ticket = _create_ticket(
        problem_description=description,
        user_message=user_message,
        ai_response=None,
    )

    if ticket:
        return jsonify(
            {
                "success": True,
                "message": f"Destek talebi #{ticket.id} başarıyla oluşturuldu.",
                "ticket": ticket.to_dict(),
            }
        )
    else:
        return jsonify({"success": False, "error": "Ticket oluşturulamadı."}), 500


@chatbot_bp.route("/tickets", methods=["GET"])
def get_tickets():
    """Tüm aktif ve kapalı ticketları JSON olarak döndürür."""
    tickets = Ticket.query.order_by(Ticket.date_created.desc()).all()
    return jsonify(
        {
            "success": True,
            "tickets": [t.to_dict() for t in tickets],
            "total": len(tickets),
            "open_count": sum(1 for t in tickets if t.status == "Açık"),
        }
    )


@chatbot_bp.route("/ticket/<int:ticket_id>/close", methods=["POST"])
def close_ticket(ticket_id: int):
    """Belirtilen ticket'ı 'Çözüldü' olarak günceller."""
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = "Çözüldü"
    db.session.commit()
    return jsonify(
        {
            "success": True,
            "message": f"Ticket #{ticket_id} çözüldü olarak işaretlendi.",
            "ticket": ticket.to_dict(),
        }
    )


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def _create_ticket(
    problem_description: str,
    user_message: Optional[str] = None,
    ai_response: Optional[str] = None,
) -> Optional[Ticket]:
    """
    Veritabanına yeni bir ticket kaydı ekler.

    Returns:
        Ticket: Oluşturulan ticket nesnesi, hata olursa None.
    """
    try:
        ticket = Ticket(
            problem_description=problem_description,
            date_created=datetime.utcnow(),
            status="Açık",
            user_message=user_message,
            ai_response=ai_response,
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Ticket oluşturulamadı: {e}")
        return None
