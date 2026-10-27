# PortfolioAI — AI-Powered Portfolio Generator

> An advanced, production-oriented AI Portfolio Generator built as a CSE College Capstone project. Automatically transforms resumes, GitHub repositories, and skill profiles into industry-grade, customizable portfolio websites.

---

## 🌟 Project Overview

**PortfolioAI** is designed to solve the challenge faced by students and job seekers who lack the technical design experience, time, or copywriting confidence needed to build competitive portfolio websites.

### Key Capabilities:
- **AI Resume PDF Parsing:** Extract structured education, experience, projects, and skills using `pypdf` and Google Gemini AI.
- **Generative AI Content Polish:** Craft recruiter-tailored headlines, career biographies, and STAR-format project summaries without hallucinations.
- **Target Job Skill Gap Analyzer:** Objective skills matching against pasted job descriptions with personalized learning recommendations.
- **Dynamic Theme Engine:** Switch seamlessly between Modern Tech, Clean Minimalist, and Creative Studio themes with live real-time preview.
- **GitHub Integration:** 1-click import of public repositories, languages, and star counts.
- **Export & Publishing:** Vanity URLs (`/p/username`), ReportLab PDF summaries, and dynamic scannable QR codes.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.13, Flask 3.1 | Application factory, REST routing, Blueprints |
| **Database & ORM**| SQLite (Dev) / PostgreSQL (Prod), Flask-SQLAlchemy 3.1 | Relational database schema and migrations |
| **Authentication** | Flask-Login, Werkzeug Password Hashing | Secure user authentication and session management |
| **Generative AI** | Google GenAI SDK (`google-genai`), Gemini 2.5 Flash | Structured resume extraction, bio generation, skills analysis |
| **Resume Parser** | `pypdf` | Secure PDF text stream extraction |
| **PDF & QR Export**| `ReportLab`, `qrcode[pil]` | ATS-formatted 1-page PDF resumes and dynamic QR codes |
| **Frontend UI/UX** | HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons | Responsive dark navy SaaS design with glassmorphism |
| **Security** | Flask-WTF (CSRF), Flask-Limiter (Rate limiting) | Defense-in-depth protection and payload limits |

---

## 📁 Project Directory Structure

```text
c:\portfolio\
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration (git ignored)
├── .gitignore                # Git exclusions (.venv, *.db, uploads/, exports/)
├── config.py                 # Application configuration classes (Dev, Test, Prod)
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration and pythonpath setup
├── run.py                    # Entrypoint to run the development server
├── README.md                 # Project documentation and guide
├── app/
│   ├── __init__.py           # Application factory (create_app), error handlers
│   ├── extensions.py         # SQLAlchemy, Migrate, LoginManager, CSRF, Limiter
│   ├── main/                 # Core landing page blueprint
│   │   ├── __init__.py
│   │   └── routes.py         # Landing page (/) and health check (/health)
│   ├── auth/                 # Authentication blueprint (Login/Register)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── dashboard/            # User workspace blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css     # Futuristic SaaS design system & glassmorphism
│   │   └── js/
│   │       └── main.js       # Dynamic navbar, interactive theme switcher
│   └── templates/
│       ├── base.html         # Base template with responsive navbar & footer
│       ├── index.html        # Modern interactive SaaS landing page
│       ├── login.html        # Sign-in form
│       ├── register.html     # Registration form
│       ├── dashboard.html    # User dashboard workspace shell
│       └── errors/
│           ├── 404.html      # Not found error
│           ├── 413.html      # File size too large
│           ├── 429.html      # Rate limit exceeded
│           └── 500.html      # Internal server error
└── tests/
    └── test_phase1.py        # Automated test suite for Phase 1 verification
```

---

## 🚀 Quickstart & Local Setup Guide

### 1. Prerequisites
- **Python 3.10+** (Python 3.13 tested and confirmed)
- **Git**
- Google Gemini API key (Free tier available at [Google AI Studio](https://aistudio.google.com/app/apikey))

### 2. Environment Setup
In PowerShell or your terminal:
```powershell
# Clone or navigate to the project directory
cd c:\portfolio

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# Upgrade pip and install all required dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Ensure your `.env` contains:
```env
FLASK_ENV=development
FLASK_APP=run.py
SECRET_KEY=dev-portfolio-ai-secret-key-college-project-2026-secure
DATABASE_URL=sqlite:///portfolio.db
GEMINI_API_KEY=your_gemini_api_key_here
MAX_CONTENT_LENGTH_MB=10
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg
```

### 4. Run the Automated Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
All Phase 1 tests will run and pass:
- `test_landing_page`: Verifies 200 OK and brand rendering
- `test_health_check`: Verifies `/health` JSON monitor
- `test_404_error_page`: Verifies custom error handling
- `test_auth_routes_accessible`: Verifies auth views

### 5. Launch the Application
```powershell
.\.venv\Scripts\python.exe run.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 🎯 Phase 1 Status
- [x] Python 3.13 Virtual environment configured
- [x] Stable package dependencies installed
- [x] Flask Application Factory (`create_app`) with Blueprints
- [x] Centralized extensions initialization (`extensions.py`)
- [x] Config hierarchy (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`)
- [x] High-converting modern SaaS landing page with dark navy & violet glassmorphic design
- [x] Interactive theme switcher preview mockup in Hero section
- [x] Responsive layout across desktop, tablet, and mobile
- [x] Global error handling (404, 413, 429, 500)
- [x] Automated unit test suite configured and passing (100% pass rate)
