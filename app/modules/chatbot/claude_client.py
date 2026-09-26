"""
app/modules/chatbot/claude_client.py

AI Chatbot istemci yönetimi.
Önce ANTHROPIC_API_KEY dener, yoksa GROQ_API_KEY ile Groq/Llama'ya geçer.

Ticket tetikleme mantığı:
- AI yanıtına gizli marker [##TICKET_GEREKLI##] eklemesi istenir.
- SADECE AI sorunu uzaktan çözemediğinde veya kullanıcı talep ettiğinde marker kullanılır.
- Marker kullanıcıya gösterilmez, arka planda ticket açılır.
"""

from __future__ import annotations
import os
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

# Gizli marker — AI yanıtının sonuna sadece ticket gerekiyorsa eklenir
TICKET_MARKER = "[##TICKET_GEREKLI##]"

# ─── IT Destek Asistanı Sistem Promptu ───────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = """Sen bir hastane bilgi işlem (IT) destek asistanısın.
Hastane personelinin bilgisayar, yazıcı, internet, ağ ve HBYS (Hastane Bilgi Yönetim Sistemi) sorunlarına teknik çözüm üretirsin.
Nazik, profesyonel, kısa ve çözüm odaklı ol. Yanıtlarını her zaman Türkçe ver.

==== ÖNEMLİ TICKET (DESTEK TALEBİ) KURALLARI ====
1. Kullanıcı bir sorun bildirdiğinde İLK OLARAK adım adım pratik çözüm rehberi sun. İLK YANITINDA KESİNLİKLE "[##TICKET_GEREKLI##]" İŞARETİNİ EKLEME VE BİLET OLUŞTURULDU DEME.
2. Çözüm sunduğun yanıtın sonunda kullanıcıyı nazikçe bilgilendir: "Lütfen bu adımları deneyin. Eğer sorununuz çözülmezse veya teknik ekip yönlendirilmesini isterseniz 'Çözülmedi' veya 'Ekip çağır' diyebilirsiniz."

3. Yanıtının en sonuna "[##TICKET_GEREKLI##]" gizli işaretini SADECE ve SADECE şu durumlarda ekle:
   a) Kullanıcı verdiğin adımları denediğini ve sorunun ÇÖZÜLMEDİĞİNİ söylediğinde (örneğin: "olmadı", "denedim yine çalışmıyor", "sorun devam ediyor", "çözülmedi").
   b) Kullanıcı açıkça destek talebi/bilet/ekip istediğinde (örneğin: "ticket aç", "ekip çağır", "destek talebi oluştur", "teknisyen gönder").
   c) Sorun uzaktan çözülemeyecek ağır fiziksel/donanımsal bir arıza olduğunda (örneğin: "kablo koptu", "ekran kırıldı", "cihaz yandı", "duman çıktı").

4. Yanıtının sonuna "[##TICKET_GEREKLI##]" işaretini eklediğin zaman yanıt metninde kullanıcıya şöyle bilgi ver: "Talebiniz üzerine otomatik bir teknik destek talebi (ticket) oluşturdum, teknik ekibimiz en kısa sürede müdahale edecektir."
================================================"""


def get_dynamic_prompt() -> str:
    """Settings.json dosyasından dinamik prompt okur, sistem kurallarını korur."""
    base_prompt = DEFAULT_SYSTEM_PROMPT
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        settings_path = os.path.join(root, "instance", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_prompt = data.get("system_prompt", "").strip()
                if custom_prompt:
                    base_prompt = custom_prompt
    except Exception as e:
        logger.warning(f"Dinamik prompt okunamadi: {e}")
        
    if "[##TICKET_GEREKLI##]" not in base_prompt:
        base_prompt = base_prompt + "\n\n" + DEFAULT_SYSTEM_PROMPT
        
    return base_prompt


def _get_provider():
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
            return "groq", client, "qwen/qwen3.8-27b"
        except Exception as e:
            logger.warning(f"Groq baslatılamadı: {e}")

    return None, None, None


def should_create_ticket(response_text: str) -> bool:
    """
    Yanıtta ticket açılması gerektiğini gösteren gizli marker var mı kontrol eder.
    SADECE AI yanıtının sonunda [##TICKET_GEREKLI##] gizli markeri bulunduğunda ticket açılır.
    """
    return TICKET_MARKER in response_text


def clean_response(response_text: str) -> str:
    """Gizli markeri kullanıcı yanıtından kaldırır."""
    return response_text.replace(TICKET_MARKER, "").strip()


def chat_with_claude(
    user_message: str,
    conversation_history: Optional[list] = None,
) -> dict:
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
                temperature=0.1,
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
