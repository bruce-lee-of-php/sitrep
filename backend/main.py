from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import asynccontextmanager
import time
from pathlib import Path
import json


# --- Database Configuration ---
DATABASE_URL = "postgresql://user:password@db/sitrep_db"

Base = declarative_base()

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    lat = Column(Float)
    lng = Column(Float)

# --- Pydantic Models for API validation ---
class ReportCreate(BaseModel):
    title: str
    description: str
    lat: float
    lng: float

class ReportResponse(ReportCreate):
    id: int
    class Config:
        from_attributes = True

# --- Database Connection Management ---
engine = None
SessionLocal = None

def connect_to_db():
    global engine, SessionLocal
    max_retries = 10
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as connection:
                print("Database connection successful!")
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine)
            return
        except Exception as e:
            print(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_db()
    yield

app = FastAPI(lifespan=lifespan)

# --- Dependency for Database Session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "SitRep API is running"}

@app.post("/api/reports", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    db_report = Report(**report.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@app.get("/api/reports", response_model=list[ReportResponse])
def get_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).all()
    return reports

@app.get("/api/kml-files")
def list_kml_files():
    kml_dir = Path("/app/kml_files")
    files = [f.name for f in kml_dir.iterdir() if f.suffix == ".kml"]
    print(files)
    print(type(files))
    print()
    # Explicitly return a JSONResponse to ensure the correct Content-Type header
    return json.dumps(files)

