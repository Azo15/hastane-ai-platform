"""
app/modules/chatbot/claude_client.py

AI Chatbot istemci yönetimi.
Önce ANTHROPIC_API_KEY dener, yoksa GROQ_API_KEY ile Groq/Llama'ya geçer.

Ticket tetikleme mantığı:
- AI yanıtına gizli marker [##TICKET_GEREKLI##] eklemesi istenir
- SADECE gerçekten çözülemez durumlarda bu marker kullanılır
- Marker kullanıcıya gösterilmez, arka planda ticket açılır
- Kullanıcı kendi "Destek Talebi Aç" butonuyla da açabilir
"""

from __future__ import annotations
import os
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

# Gizli marker — AI yanıtının sonuna sadece gerekliyse eklenir
TICKET_MARKER = "[##TICKET_GEREKLI##]"

# ─── IT Destek Asistanı Sistem Promptu (Yedek) ───────────────────────────────
DEFAULT_SYSTEM_PROMPT = """Sen bir hastane bilgi işlem (IT) destek asistanısın.
Hastane personelinin bilgisayar, yazıcı, internet, ağ ve HBYS (Hastane Bilgi Yönetim Sistemi) sorunlarına teknik çözüm üretirsin.
Nazik, profesyonel, kısa ve çözüm odaklı ol. Yanıtlarını her zaman Türkçe ver."""

TICKET_INSTRUCTION = """

==== TICKET KURALI (ÇOK ÖNEMLİ) ====
Yanıtının sonuna "[##TICKET_GEREKLI##]" işaretini SADECE şu durumlarda ekle:
1. Sorunu KESINLIKLE uzaktan çözemiyorsan (donanım arızası, fiziksel müdahale, kablo değişikliği, teknik ekibin gitmesi vb.)
2. Kullanıcı "ticket aç", "talep oluştur", "ekip çağır", "ekip yola çıksın", "ekip yönlendir" gibi bir istekte bulunuyorsa.

Selamlama, basit soru, yönlendirme, tavsiye, adım adım rehberlik gibi NORMAL yanıtlarda bu işareti KESİNLİKLE KULLANMA.
Yanıtın sonundaki bu işaret kullanıcıya gösterilmez; sistem otomatik ticket açar.
======================================"""

def get_dynamic_prompt() -> str:
    """Settings.json dosyasından dinamik prompt okur, sonuna ticket kuralını ekler."""
    base_prompt = DEFAULT_SYSTEM_PROMPT
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        settings_path = os.path.join(root, "instance", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                base_prompt = data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    except Exception as e:
        logger.warning(f"Dinamik prompt okunamadi: {e}")
        
    # Eğer prompt içinde ticket kuralı yoksa otomatik ekle
    if "TICKET_GEREKLI" not in base_prompt and "TICKET KURALI" not in base_prompt:
        base_prompt += TICKET_INSTRUCTION
        
    return base_prompt


def _get_provider():
    """
    Mevcut API anahtarına göre uygun sağlayıcıyı döndürür.
    Öncelik: Anthropic > Groq
    Returns: ('anthropic' | 'groq', client, model_name)
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            return "anthropic", client, "claude-3-5-haiku-20241022"
        except Exception as e:
            logger.warning(f"Anthropic baslatılamadı: {e}")

    if groq_key and groq_key != "your_groq_api_key_here":
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            return "groq", client, "llama-3.3-70b-versatile"
        except Exception as e:
            logger.warning(f"Groq baslatılamadı: {e}")

    return None, None, None


def should_create_ticket(response_text: str) -> bool:
    """Yanıtta gizli ticket marker veya bilet açıldığını/ekibin yola çıktığını bildiren ifadeler var mı kontrol eder."""
    if TICKET_MARKER in response_text:
        return True

    # Ekibin yola çıktığını veya kaydın açıldığını bildiren anlamsal yedek kelimeler
    indicators = [
        "yola çık",
        "yola koyul",
        "ekip yönlendir",
        "ekibim yönlendir",
        "talep oluştur",
        "bilet oluştur",
        "bilet aç",
        "destek talebi aç",
        "arıza kaydı oluştur",
        "kayıt açt",
        "fiziksel müdahale",
        "donanım arızası",
        "teknisyen"
    ]
    
    clean_text = response_text.lower()
    for ind in indicators:
        if ind in clean_text:
            return True
            
    return False


def clean_response(response_text: str) -> str:
    """Gizli markeri kullanıcı yanıtından kaldırır."""
    return response_text.replace(TICKET_MARKER, "").strip()


def chat_with_claude(
    user_message: str,
    conversation_history: Optional[list] = None,
) -> dict:
    """
    AI API'ye mesaj gönderir. Anthropic veya Groq kullanır.

    Returns:
        dict: {
            "success": bool,
            "response": str,       # Markersiz temiz yanıt
            "should_create_ticket": bool,
            "error": str | None,
            "provider": str,
        }
    """
    provider, client, model = _get_provider()

    if client is None:
        return {
            "success": False,
            "response": (
                "⚠️ API anahtarı bulunamadı.\n\n"
                "Ücretsiz test için:\n"
                "1. console.groq.com adresine gidin\n"
                "2. Ücretsiz API key alın\n"
                "3. .env dosyasına GROQ_API_KEY=gsk_... ekleyin\n"
                "4. Sunucuyu yeniden başlatın"
            ),
            "should_create_ticket": False,
            "error": "API key eksik",
            "provider": "none",
        }

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    try:
        dynamic_prompt = get_dynamic_prompt()
        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=dynamic_prompt,
                messages=messages,
            )
            raw_text = response.content[0].text

        elif provider == "groq":
            groq_messages = [{"role": "system", "content": dynamic_prompt}] + messages
            completion = client.chat.completions.create(
                model=model,
                messages=groq_messages,
                max_tokens=1024,
                temperature=0.5,
            )
            raw_text = completion.choices[0].message.content

        create_ticket = should_create_ticket(raw_text)
        clean_text   = clean_response(raw_text)

        logger.info(f"[{provider}] Yanıt alındı. Ticket tetiklendi: {create_ticket}")

        return {
            "success": True,
            "response": clean_text,
            "should_create_ticket": create_ticket,
            "error": None,
            "provider": provider,
        }

    except Exception as e:
        logger.error(f"[{provider}] API hatası: {e}")
        error_msg = str(e)

        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            msg = f"⚠️ {provider.capitalize()} API anahtarı geçersiz. .env dosyasını kontrol edin."
        elif "rate_limit" in error_msg.lower() or "429" in error_msg:
            msg = "⚠️ API kotası doldu. Lütfen birkaç saniye bekleyip tekrar deneyin."
        elif "connection" in error_msg.lower():
            msg = "⚠️ İnternet bağlantısı yok veya API servisine ulaşılamıyor."
        else:
            msg = f"⚠️ Bir hata oluştu: {error_msg[:100]}"

        return {
            "success": False,
            "response": msg,
            "should_create_ticket": False,
            "error": error_msg,
            "provider": provider,
        }
