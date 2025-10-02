# SitRep Map

SitRep Map is a self-hosted, Docker-based system for submitting and visualizing geospatial situation reports (sitreps). It provides a clean, map-based interface for securely logging location-based data and viewing it in real-time. This project is perfect for community organizing, emergency response coordination, citizen journalism, or environmental monitoring.

## Features

* **Interactive Map Interface:** Uses Leaflet to provide a smooth, responsive map for both submitting and viewing data.

* **Point-and-Click Reporting:** Simply click anywhere on the map to drop a pin and bring up the submission form.

* **Secure Geospatial Database:** All reports are stored securely in a PostgreSQL database with the PostGIS extension for powerful location-based queries.

* **KML Overlay Support:** Add any `.kml` file to the `kml_files` directory, and it will be automatically loaded as a toggleable overlay on the map.

* **Live Layer Toggling:** A simple UI in the header allows users to turn KML layers on and off without reloading the page.

* **Fully Containerized:** The entire application stack (frontend, backend, database, proxy) is managed by Docker Compose for easy setup and portability.

## Tech Stack

The project is built with a modern, reliable, and scalable technology stack.

* **Frontend:** [React](https://reactjs.org/) with [Vite](https://vitejs.dev/) and [Leaflet](https://leafletjs.com/) for the interactive map.

* **Backend:** A robust API built with [Python](https://www.python.org/) and [FastAPI](https://fastapi.tiangolo.com/).

* **Database:** [PostgreSQL](https://www.postgresql.org/) + [PostGIS](https://postgis.net/) for powerful and secure geospatial data storage.

* **Web Server / Proxy:** [Nginx](https://www.nginx.com/) to handle web traffic and route requests.

* **Containerization:** [Docker Compose](https://docs.docker.com/compose/) for orchestrating the multi-container setup.

## Installation and Running

Getting the application running is straightforward, provided you have Docker and Docker Compose installed.

**1. Clone the Repository**
```bash
git clone https://github.com/bruce-lee-of-php/sitrep.git

cd sitrep-mvp
```
**2. Add KML Files (Optional)**

Now copy your `.kml` files into this the `kml_files` directory
**3. Build and Run with Docker Compose**

From the root directory of the project (`sitrep-mvp/`), run the following command:
```bash
docker-compose up --build
```
This command will build the images for each service, create the containers, and start the application.

**4. Access the Application**

Once all the containers are running, open your web browser and navigate to:

**`http://localhost:8085`**

## How to Use

* **View Reports:** Existing situation reports will appear as markers on the map.

* **Submit a New Report:** Click anywhere on the map to select a location. A marker will appear, and a submission form will open in the top-right corner. Fill it out and click "Submit".

* **Toggle KML Layers:** Click the "Overlays" button in the header to open a menu. You can check or uncheck the boxes to show or hide the KML layers you've added.

## Project Structure

sitrep-mvp/
├── backend/              # FastAPI backend API
├── frontend/             # React frontend application
├── kml_files/            # Directory for your KML overlays
├── nginx/                # Nginx configuration and Dockerfile
└── docker-compose.yml    # Main Docker