import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMapEvents } from "react-leaflet";
import axios from 'axios';
import { kml } from "@tmcw/togeojson";
import "leaflet/dist/leaflet.css";
import "./MapView.css";

// Helper component to capture map clicks
function LocationClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng);
    },
  });
  return null; // This component doesn't render anything
}

const MapView = ({ reports, onMapClick, selectedLocation, onKmlLoad, kmlVisibility }) => {
  const [kmlGeoJsons, setKmlGeoJsons] = useState([]);
  const position = [42.4735, -83.1449]; // Ferndale, MI coordinates

  useEffect(() => {
    const fetchKmlData = async () => {
      try {
        const response = await axios.get('/api/kml-files');
        const kmlFiles = JSON.parse(response.data);
        
        if (!Array.isArray(kmlFiles)) {
          console.error("KML file list is not in the expected format:", kmlFiles);
          return;
        }

        const geoJsonPromises = kmlFiles.map(async (fileName) => {
          const kmlResponse = await axios.get(`/kml/${fileName}`);
          const dom = new DOMParser().parseFromString(kmlResponse.data, 'text/xml');
          return kml(dom);
        });
        
        const resolvedGeoJsons = await Promise.all(geoJsonPromises);
        setKmlGeoJsons(resolvedGeoJsons);
        onKmlLoad(resolvedGeoJsons); // Pass loaded layers up to App component

      } catch (error) {
        console.error("Error fetching or parsing KML data:", error);
      }
    };

    fetchKmlData();
  }, [onKmlLoad]);

  return (
    <MapContainer center={position} zoom={13} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      
      {/* Existing SitRep Markers */}
      {reports.map(report => (
        <Marker key={report.id} position={[report.lat, report.lng]}>
          <Popup>
            <strong>{report.title}</strong><br />
            {report.description}
          </Popup>
        </Marker>
      ))}

      {/* Render KML data as GeoJSON layers, respecting the visibility state */}
      {kmlGeoJsons.map((geoJson, index) => (
        kmlVisibility[index] && <GeoJSON key={index} data={geoJson} />
      ))}

      {/* Marker for the new, selected location */}
      {selectedLocation && <Marker position={selectedLocation}></Marker>}

      {/* Component that listens for clicks */}
      <LocationClickHandler onMapClick={onMapClick} />

    </MapContainer>
  );
};

export default MapView;

