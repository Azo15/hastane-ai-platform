"""
run.py — Hastane AI Platformu Ana Giriş Noktası
Uygulamayı başlatmak için: python run.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
