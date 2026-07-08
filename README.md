# 🏥 Hastane AI — Kurumsal Yapay Zeka ve Operasyon Platformu

Hastane AI, sağlık kuruluşlarının operasyonel verimliliğini artırmak ve IT destek süreçlerini otomatize etmek için geliştirilmiş modern, yapay zeka destekli bir yönetim panelidir. Platform; poliklinik personeli (HBYS kullanıcıları) ve bilgi işlem sorumluları olmak üzere iki farklı rol için özel deneyimler ve araçlar sunar.

---

## 🚀 Öne Çıkan Özellikler

### 1. Rol Tabanlı Giriş ve Yetkilendirme
*   **HBYS Personeli Paneli:** Doktorlar, hemşireler ve sekreterler gibi poliklinik personellerine yönelik sadeleştirilmiş arayüz. Personeller sadece kendi oluşturdukları arıza/destek taleplerini görür.
*   **Bilgi İşlem Sorumlusu Paneli:** Hastanenin tüm IT operasyonlarını yöneten sistem yöneticisi ekranı. Tüm destek taleplerini, sistem ayarlarını, API anahtarlarını ve performans raporlarını yönetir.

### 2. Akıllı IT Destek Chatbotu
*   **Yapay Zeka Motoru:** Anthropic Claude veya Groq Llama 3.3 entegrasyonu ile çalışır.
*   **Akıllı Bilet (Ticket) Tetikleme:** Personelin bildirdiği teknik arızaları analiz ederek fiziksel müdahale gerektiren durumlarda veya personel talep ettiğinde sağ taraftaki panele otomatik destek talebi açar.
*   **Geçmiş Sohbetler Sidebar'ı:** Kullanıcıların geçmiş chatbot diyalogları SQLite veritabanında güvenle saklanır, listeden seçilerek anında yüklenebilir veya silinebilir.

### 3. No-Show Randevu Risk Analizi
*   **Machine Learning Altyapısı:** LightGBM modeli (`lightgbm_model.pkl`) ile eğitilmiş randevuya gelmeme (no-show) riski tahmin motoru.
*   **AJAX Entegrasyonu:** Sayfa yenilenmeden, form verileri arka planda işlenerek randevunun risk skoru, risk rengi ve yapay zeka önerisi animasyonlu grafiklerle dinamik olarak sunulur.

### 4. Gelişmiş Raporlama & Veri Aktarımı
*   **PDF Raporu:** CSS Print optimizasyonu sayesinde sayfa tasarımı bozulmadan, gereksiz menüler (sidebar vb.) gizlenerek temiz bir A4 PDF çıktısı alınmasını sağlar.
*   **Excel (CSV) Aktarımı:** Veritabanındaki tüm IT destek biletlerini tek tuşla CSV formatında indirerek Excel gibi araçlarla analiz etme imkanı sunar.
 
---

## 🛠️ Kullanılan Teknolojiler

*   **Backend:** Python 3.9+, Flask Web Framework, Flask-SQLAlchemy (ORM)
*   **Veritabanı:** SQLite (Local veri saklama katmanı)
*   **Makine Öğrenmesi (ML):** LightGBM, Pandas, Scikit-learn
*   **Yapay Zeka (AI):** Groq API (Llama 3.3 70B), Anthropic API (Claude 3.5 Haiku)
*   **Frontend:** HTML5, CSS3 (Vanilla Premium Grid/Flex Layouts, CSS Variables), JavaScript (ES6+ Vanilla AJAX)
*   **Tasarım & İkonlar:** Google Fonts (Outfit & Inter), Bootstrap Icons

---

## 📦 Proje Yapısı

```text
Staj2/
│
├── app/
│   ├── modules/
│   │   ├── chatbot/          # AI Destek Chatbot modülü (Rotalar ve API istemcisi)
│   │   └── no_show/          # No-Show tahmin modülü (Model yükleme ve tahmin rotaları)
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css     # Premium tasarım sistemi ve responsive düzenler
│   │   └── js/
│   │       └── main.js       # AJAX, Chatbot geçmişi ve dinamik UI mantığı
│   │
│   ├── templates/            # HTML Şablonları (base, index, login, reports vb.)
│   │
│   ├── database.py           # SQLAlchemy Veri modelleri (Ticket & Conversation)
│   └── main_routes.py        # Giriş, oturum yönetimi, raporlama ve ayar rotaları
│
├── instance/                 # settings.json ve local SQLite veritabanı dosyası
├── models/                   # LightGBM eğitilmiş model dosyası (lightgbm_model.pkl)
├── requirements.txt          # Gerekli kütüphaneler listesi
├── run.py                    # Uygulamayı başlatan ana Python scripti
└── .env                      # API anahtarları ve gizli ayarlar (Git'e eklenmez)
```

---

## 🔧 Kurulum ve Çalıştırma

Platformu kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

### 1. Depoyu Klonlayın
```bash
git clone <depo_adresi>
cd Staj2
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktif Edin
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Çevre Değişkenlerini Tanımlayın (`.env`)
Proje dizininde yer alan `.env.example` dosyasını kopyalayarak `.env` adında yeni bir dosya oluşturun ve API anahtarınızı girin:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=super-secret-key-change-me

# Yapay Zeka Sağlayıcıları (En az bir tanesi gereklidir)
GROQ_API_KEY=gsk_your_groq_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 5. Uygulamayı Başlatın
```bash
python run.py
```
Uygulama başlatıldıktan sonra tarayıcınızdan **`http://127.0.0.1:5000`** adresine giderek platforma erişebilirsiniz.

---

## 🔑 Demo Kullanıcı Giriş Bilgileri

Kolay test edilebilmesi için giriş ekranında şifre gerektirmeyen **"Hızlı Giriş Seçeneği"** kartları bulunmaktadır. Manuel giriş yapmak isterseniz bilgiler aşağıdaki gibidir:

| Kullanıcı Adı | Şifre | Rol | Yetkiler |
| :--- | :--- | :--- | :--- |
| **sekreter** | 123 | **HBYS Kullanıcısı** | Sadece kendi destek biletlerini ve sohbet geçmişini görür. Ayarlar ve Raporlar sayfaları gizlidir. |
| **admin** | 123 | **Bilgi İşlem Sorumlusu** | Tüm sistemi yönetir. Ayarlar, Raporlar ve tüm bilet listelerine erişebilir. |

---

## 🎓 Geliştirici Bilgileri & Lisans
Bu proje, Kırklareli Üniversitesi Yazılım Mühendisliği Bölümü öğrencisi **Azo İSMAİL** tarafından staj operasyonları ve proje çalışmaları kapsamında geliştirilmiştir. Tüm hakları saklıdır.
