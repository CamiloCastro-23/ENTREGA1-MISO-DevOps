import os
import newrelic.agent

newrelic_config = os.getenv('NEW_RELIC_CONFIG_FILE', './newrelic.ini')
newrelic.agent.initialize(newrelic_config)

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, Text
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

import os
import socket #pragma: no cover


DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Db_miso-psswdDevops12")
DB_HOST = os.getenv("DB_HOST", "database-1.cj5g868olfdm.us-east-1.rds.amazonaws.com")
# DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

IS_TEST_MODE = os.getenv("TEST_MODE", False)

if IS_TEST_MODE: #pragma: no cover
    DATABASE_URL = "sqlite:///:memory:" #pragma: no cover
else: #pragma: no cover
    DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" #pragma: no cover


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = sqlalchemy.orm.declarative_base()


class BlacklistEntry(Base):
    __tablename__ = "blacklist"

    email = Column(String, primary_key=True, index=True)
    app_uuid = Column(String, nullable=False)
    blocked_reason = Column(Text, nullable=True)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


app = FastAPI()


API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

DEPLOYMENT_MODE = "FIRST_DEPLOYMENT_NEW_RELIC"

security = HTTPBearer()

def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.scheme != "Bearer" or credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


class BlacklistCreateRequest(BaseModel):
    email: EmailStr
    app_uuid: UUID
    blocked_reason: Optional[constr(max_length=255)] = None # type: ignore

class BlacklistCreateResponse(BaseModel):
    message: str

class BlacklistCheckResponse(BaseModel):
    is_blacklisted: bool
    blocked_reason: Optional[str] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "OK - Pipeline de CI/CD con FastAPI"}

@app.get("/deploy")
def ping():
    hostname = socket.gethostname()
    return {"hostname": hostname, "deployment_mode": DEPLOYMENT_MODE}

@app.post("/reset")
def reset_database(token: str = Depends(get_token)):
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"message": "Base de datos reseteada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al resetear la base de datos: {e}")

@app.get("/blacklists/{email}", response_model=BlacklistCheckResponse)
def check_blacklist(
    email: str,
    token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    entry = db.query(BlacklistEntry).filter(BlacklistEntry.email == email).first()
    if entry:
        return {"is_blacklisted": True, "blocked_reason": entry.blocked_reason}
    else:
        return {"is_blacklisted": False, "blocked_reason": None}

@app.post("/blacklists", response_model=BlacklistCreateResponse)
def add_to_blacklist(
    request_data: BlacklistCreateRequest,
    request: Request,
    token: str = Depends(get_token),
    db: Session = Depends(get_db)
):
    existing_entry = db.query(BlacklistEntry).filter(BlacklistEntry.email == request_data.email).first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="El email ya está en la lista negra")

    blacklist_entry = BlacklistEntry(
        email=request_data.email,
        app_uuid=str(request_data.app_uuid),
        blocked_reason=request_data.blocked_reason,
        ip_address=request.client.host,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(blacklist_entry)
    db.commit()
    return {"message": "Email agregado a la lista negra exitosamente"}

