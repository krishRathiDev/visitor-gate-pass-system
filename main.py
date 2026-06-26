from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timedelta
from jose import JWTError, jwt
import bcrypt
import uuid

# ─── CONFIG ───
SECRET_KEY = "gatepass-secret-key-2026"
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

# ─── DATABASE ───
SQLALCHEMY_DATABASE_URL = "sqlite:///./gatepass.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ─── MODELS ───
class UserDB(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    role     = Column(String)

class PassDB(Base):
    __tablename__ = "passes"
    id              = Column(Integer, primary_key=True, index=True)
    visitor_name    = Column(String)
    contact_number  = Column(String)
    visitor_email   = Column(String, nullable=True)
    id_proof_type   = Column(String)
    id_proof_number = Column(String)
    visit_date      = Column(String)
    purpose         = Column(Text)
    status          = Column(String, default="pending")
    qr_token        = Column(String, nullable=True)
    host_id         = Column(Integer)
    host_name       = Column(String)
    created_at      = Column(DateTime, default=datetime.utcnow)

class VisitorLogDB(Base):
    __tablename__ = "visitor_log"
    id         = Column(Integer, primary_key=True, index=True)
    pass_id    = Column(Integer)
    entry_time = Column(DateTime, nullable=True)
    exit_time  = Column(DateTime, nullable=True)
    guard_name = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# ─── AUTH HELPERS ───
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email   = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ─── SEED DEFAULT USERS ───
def seed_users(db: Session):
    if db.query(UserDB).count() == 0:
        users = [
            UserDB(name="Ramesh Admin", email="admin@gatepass.com",  password=hash_password("admin123"), role="admin"),
            UserDB(name="Krish",        email="krish@gatepass.com",  password=hash_password("emp123"),   role="employee"),
            UserDB(name="Anjali S.",    email="anjali@gatepass.com", password=hash_password("emp123"),   role="employee"),
            UserDB(name="Ramesh K.",    email="guard@gatepass.com",  password=hash_password("guard123"), role="guard"),
        ]
        db.add_all(users)
        db.commit()

# ─── APP ───
app = FastAPI(title="Visitor Gate Pass System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    db = SessionLocal()
    seed_users(db)
    db.close()

# ─── PYDANTIC SCHEMAS ───
class PassCreate(BaseModel):
    visitor_name:    str
    contact_number:  str
    visitor_email:   Optional[str] = None
    id_proof_type:   str
    id_proof_number: str
    visit_date:      str
    purpose:         str

class ScanRequest(BaseModel):
    qr_token: str

# ══════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "Gate Pass Backend is running ✅"}

# ─── AUTH ───
@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email, "role": user.role, "name": user.name})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "name": user.name}

# ─── PASSES ───
@app.post("/passes")
def create_pass(body: PassCreate, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["employee", "admin"]:
        raise HTTPException(status_code=403, detail="Only employees can request passes")
    new_pass = PassDB(
        visitor_name    = body.visitor_name,
        contact_number  = body.contact_number,
        visitor_email   = body.visitor_email,
        id_proof_type   = body.id_proof_type,
        id_proof_number = body.id_proof_number,
        visit_date      = body.visit_date,
        purpose         = body.purpose,
        host_id         = current_user.id,
        host_name       = current_user.name,
        status          = "pending",
    )
    db.add(new_pass)
    db.commit()
    db.refresh(new_pass)
    return {"pass_id": new_pass.id, "message": "Pass request submitted"}

@app.get("/passes/my")
def my_passes(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    passes = db.query(PassDB).filter(PassDB.host_id == current_user.id).order_by(PassDB.created_at.desc()).all()
    return [
        {
            "id":         p.id,
            "visitor":    p.visitor_name,
            "contact":    p.contact_number,
            "visit_date": p.visit_date,
            "purpose":    p.purpose,
            "status":     p.status,
            "qr_token":   p.qr_token,
        }
        for p in passes
    ]

@app.get("/passes/pending")
def pending_passes(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    passes = db.query(PassDB).filter(PassDB.status == "pending").order_by(PassDB.created_at.desc()).all()
    return [
        {
            "id":         p.id,
            "visitor":    p.visitor_name,
            "contact":    p.contact_number,
            "host":       p.host_name,
            "visit_date": p.visit_date,
            "purpose":    p.purpose,
            "status":     p.status,
        }
        for p in passes
    ]

@app.patch("/passes/{pass_id}/approve")
def approve_pass(pass_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    p = db.query(PassDB).filter(PassDB.id == pass_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pass not found")
    p.status   = "approved"
    p.qr_token = str(uuid.uuid4())
    db.commit()
    log = VisitorLogDB(pass_id=p.id)
    db.add(log)
    db.commit()
    return {"message": "Pass approved", "qr_token": p.qr_token}

@app.patch("/passes/{pass_id}/reject")
def reject_pass(pass_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    p = db.query(PassDB).filter(PassDB.id == pass_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pass not found")
    p.status = "rejected"
    db.commit()
    return {"message": "Pass rejected"}

# ─── GATE SCAN ───
@app.post("/gate/scan")
def gate_scan(body: ScanRequest, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(PassDB).filter(PassDB.qr_token == body.qr_token).first()
    if not p:
        return {"result": "INVALID", "message": "Token not found / not approved"}
    if p.status != "approved":
        return {"result": "NOT_APPROVED", "message": "This pass has not been approved yet"}

    today = date.today().isoformat()
    if p.visit_date < today:
        return {"result": "EXPIRED",       "message": f"Pass was valid for {p.visit_date} only", "visitor": p.visitor_name}
    if p.visit_date > today:
        return {"result": "NOT_YET_VALID", "message": f"Pass is valid on {p.visit_date} only",   "visitor": p.visitor_name}

    log = db.query(VisitorLogDB).filter(VisitorLogDB.pass_id == p.id).first()
    if not log:
        log = VisitorLogDB(pass_id=p.id)
        db.add(log)
        db.commit()
        db.refresh(log)

    if log.entry_time is None:
        log.entry_time = datetime.utcnow()
        log.guard_name = current_user.name
        db.commit()
        return {"result": "ENTRY_RECORDED", "message": "Visitor may proceed inside",
                "visitor": p.visitor_name, "host": p.host_name, "purpose": p.purpose,
                "entry_time": log.entry_time.isoformat()}
    elif log.exit_time is None:
        log.exit_time  = datetime.utcnow()
        log.guard_name = current_user.name
        db.commit()
        return {"result": "EXIT_RECORDED", "message": "Visitor has exited premises",
                "visitor": p.visitor_name,
                "entry_time": log.entry_time.isoformat(), "exit_time": log.exit_time.isoformat()}
    else:
        return {"result": "ALREADY_USED", "message": "Pass already fully used", "visitor": p.visitor_name}

# ─── VISITOR LOG ───
@app.get("/visitors/log")
def visitor_log(
    date_filter:  Optional[str] = None,
    visitor_name: Optional[str] = None,
    host_name:    Optional[str] = None,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    query = db.query(PassDB, VisitorLogDB).join(VisitorLogDB, PassDB.id == VisitorLogDB.pass_id, isouter=True)
    if date_filter:  query = query.filter(PassDB.visit_date == date_filter)
    if visitor_name: query = query.filter(PassDB.visitor_name.ilike(f"%{visitor_name}%"))
    if host_name:    query = query.filter(PassDB.host_name.ilike(f"%{host_name}%"))
    results = query.order_by(PassDB.created_at.desc()).all()
    return [
        {
            "visitor":    p.visitor_name,
            "contact":    p.contact_number,
            "host":       p.host_name,
            "visit_date": p.visit_date,
            "entry_time": l.entry_time.isoformat() if l and l.entry_time else None,
            "exit_time":  l.exit_time.isoformat()  if l and l.exit_time  else None,
            "guard":      l.guard_name if l else "—",
        }
        for p, l in results
    ]
