"""
app/modules/no_show/model_utils.py

LightGBM modelini yükler ve randevu kaçırma tahminleri üretir.

Eğer eğitilmiş model dosyası bulunamazsa, sistemi çalışır halde tutmak için
gerçekçi özelliklerle eğitilmiş bir yedek model otomatik olarak oluşturulur
ve kaydedilir. Üretim ortamında bu yedek model gerçek model dosyasıyla
değiştirilmelidir.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Model dosyasının yolu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "models", "lightgbm_model.pkl")

# Global model referansı (tek seferinde yüklenir)
_model = None


def _build_fallback_model():
    """
    Gerçek model dosyası yoksa gerçekçi bir yedek LightGBM modeli oluşturur.
    Bu fonksiyon yalnızca geliştirme/demo ortamı içindir.
    """
    try:
        import lightgbm as lgb
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        logger.warning("Gerçek model bulunamadı — yedek demo modeli oluşturuluyor.")

        # Sentetik eğitim verisi oluştur (gerçek veri dağılımlarına yakın)
        np.random.seed(42)
        n_samples = 5000

        # Özellikler: age, scholarship, hipertension, diabetes, alcoholism,
        # handcap, sms_received, days_waiting, previous_noshow_count
        age = np.random.randint(0, 95, n_samples).astype(float)
        scholarship = np.random.binomial(1, 0.25, n_samples).astype(float)
        hipertension = np.random.binomial(1, 0.20, n_samples).astype(float)
        diabetes = np.random.binomial(1, 0.07, n_samples).astype(float)
        alcoholism = np.random.binomial(1, 0.03, n_samples).astype(float)
        handcap = np.random.binomial(1, 0.02, n_samples).astype(float)
        sms_received = np.random.binomial(1, 0.32, n_samples).astype(float)
        days_waiting = np.random.randint(0, 180, n_samples).astype(float)
        previous_noshow = np.random.randint(0, 5, n_samples).astype(float)

        X = np.column_stack([
            age, scholarship, hipertension, diabetes,
            alcoholism, handcap, sms_received, days_waiting, previous_noshow
        ])

        # Gerçekçi etiket üretimi (mantıksal kural bazlı)
        noshow_prob = (
            0.15
            + 0.12 * (days_waiting > 30)
            + 0.08 * (sms_received == 0)
            + 0.10 * (scholarship == 1)
            + 0.15 * (previous_noshow > 1)
            - 0.05 * (age > 60)
            + np.random.normal(0, 0.05, n_samples)
        )
        noshow_prob = np.clip(noshow_prob, 0, 1)
        y = (noshow_prob > 0.25).astype(int)

        # LightGBM modelini eğit
        model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
        model.fit(X, y)

        # Modeli kaydet
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)

        logger.info(f"Yedek model oluşturuldu ve kaydedildi: {MODEL_PATH}")
        return model

    except Exception as e:
        logger.error(f"Yedek model oluşturulamadı: {e}")
        return None


def load_model():
    """
    LightGBM modelini yükler. Model zaten yüklüyse önbellekten döner.
    """
    global _model
    if _model is not None:
        return _model

    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            logger.info(f"Model başarıyla yüklendi: {MODEL_PATH}")
        except Exception as e:
            logger.error(f"Model yüklenemedi: {e}")
            _model = _build_fallback_model()
    else:
        _model = _build_fallback_model()

    return _model


def prepare_features(form_data: dict) -> np.ndarray:
    """
    Form verilerini modelin beklediği numpy dizisine dönüştürür.

    Beklenen form alanları:
        age            : int — Hasta yaşı
        scholarship    : 0/1 — Burs/sosyal yardım alıyor mu?
        hipertension   : 0/1 — Hipertansiyon var mı?
        diabetes       : 0/1 — Diyabet var mı?
        alcoholism     : 0/1 — Alkol bağımlılığı var mı?
        handcap        : 0/1 — Engel durumu
        sms_received   : 0/1 — SMS bildirimi gönderildi mi?
        days_waiting   : int — Randevu bekleme süresi (gün)
        previous_noshow: int — Daha önce kaç kez gelmedi?
    """
    features = [
        float(form_data.get("age", 30)),
        float(form_data.get("scholarship", 0)),
        float(form_data.get("hipertension", 0)),
        float(form_data.get("diabetes", 0)),
        float(form_data.get("alcoholism", 0)),
        float(form_data.get("handcap", 0)),
        float(form_data.get("sms_received", 0)),
        float(form_data.get("days_waiting", 0)),
        float(form_data.get("previous_noshow", 0)),
    ]
    return np.array(features).reshape(1, -1)


def predict_no_show(form_data: dict) -> dict:
    """
    Randevu kaçırma tahminini döndürür.

    Returns:
        dict: {
            "prediction": int (0 veya 1),
            "probability": float (0.0 - 1.0),
            "risk_score": float (0 - 100),
            "risk_level": str ("Düşük" / "Orta" / "Yüksek"),
            "risk_color": str ("success" / "warning" / "danger"),
        }
    """
    model = load_model()
    if model is None:
        return {
            "prediction": 0,
            "probability": 0.0,
            "risk_score": 0.0,
            "risk_level": "Bilinmiyor",
            "risk_color": "secondary",
            "error": "Model yüklenemedi.",
        }

    X = prepare_features(form_data)

    prediction = int(model.predict(X)[0])
    probability = float(model.predict_proba(X)[0][1])
    risk_score = round(probability * 100, 1)

    # Risk seviyesi ve renk sınıflandırması
    if risk_score <= 30:
        risk_level = "Düşük Risk"
        risk_color = "success"
    elif risk_score <= 70:
        risk_level = "Orta Risk"
        risk_color = "warning"
    else:
        risk_level = "Yüksek Risk"
        risk_color = "danger"

    return {
        "prediction": prediction,
        "probability": probability,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
    }
