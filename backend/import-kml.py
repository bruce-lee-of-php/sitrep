import os
import psycopg2
from fastkml import kml
from shapely.geometry import shape
from shapely.wkt import dumps
from shapely.ops import transform
from fastkml.utils import find, find_all
from fastkml import Placemark, Point, StyleUrl, Style


# --- Database Configuration ---
DB_NAME = os.getenv("POSTGRES_DB", "sitrep_db")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = "db"
DB_PORT = "5432"

# --- Script Configuration ---
KML_DIRECTORY = "/app/kml_files"
TABLE_NAME = "kml_features"

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error: Could not connect to the database. {e}")
        return None

def create_kml_table(conn):
    """Creates the table to store KML features if it doesn't already exist."""
    with conn.cursor() as cur:
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            description TEXT,
            source_file VARCHAR(255),
            geom GEOMETRY(GEOMETRYZ, 4326)
        );
        """)
    print(f"DEBUG: Table '{TABLE_NAME}' is ready.")

def clear_existing_data(cur, source_file):
    """Deletes old data for a specific KML file. Uses the provided cursor."""
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE source_file = %s;", (source_file,))
    print(f"DEBUG: Cleared existing data for '{source_file}'.")

def force_3d(geom):
    """Forces a shapely geometry to be 3D by adding a Z coordinate of 0 if it's 2D."""
    if geom.has_z:
        return geom
    else:
        def to_3d(x, y):
            return (x, y, 0)
        return transform(to_3d, geom)

def parse_and_insert(cur, kml_filepath):
    """
    Parses a KML file and inserts its placemarks using the provided cursor.
    The calling function is responsible for transaction management (commit/rollback).
    """
    source_filename = os.path.basename(kml_filepath)
    clear_existing_data(cur, source_filename)

    k = kml.KML.parse(kml_filepath)
    all_placemarks = list(find_all(k, of_type=kml.Placemark))
    total_placemarks = len(all_placemarks)
    
    print(f"DEBUG: Found {total_placemarks} placemarks. Staging for insert...")
    
    insert_count = 0
    for i, place in enumerate(all_placemarks):
        try:
            if not hasattr(place, 'geometry') or place.geometry is None:
                continue
            
            geom_2d = shape(place.geometry)
            geom_3d = force_3d(geom_2d)
            wkt_geom = f"SRID=4326;{dumps(geom_3d)}"

            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (name, description, source_file, geom)
                VALUES (%s, %s, %s, ST_GeomFromEWKT(%s));
                """,
                (place.name, place.description, source_filename, wkt_geom)
            )
            insert_count += 1
        except Exception as feature_error:
            print(f"  - SKIPPING feature #{i+1} ('{place.name}') due to error: {feature_error}")
            continue
    
    print(f"DEBUG: Successfully staged {insert_count} features.")

def external_verification(source_file):
    """
    Opens a brand new connection to act like an external user (e.g., psql)
    and checks if the data is visible, printing the contents.
    """
    print("\n--- STARTING EXTERNAL VERIFICATION ---")
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                # Select key fields to display, converting geom to text for readability
                cur.execute(f"SELECT id, name, description, ST_AsText(geom) FROM {TABLE_NAME} WHERE source_file = %s;", (source_file,))
                results = cur.fetchall()
                count = len(results)
                print(f"EXTERNAL VERIFICATION RESULT: Found {count} features for '{source_file}'.")
                
                # Print the details of each found record
                if count > 0:
                    print("--- VERIFIED RECORDS ---")
                    for row in results:
                        # Truncate long fields for cleaner logging
                        desc = (row[2][:70] + '...') if row[2] and len(row[2]) > 70 else row[2]
                        geom_text = (row[3][:70] + '...') if row[3] and len(row[3]) > 70 else row[3]
                        print(f"  ID: {row[0]}, Name: {row[1]}, Desc: {desc}, Geom: {geom_text}")
                    print("------------------------")
        else:
            print("EXTERNAL VERIFICATION FAILED: Could not get a new DB connection.")
    except Exception as e:
        print(f"EXTERNAL VERIFICATION ERROR: {e}")
    finally:
        if conn:
            conn.close()
        print("--- EXTERNAL VERIFICATION FINISHED ---\n")


def main():
    """Main function to run the import process."""
    print("DEBUG: Script started.")
    try:
        with get_db_connection() as conn:
            print(f"DEBUG: Initial connection object: {conn}")
            with conn.cursor() as cur:
                create_kml_table(conn)
        print("DEBUG: Initial setup check complete. Connection closed.")
    except Exception as e:
        print(f"Could not perform initial setup. Aborting. Error: {e}")
        return

    if not os.path.isdir(KML_DIRECTORY):
        print(f"Error: KML directory not found at '{KML_DIRECTORY}'")
        return

    for filename in os.listdir(KML_DIRECTORY):
        if filename.lower().endswith(".kml"):
            print(f"\n--- Processing {filename} ---")
            
            try:
                print(f"DEBUG: Opening transaction block for {filename}...")
                with get_db_connection() as conn:
                    print(f"DEBUG: Connection object for {filename}: {conn}")
                    print(f"DEBUG: Transaction status: {conn.status}, Autocommit: {conn.autocommit}")
                    with conn.cursor() as cur:
                        parse_and_insert(cur, os.path.join(KML_DIRECTORY, filename))
                    print(f"DEBUG: Cursor block finished. About to commit transaction for {filename}.")
                
                print(f"DEBUG: Transaction for {filename} committed and connection closed.")
            except Exception as e:
                print(f"Transaction for {filename} FAILED and was rolled back. Error: {e}")
            
            # This mimics your psql check immediately after the transaction.
            external_verification(filename)

    print("\nImport process finished.")

if __name__ == "__main__":
    main()

