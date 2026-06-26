# visitor-gate-pass-system
Full-stack Visitor Gate Pass System | FastAPI + SQLite backend, Vanilla JS frontend | Role-based login for Employee, Admin &amp; Security Guard
# 🔐 Visitor Gate Pass System

A full-stack web application to manage visitor entry and exit in an organization. Built with **FastAPI** (Python) and **Vanilla JavaScript**.

---

## 📋 Features

- **Employee** — Request visitor pass with ID proof and visit details
- **Admin** — Approve / Reject pending pass requests, view visitor log
- **Security Guard** — Scan QR token at gate for entry/exit recording
- JWT-based authentication with role-based access control
- Auto-generated QR tokens for approved passes
- Real-time entry/exit log with search and date filters

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, Vanilla JavaScript |
| Backend | Python, FastAPI |
| Database | SQLite (via SQLAlchemy) |
| Auth | JWT (python-jose) + bcrypt |

---

## 👤 Default Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@gatepass.com | admin123 |
| Employee | krish@gatepass.com | emp123 |
| Guard | guard@gatepass.com | guard123 |

---

## 🚀 How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/visitor-gate-pass-system.git
cd visitor-gate-pass-system
```

### 2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy python-jose[cryptography] bcrypt python-multipart
```

### 4. Start the backend
```bash
uvicorn main:app --reload
```

### 5. Open in browser
```
http://localhost:8000
```

---

## 📁 Project Structure

```
visitor-gate-pass-system/
│
├── main.py          # FastAPI backend (all routes + database)
├── index.html       # Frontend (all 5 screens in one file)
├── gatepass.db      # SQLite database (auto-created on first run)
└── README.md
```

---

## 🖥️ Screens

| Screen | Role | Description |
|--------|------|-------------|
| Login | All | Email + password + role-based redirect |
| Request Pass | Employee | Submit new visitor pass request |
| Pending Queue | Admin | Approve or reject pass requests |
| Gate Scan | Guard / Admin | Scan QR token for entry/exit |
| Visitor Log | Admin | Search and filter entry/exit records |

---

## 📌 Project Info

- **Project:** #33 — Visitor Gate Pass System
- **Developer:** Krish Kumar Rathi
