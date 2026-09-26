"""
app/modules/no_show/routes.py — No-Show Tahmin Rotaları

/no-show/          → Dashboard + kaydedilmiş son tahminler
/no-show/predict   → POST: Tekli randevu tahmin API'si (sonuç DB'ye kalıcı olarak kaydedilir)
"""

import logging
from flask import render_template, request, jsonify, session
from . import no_show_bp
from .model_utils import predict_no_show
from ...database import db, Appointment

logger = logging.getLogger(__name__)


@no_show_bp.route("/", methods=["GET"])
def dashboard():
    """No-Show analiz dashboard'u — kayıtlı gerçek tahminlerden en son yapılanları listeler."""
    recent_appointments = (
        Appointment.query.order_by(Appointment.date_created.desc(), Appointment.id.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "no_show.html",
        high_risk_appointments=recent_appointments,
        prediction_result=None,
    )


@no_show_bp.route("/predict", methods=["POST"])
def predict():
    """
    Tekli randevu no-show tahmin API'si.
    Form POST veya JSON POST kabul eder. Sonuç, geçmiş/rapor sayfalarında
    gerçek veri olarak görünmesi için Appointment tablosuna kalıcı olarak yazılır.
    """
    if request.is_json:
        form_data = request.get_json()
    else:
        form_data = request.form.to_dict()

    result = predict_no_show(form_data)
    saved_apt = _save_appointment(form_data, result)

    if request.is_json:
        if saved_apt:
            result["appointment"] = saved_apt.to_dict()
        return jsonify(result)

    recent_appointments = (
        Appointment.query.order_by(Appointment.date_created.desc(), Appointment.id.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "no_show.html",
        high_risk_appointments=recent_appointments,
        prediction_result=result,
        form_data=form_data,
    )


def _save_appointment(form_data: dict, result: dict):
    """Tahmin sonucunu Appointment tablosuna kaydeder ve kaydedilen nesneyi döndürür."""
    if result.get("error"):
        return None
    try:
        appointment = Appointment(
            patient_name=(form_data.get("patient_name") or "İsimsiz Hasta").strip() or "İsimsiz Hasta",
            poliklinik=(form_data.get("poliklinik") or "").strip() or None,
            age=int(float(form_data.get("age", 0) or 0)),
            scholarship=int(form_data.get("scholarship", 0) or 0),
            hipertension=int(form_data.get("hipertension", 0) or 0),
            diabetes=int(form_data.get("diabetes", 0) or 0),
            alcoholism=int(form_data.get("alcoholism", 0) or 0),
            handcap=int(form_data.get("handcap", 0) or 0),
            sms_received=int(form_data.get("sms_received", 0) or 0),
            days_waiting=int(float(form_data.get("days_waiting", 0) or 0)),
            previous_noshow=int(form_data.get("previous_noshow", 0) or 0),
            prediction=result["prediction"],
            probability=result["probability"],
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            risk_color=result["risk_color"],
            created_by=session.get("username", "admin"),
        )
        db.session.add(appointment)
        db.session.commit()
        return appointment
    except Exception as e:
        db.session.rollback()
        logger.error(f"Randevu tahmini kaydedilemedi: {e}")
        return None
