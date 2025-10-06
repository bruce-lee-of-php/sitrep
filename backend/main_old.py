import os
import json
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Any
from bs4 import BeautifulSoup # Import BeautifulSoup

# --- Database Configuration ---
DB_NAME = os.getenv("POSTGRES_DB", "sitrep_db")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = "db"
DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- NEW: HTML Description Parser ---
def parse_html_description(html_content: str):
    """
    Parses HTML content from a KML description field. If it finds a table,
    it extracts the key-value pairs into a dictionary. Otherwise, it returns
    the original text content.
    """
    if not html_content or '<' not in html_content:
        return html_content # Not HTML, return as is

    soup = BeautifulSoup(html_content, 'lxml')
    
    # Try to find a table with key-value pairs
    table = soup.find('table')
    if not table:
        # If no table, return the stripped text content of the body
        body = soup.find('body')
        return body.get_text(separator=' ', strip=True) if body else html_content

    data = {}
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) == 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if key: # Ensure the key is not empty
                data[key] = value
    
    # If we successfully extracted data, return the dictionary
    return data if data else soup.get_text(separator=' ', strip=True)


# --- Pydantic Models ---
class KMLFeature(BaseModel):
    id: int
    name: str | None
    # Description can now be a string OR a dictionary (Any)
    description: Any | None
    sourceFile: str
    geometry: Any

# --- API Endpoints ---
@app.get("/api/reports")
def get_reports(db: Session = Depends(get_db)):
    # This endpoint remains unchanged for now
    return []

@app.post("/api/reports")
def create_report(db: Session = Depends(get_db)):
    # This endpoint remains unchanged for now
    return {}

@app.get("/api/kml-files", response_model=List[str])
def get_kml_files():
    kml_dir = "/app/kml_files"
    try:
        files = [f for f in os.listdir(kml_dir) if f.lower().endswith(".kml")]
        return files
    except FileNotFoundError:
        return []

@app.get("/api/kml-features", response_model=List[KMLFeature])
def get_kml_features(db: Session = Depends(get_db)):
    query = text("""
        SELECT id, name, description, source_file, ST_AsGeoJSON(geom) as geometry
        FROM kml_features;
    """)
    result = db.execute(query).fetchall()
    
    features = []
    for row in result:
        geom = json.loads(row[4]) if row[4] else None
        
        # --- MODIFIED: Process the description before sending ---
        parsed_description = parse_html_description(row[2])

        features.append(
            KMLFeature(
                id=row[0],
                name=row[1],
                description=parsed_description, # Use the parsed description
                sourceFile=row[3],
                geometry=geom
            )
        )
    return features

