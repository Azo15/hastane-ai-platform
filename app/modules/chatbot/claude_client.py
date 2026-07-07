"""
app/modules/chatbot/claude_client.py

Anthropic Claude API istemci yönetimi.

Hastane IT Destek Asistanı sistem promptuyla yapılandırılmış Claude
API'sine mesaj gönderir ve yanıt + ticket tetikleyici bilgisini döndürür.
"""

from __future__ import annotations
import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

# ─── IT Destek Asistanı Sistem Promptu ───────────────────────────────────────
SYSTEM_PROMPT = """Sen bir hastane bilgi işlem (IT) destek asistanısın. \
Hastane personelinin bilgisayar, yazıcı, internet, ağ ve HBYS (Hastane Bilgi \
Yönetim Sistemi) arızalarına ve teknik sorularına çözüm üretirsin. \
Nazik, profesyonel, kısa ve teknik çözüm odaklı olmalısın.

Eğer sorunu çözemiyorsan veya daha ileri teknik müdahale gerekiyorsa, \
yanıtında "talebinizi oluşturuyorum", "teknik ekibe iletiyorum" veya \
"destek talebi açıyorum" ifadelerinden birini kullanarak \
personeli yönlendir. Bu ifadeler sistem tarafından otomatik ticket oluşturmak \
için kullanılır.

Yanıtlarını her zaman Türkçe ver."""
# ─────────────────────────────────────────────────────────────────────────────

# Ticket açılmasını tetikleyen anahtar kelimeler
TICKET_TRIGGER_PHRASES = [
    "talebinizi oluşturuyorum",
    "teknik ekibe iletiyorum",
    "destek talebi açıyorum",
    "ekibimize bildiriyorum",
    "ticket açıyorum",
    "çözüm ekibine yönlendiriyorum",
]


def _get_client() -> anthropic.Anthropic:
    """Anthropic istemcisini oluşturur ve döndürür."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        raise ValueError(
            "ANTHROPIC_API_KEY ortam değişkeni tanımlı değil veya varsayılan değerde. "
            ".env dosyasını güncelleyin."
        )
    return anthropic.Anthropic(api_key=api_key)


def should_create_ticket(response_text: str) -> bool:
    """
    Claude'un yanıtında ticket tetikleyici anahtar kelime var mı kontrol eder.

    Args:
        response_text: Claude'un yanıt metni

    Returns:
        bool: Ticket oluşturulmalıysa True
    """
    response_lower = response_text.lower()
    return any(phrase in response_lower for phrase in TICKET_TRIGGER_PHRASES)


def chat_with_claude(
    user_message: str,
    conversation_history: Optional[list] = None,
) -> dict:
    """
    Claude API'ye mesaj gönderir ve yanıtı döndürür.

    Args:
        user_message: Kullanıcının mesajı
        conversation_history: Önceki mesajların listesi (çok turlu sohbet desteği)
            Örnek: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        dict: {
            "success": bool,
            "response": str,           # Claude'un yanıtı
            "should_create_ticket": bool,  # Ticket oluşturulmalı mı?
            "error": str | None,       # Hata varsa
        }
    """
    try:
        client = _get_client()

        # Sohbet geçmişini hazırla
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        response_text = response.content[0].text
        create_ticket = should_create_ticket(response_text)

        logger.info(
            f"Claude yanıtı alındı. Ticket tetiklendi: {create_ticket}"
        )

        return {
            "success": True,
            "response": response_text,
            "should_create_ticket": create_ticket,
            "error": None,
        }

    except ValueError as e:
        logger.error(f"API anahtarı hatası: {e}")
        return {
            "success": False,
            "response": (
                "⚠️ API bağlantısı kurulamadı. Lütfen sistem yöneticinize başvurun. "
                "(.env dosyasındaki ANTHROPIC_API_KEY değerini kontrol edin)"
            ),
            "should_create_ticket": False,
            "error": str(e),
        }

    except anthropic.APIConnectionError as e:
        logger.error(f"Anthropic API bağlantı hatası: {e}")
        return {
            "success": False,
            "response": "⚠️ Yapay zeka servisine bağlanılamadı. İnternet bağlantınızı kontrol edin.",
            "should_create_ticket": False,
            "error": str(e),
        }

    except anthropic.RateLimitError as e:
        logger.error(f"Anthropic API kota hatası: {e}")
        return {
            "success": False,
            "response": "⚠️ Yapay zeka servisi geçici olarak meşgul. Lütfen birkaç saniye sonra tekrar deneyin.",
            "should_create_ticket": False,
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Beklenmedik Claude API hatası: {e}")
        return {
            "success": False,
            "response": f"⚠️ Bir hata oluştu: {str(e)}",
            "should_create_ticket": False,
            "error": str(e),
        }
