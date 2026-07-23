"""
app/modules/chatbot/routes.py — IT Destek Chatbot Rotaları

/chatbot/              → Chat arayüzü + aktif ticket listesi (arama/filtre/sayfalama destekli)
/chatbot/send          → POST: Mesaj gönder, Claude yanıtı al, ticket kontrol et
/chatbot/create-ticket → POST: Manuel ticket oluştur (buton tıklaması)
/chatbot/tickets       → GET: Tüm aktif ticketları JSON olarak döndür
/chatbot/ticket/<id>/close → POST: Ticket'ı kapat (sahiplik/rol kontrollü)
"""

from datetime import datetime
from flask import render_template, request, jsonify, session, abort
from . import chatbot_bp
from .claude_client import chat_with_claude
from ...database import db, Ticket, Conversation, get_visible_tickets_query

TICKETS_PER_PAGE = 15


@chatbot_bp.route("/", methods=["GET"])
def index():
    """Chat arayüzü ve aktif ticket listesi. Rol bazlı filtreleme + arama/durum filtresi + sayfalama."""
    username = session.get("username", "admin")
    role = session.get("user_role_code", "admin")

    status = request.args.get("status", "").strip() or None
    search = request.args.get("q", "").strip() or None
    page = request.args.get("page", 1, type=int)

    pagination = get_visible_tickets_query(role, username, status=status, search=search).paginate(
        page=page, per_page=TICKETS_PER_PAGE, error_out=False
    )

    conversations = Conversation.query.filter_by(username=username).order_by(Conversation.date_created.desc()).all()
    return render_template(
        "chatbot.html",
        tickets=pagination.items,
        pagination=pagination,
        current_status=status or "",
        current_search=search or "",
        conversations=conversations,
    )


@chatbot_bp.route("/send", methods=["POST"])
def send_message():
    """
    Kullanıcının mesajını Claude'a iletir.
    Yanıtta ticket tetikleyici varsa otomatik SQLite kaydı oluşturur.
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "Mesaj boş olamaz."}), 400

    user_message = data.get("message", "").strip()
    conversation_history = data.get("history", [])
    username = session.get("username", "admin")

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
            created_by=username
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
    """Manuel olarak bilet oluşturur. Bilete oluşturan kullanıcı atanır."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Veri gönderilmedi."}), 400

    description = data.get("description", "Manuel destek talebi").strip()
    user_message = data.get("user_message", "")
    username = session.get("username", "admin")

    ticket = _create_ticket(
        problem_description=description,
        user_message=user_message,
        ai_response=None,
        created_by=username
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
    """Tüm aktif ve kapalı ticketları JSON olarak döndürür. Rol bazlı filtreleme uygulanır."""
    username = session.get("username", "admin")
    role = session.get("user_role_code", "admin")

    tickets = get_visible_tickets_query(role, username).all()

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
    """Belirtilen ticket'ı 'Çözüldü' olarak günceller.

    Sadece admin veya biletin sahibi kapatabilir — aksi halde herhangi bir
    kullanıcı ID'sini tahmin ederek başkasının biletini kapatabilirdi (IDOR).
    """
    username = session.get("username", "admin")
    role = session.get("user_role_code", "admin")

    ticket = Ticket.query.get_or_404(ticket_id)
    if role != "admin" and ticket.created_by != username:
        abort(403)

    ticket.status = "Çözüldü"
    db.session.commit()
    return jsonify(
        {
            "success": True,
            "message": f"Ticket #{ticket_id} çözüldü olarak işaretlendi.",
            "ticket": ticket.to_dict(),
        }
    )


# ─── GEÇMİŞ KONUŞMA ROTALARI ──────────────────────────────────────────────────

@chatbot_bp.route("/conversation/save", methods=["POST"])
def save_conversation():
    """Aktif konuşma geçmişini veritabanına kaydeder."""
    import json
    data = request.get_json() or {}
    username = session.get("username", "admin")
    conv_id = data.get("conversation_id")
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"success": False, "error": "Boş sohbet kaydedilemez."})

    # İlk kullanıcı mesajının içeriğini başlık yapalım
    user_msgs = [m for m in messages if m.get("role") == "user"]
    first_user_content = user_msgs[0].get("content", "Yeni Konuşma") if user_msgs else "Yeni Konuşma"
    title = first_user_content[:30] + ("..." if len(first_user_content) > 30 else "")

    if conv_id:
        conv = Conversation.query.filter_by(id=conv_id, username=username).first()
        if conv:
            conv.messages_json = json.dumps(messages, ensure_ascii=False)
            conv.title = title
            db.session.commit()
            return jsonify({"success": True, "conversation_id": conv.id, "title": title})

    conv = Conversation(
        username=username,
        title=title,
        messages_json=json.dumps(messages, ensure_ascii=False)
    )
    db.session.add(conv)
    db.session.commit()
    return jsonify({"success": True, "conversation_id": conv.id, "title": title})


@chatbot_bp.route("/conversations", methods=["GET"])
def get_conversations():
    """Kullanıcının geçmiş konuşmalarını çeker."""
    username = session.get("username", "admin")
    convs = Conversation.query.filter_by(username=username).order_by(Conversation.date_created.desc()).all()
    return jsonify({
        "success": True,
        "conversations": [c.to_dict() for c in convs]
    })


@chatbot_bp.route("/conversation/<int:conv_id>/delete", methods=["POST", "DELETE"])
def delete_conversation(conv_id: int):
    """Belirli bir geçmiş konuşmayı siler."""
    username = session.get("username", "admin")
    conv = Conversation.query.filter_by(id=conv_id, username=username).first_or_404()
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"success": True, "message": "Konuşma geçmişi başarıyla silindi."})


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def _create_ticket(
    problem_description,
    user_message = None,
    ai_response = None,
    created_by = "admin"
):
    """Veritabanına yeni bir ticket kaydı ekler."""
    try:
        ticket = Ticket(
            problem_description=problem_description,
            date_created=datetime.utcnow(),
            status="Açık",
            user_message=user_message,
            ai_response=ai_response,
            created_by=created_by
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Ticket oluşturulamadı: {e}")
        return None
