# Contributing Guidelines / Katkı Sağlama Kılavuzu

Thank you for considering contributing to Hastane AI Platform! We welcome contributions to improve our hospital operation & AI automation suite.

---

## 🚀 How to Contribute / Nasıl Katkı Sağlayabilirsiniz?

### 1. Fork and Clone / Projeyi Çatallama ve Klonlama
1. Fork the repository to your own GitHub account.
2. Clone your forked repository:
   git clone https://github.com/YOUR_USERNAME/hastane-ai-platform.git
   cd hastane-ai-platform

### 2. Branching Standard / Dal Oluşturma Standardı
Create a descriptive branch for your changes:
   git checkout -b feature/amazing-feature
   # or for bug fixes / model updates:
   # git checkout -b fix/issue-description

### 3. Local Environment Setup / Yerel Kurulum
Set up a Python virtual environment and install dependencies:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Make sure to set ANTHROPIC_API_KEY and Flask configs in .env

### 4. Running Tests & Code Quality / Testler
Before submitting changes, make sure all pytest cases and CSRF/security checks pass:
   pytest

### 5. Commit Messages / Commit Mesajı Formatı
Please follow standard conventional commit rules:
- feat: New feature, model, or chatbot tool integration
- fix: Bug fix or session/database handling fixes
- docs: Documentation updates
- refactor: Code structuring, blueprint improvements, or test fixture cleanups

### 6. Push & Open Pull Request / PR Açma
1. Push your branch to GitHub:
   git push origin feature/amazing-feature
2. Open a Pull Request against the master branch.
3. Describe clearly what changes you made (e.g., LightGBM hyperparameter changes, Claude prompt updates, Flask blueprint fixes).

---

## 🛠️ Tech Stack & Architecture Rules
- Flask (Application Factory Pattern with Blueprints)
- LightGBM (No-Show Appointment Prediction Engine)
- Anthropic Claude API (IT Support Chatbot & Automation)
- CSRF Protection enabled for all AJAX endpoints.

---

Thank you for helping build a smarter healthcare management ecosystem! 🏥🤖
