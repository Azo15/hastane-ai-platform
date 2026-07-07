"""
app/modules/no_show/routes.py — No-Show Tahmin Rotaları

/no-show/          → Dashboard + haftalık yüksek riskli randevular
/no-show/predict   → POST: Tekli randevu tahmin API'si
"""

from flask import render_template, request, jsonify
from . import no_show_bp
from .model_utils import predict_no_show


# ─── Haftalık yüksek riskli simülasyon verisi ────────────────────────────────
# Gerçek uygulamada bu veriler veritabanından çekilmelidir.
SAMPLE_HIGH_RISK_APPOINTMENTS = [
    {
        "id": "RAN-2024-001",
        "hasta_adi": "Ahmet Yılmaz",
        "yas": 38,
        "tarih": "08.07.2024",
        "saat": "09:30",
        "poliklinik": "Kardiyoloji",
        "risk_skoru": 87.3,
        "onceki_kaçirma": 3,
        "sms_gonderildi": "Hayır",
    },
    {
        "id": "RAN-2024-002",
        "hasta_adi": "Fatma Kaya",
        "yas": 24,
        "tarih": "08.07.2024",
        "saat": "11:00",
        "poliklinik": "Dahiliye",
        "risk_skoru": 79.6,
        "onceki_kaçirma": 2,
        "sms_gonderildi": "Hayır",
    },
    {
        "id": "RAN-2024-003",
        "hasta_adi": "Mehmet Demir",
        "yas": 19,
        "tarih": "09.07.2024",
        "saat": "10:15",
        "poliklinik": "Ortopedi",
        "risk_skoru": 82.1,
        "onceki_kaçirma": 4,
        "sms_gonderildi": "Evet",
    },
    {
        "id": "RAN-2024-004",
        "hasta_adi": "Zeynep Arslan",
        "yas": 45,
        "tarih": "09.07.2024",
        "saat": "14:30",
        "poliklinik": "Nöroloji",
        "risk_skoru": 73.8,
        "onceki_kaçirma": 1,
        "sms_gonderildi": "Hayır",
    },
    {
        "id": "RAN-2024-005",
        "hasta_adi": "Ali Çelik",
        "yas": 31,
        "tarih": "10.07.2024",
        "saat": "08:45",
        "poliklinik": "Psikiyatri",
        "risk_skoru": 91.2,
        "onceki_kaçirma": 5,
        "sms_gonderildi": "Hayır",
    },
    {
        "id": "RAN-2024-006",
        "hasta_adi": "Ayşe Şahin",
        "yas": 27,
        "tarih": "10.07.2024",
        "saat": "13:00",
        "poliklinik": "Göz Hastalıkları",
        "risk_skoru": 76.4,
        "onceki_kaçirma": 2,
        "sms_gonderildi": "Evet",
    },
    {
        "id": "RAN-2024-007",
        "hasta_adi": "Hasan Öztürk",
        "yas": 52,
        "tarih": "11.07.2024",
        "saat": "09:00",
        "poliklinik": "Üroloji",
        "risk_skoru": 84.7,
        "onceki_kaçirma": 3,
        "sms_gonderildi": "Hayır",
    },
]
# ─────────────────────────────────────────────────────────────────────────────


@no_show_bp.route("/", methods=["GET"])
def dashboard():
    """No-Show analiz dashboard'u — haftalık yüksek riskli randevuları listeler."""
    return render_template(
        "no_show.html",
        high_risk_appointments=SAMPLE_HIGH_RISK_APPOINTMENTS,
        prediction_result=None,
    )


@no_show_bp.route("/predict", methods=["POST"])
def predict():
    """
    Tekli randevu no-show tahmin API'si.
    Form POST veya JSON POST kabul eder.
    HTML form için: sonucu sayfada gösterir.
    """
    if request.is_json:
        # AJAX / JSON isteği → JSON yanıt döndür
        form_data = request.get_json()
        result = predict_no_show(form_data)
        return jsonify(result)

    # HTML form gönderimi → sayfayı sonuçla yeniden render et
    form_data = request.form.to_dict()
    result = predict_no_show(form_data)

    return render_template(
        "no_show.html",
        high_risk_appointments=SAMPLE_HIGH_RISK_APPOINTMENTS,
        prediction_result=result,
        form_data=form_data,
    )
