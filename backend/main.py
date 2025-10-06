import os
import json
import httpx # Import the new library
from fastapi import FastAPI, Depends, Query
from sqlalchemy import create_engine, text, Column, Integer, String, MetaData, Table
from geoalchemy2 import Geometry
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import List, Any, Optional
from bs4 import BeautifulSoup

# --- Database Configuration ---
DB_NAME = os.getenv("POSTGRES_DB", "sitrep_db")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = "db"
DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# --- SQLAlchemy Table Definition for 'reports' ---
reports_table = Table(
    'reports', metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('event_type', String),
    Column('event_subtype', String, nullable=True),
    Column('personnel_count', String, nullable=True),
    Column('vehicle_count', String, nullable=True),
    Column('confidence_level', String),
    Column('is_urgent', String),
    Column('granularity', String),
    Column('description', String, nullable=True),
    Column('location', Geometry('POINTZ', srid=4326), nullable=False)
)

# Create the table if it doesn't exist
metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_html_description(html_content: str):
    if not html_content or '<' not in html_content:
        return html_content
    soup = BeautifulSoup(html_content, 'lxml')
    table = soup.find('table')
    if not table:
        body = soup.find('body')
        return body.get_text(separator=' ', strip=True) if body else html_content
    data = {}
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) == 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if key:
                data[key] = value
    return data if data else soup.get_text(separator=' ', strip=True)

# --- Pydantic Models ---
class ReportCreate(BaseModel):
    eventType: str = Field(..., alias='eventType')
    eventSubType: Optional[str] = Field(None, alias='eventSubType')
    personnelCount: Optional[str] = Field(None, alias='personnelCount')
    vehicleCount: Optional[str] = Field(None, alias='vehicleCount')
    confidenceLevel: str = Field(..., alias='confidenceLevel')
    isUrgent: bool = Field(..., alias='isUrgent')
    granularity: str
    description: Optional[str] = None
    location: dict

class KMLFeature(BaseModel):
    id: int
    name: Optional[str] = None
    description: Any
    sourceFile: str
    geometry: Any

# --- API Endpoints ---
@app.get("/api/reports")
def get_reports(db: Session = Depends(get_db)):
    query = text("SELECT id, event_type, ST_AsGeoJSON(location) as location, description FROM reports;")
    result = db.execute(query).fetchall()
    reports_list = []
    for row in result:
        location_geojson = json.loads(row[2])
        reports_list.append({
            "id": row[0],
            "type": row[1],
            "location": [location_geojson['coordinates'][1], location_geojson['coordinates'][0]], # lat, lon
            "description": row[3]
        })
    return reports_list

@app.post("/api/reports")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    point_wkt = f"SRID=4326;POINTZ({report.location['lng']} {report.location['lat']} 0)"
    query = reports_table.insert().values(
        event_type=report.eventType,
        event_subtype=report.eventSubType,
        personnel_count=report.personnelCount,
        vehicle_count=report.vehicleCount,
        confidence_level=report.confidenceLevel,
        is_urgent=str(report.isUrgent),
        granularity=report.granularity,
        description=report.description,
        location=point_wkt
    )
    db.execute(query)
    db.commit()
    return {"status": "success"}

# --- NEW: Reverse Geocode Endpoint ---
@app.get("/api/reverse-geocode")
async def reverse_geocode(lat: float = Query(...), lon: float = Query(...)):
    """
    Acts as a secure proxy to the Nominatim reverse geocoding API.
    """
    nominatim_url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
    headers = {
        'User-Agent': 'SitRepApp/1.0' # Good practice to set a User-Agent
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(nominatim_url, headers=headers, timeout=10.0)
            response.raise_for_status() # Raise an exception for 4xx/5xx errors
            return response.json()
        except httpx.RequestError as exc:
            print(f"An error occurred while requesting {exc.request.url!r}.")
            return {"error": "Failed to connect to geocoding service."}
        except httpx.HTTPStatusError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            return {"error": "Received an error from the geocoding service."}


@app.get("/api/kml-features", response_model=List[KMLFeature])
def get_kml_features(db: Session = Depends(get_db)):
    query = text("SELECT id, name, description, source_file, ST_AsGeoJSON(geom) as geometry FROM kml_features;")
    result = db.execute(query).fetchall()
    features = []
    for row in result:
        geom = json.loads(row[4]) if row[4] else None
        parsed_description = parse_html_description(row[2])
        features.append(
            KMLFeature(
                id=row[0],
                name=row[1],
                description=parsed_description,
                sourceFile=row[3],
                geometry=geom
            )
        )
    return features

