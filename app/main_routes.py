"""
app/main_routes.py — Ana Sayfa (index) Blueprint
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Karşılama ekranı — Hastane AI Platformu genel özet paneli."""
    stats = {
        "total_appointments": 1284,
        "high_risk_count": 87,
        "open_tickets": 14,
        "resolved_tickets": 203,
        "no_show_rate": 22.4,
        "ai_accuracy": 91.7,
    }
    return render_template("index.html", stats=stats)
