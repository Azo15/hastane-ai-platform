"""
app/main_routes.py — Ana Sayfa, Ayarlar ve Raporlar rotaları
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .database import db, Ticket

main_bp = Blueprint("main", __name__)

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "settings.json")

def load_settings():
    """settings.json dosyasını yükler, yoksa varsayılanları oluşturur."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        defaults = {
            "hospital_name": "Hastane AI",
            "system_prompt": (
                "Sen bir hastane bilgi işlem (IT) destek asistanısın.\n"
                "Hastane personelinin bilgisayar, yazıcı, internet, ağ ve HBYS sorunlarına teknik çözüm üretirsin.\n"
                "Nazik, profesyonel ve çözüm odaklı ol. Yanıtlarını her zaman Türkçe ver."
            ),
            "default_provider": "groq"
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(defaults, f, indent=4, ensure_ascii=False)
        return defaults
    
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"hospital_name": "Hastane AI"}

def save_settings(data):
    """Ayarları settings.json dosyasına kaydeder."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_env_variable(key, value):
    """.env dosyasındaki ilgili değişkeni günceller veya ekler."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    
    # Çalışma zamanında os.environ'u da güncelle ki sunucu restart istemeden çalışsın
    os.environ[key] = value
    
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
        return
        
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    replaced = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            replaced = True
        else:
            new_lines.append(line)
            
    if not replaced:
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


@main_bp.route("/")
def index():
    """Karşılama ekranı — Hastane AI Platformu genel özet paneli. Rol bazlı istatistikler."""
    username = session.get("username", "admin")
    role = session.get("user_role_code", "admin")

    # SQLite veritabanından rol bazlı sayıları çekelim
    try:
        if role == "admin":
            tickets = Ticket.query.all()
        else:
            tickets = Ticket.query.filter_by(created_by=username).all()
            
        open_t = sum(1 for t in tickets if t.status == "Açık")
        resolved_t = sum(1 for t in tickets if t.status == "Çözüldü")
    except Exception:
        open_t, resolved_t = 0, 0

    stats = {
        "total_appointments": 1284,
        "high_risk_count": 87,
        "open_tickets": open_t,
        "resolved_tickets": resolved_t,
        "no_show_rate": 22.4,
        "ai_accuracy": 91.7,
    }
    return render_template("index.html", stats=stats)


@main_bp.route("/settings", methods=["GET", "POST"])
def settings():
    """Sistem ayarları sayfası."""
    current_settings = load_settings()
    
    if request.method == "POST":
        # Form verilerini al
        hospital_name = request.form.get("hospital_name", "Hastane AI").strip()
        system_prompt = request.form.get("system_prompt", "").strip()
        default_provider = request.form.get("default_provider", "groq")
        
        anthropic_key = request.form.get("anthropic_key", "").strip()
        groq_key = request.form.get("groq_key", "").strip()
        
        # settings.json güncelle
        current_settings["hospital_name"] = hospital_name
        current_settings["system_prompt"] = system_prompt
        current_settings["default_provider"] = default_provider
        save_settings(current_settings)
        
        # API anahtarlarını .env dosyasına yaz (boş değilse)
        if anthropic_key:
            update_env_variable("ANTHROPIC_API_KEY", anthropic_key)
        if groq_key:
            update_env_variable("GROQ_API_KEY", groq_key)
            
        flash("Ayarlar başarıyla güncellendi!", "success")
        return redirect(url_for("main.settings"))

    # Mevcut API anahtarlarını .env veya os.environ'dan oku (UI'da göstermek için)
    env_keys = {
        "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "groq_key": os.environ.get("GROQ_API_KEY", "")
    }
    
    # Güvenlik amacıyla API key'leri maskele (örn: gsk_am...mBDA)
    masked_keys = {}
    for k, val in env_keys.items():
        if val and val != "your_anthropic_api_key_here" and val != "your_groq_api_key_here":
            if len(val) > 10:
                masked_keys[k] = val[:6] + "..." + val[-6:]
            else:
                masked_keys[k] = val
        else:
            masked_keys[k] = ""

    return render_template("settings.html", settings=current_settings, keys=masked_keys)


@main_bp.route("/reports")
def reports():
    """Sistem analiz ve performans raporları sayfası."""
    # Grafik verilerini oluşturup HTML'e gönder
    try:
        tickets = Ticket.query.all()
        open_t = sum(1 for t in tickets if t.status == "Açık")
        resolved_t = sum(1 for t in tickets if t.status == "Çözüldü")
    except Exception:
        open_t, resolved_t = 0, 0

    # Kategorilere göre dağılım (AI yardımıyla veya mock)
    # Veritabanında kategori olmadığından, problem açıklamalarındaki anahtar kelimelere göre basitçe sınıflandıralım
    categories = {
        "HBYS / Yazılım": 0,
        "Yazıcı / Donanım": 0,
        "İnternet / Ağ": 0,
        "Şifre / Giriş": 0,
        "Diğer": 0
    }
    
    try:
        for t in tickets:
            desc = (t.problem_description or "").lower()
            if "hbys" in desc or "sistem" in desc or "yazılım" in desc:
                categories["HBYS / Yazılım"] += 1
            elif "yazıcı" in desc or "kablo" in desc or "donanım" in desc:
                categories["Yazıcı / Donanım"] += 1
            elif "internet" in desc or "ağ" in desc or "wifi" in desc or "bağlantı" in desc:
                categories["İnternet / Ağ"] += 1
            elif "şifre" in desc or "parola" in desc or "giriş" in desc:
                categories["Şifre / Giriş"] += 1
            else:
                categories["Diğer"] += 1
    except Exception:
        pass

    # No-Show tahmin verileri için istatistik şablonu (Düşük, Orta, Yüksek riskli randevu sayıları)
    no_show_stats = {
        "low_risk": 756,
        "medium_risk": 328,
        "high_risk": 200
    }

    return render_template("reports.html", 
                           ticket_stats={"open": open_t, "resolved": resolved_t, "total": open_t + resolved_t},
                           categories=categories,
                           no_show_stats=no_show_stats)


# ─── OTURUM VE YETKİLENDİRME (DEMO USERS) ────────────────────────────────────
DEMO_USERS = {
    "sekreter": {
        "password": "123",
        "name": "HBYS Personeli",
        "role": "HBYS Kullanıcısı",
        "role_code": "sekreter"
    },
    "admin": {
        "password": "123",
        "name": "Bilgi İşlem",
        "role": "Bilgi İşlem Sorumlusu",
        "role_code": "admin"
    }
}

@main_bp.before_app_request
def check_login():
    """Giriş yapılmamışsa giriş sayfasına yönlendir."""
    # Giriş gerekmeyen rotalar ve statik dosyalar
    allowed_routes = ["main.login", "static"]
    if request.endpoint and request.endpoint not in allowed_routes:
        if not session.get("logged_in"):
            return redirect(url_for("main.login"))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    """Rol bazlı giriş ekranı."""
    if session.get("logged_in"):
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = DEMO_USERS.get(username)
        if user and user["password"] == password:
            session["logged_in"] = True
            session["username"] = username
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            session["user_role_code"] = user["role_code"]
            flash(f"Hoş geldiniz, {user['name']}!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Geçersiz kullanıcı adı veya şifre.", "error")

    return render_template("login.html")

@main_bp.route("/logout")
def logout():
    """Oturumu sonlandır."""
    session.clear()
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect(url_for("main.login"))
