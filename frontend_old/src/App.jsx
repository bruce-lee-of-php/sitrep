import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import MapView from './MapView';
import SubmissionForm from './SubmissionForm';
import LayerToggle from './LayerToggle'; // Import the new component
import './App.css';

function App() {
  const [reports, setReports] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [kmlLayers, setKmlLayers] = useState([]); // State to hold KML layer data

  // Fetch initial SitRep data
  useEffect(() => {
    axios.get('/api/reports')
      .then(response => setReports(response.data))
      .catch(error => console.error("Error fetching reports:", error));
  }, []);

  // --- NEW: Fetch KML Features from the API ---
  useEffect(() => {
    axios.get('/api/kml-features')
      .then(response => {
        // Augment the data with a 'visible' property for the toggle
        const layersWithVisibility = response.data.map(layer => ({
          ...layer,
          visible: true // Initially, all layers are visible
        }));
        setKmlLayers(layersWithVisibility);
      })
      .catch(error => console.error("Error fetching KML features:", error));
  }, []); // Empty dependency array means this runs once on mount

  const handleMapClick = useCallback((latlng) => {
    console.log("[App.jsx] handleMapClick called with:", latlng);
    setSelectedLocation(latlng);
  }, []);

  const handleCancel = () => {
    setSelectedLocation(null);
  };

  const handleSubmit = (newReport) => {
    setReports(prevReports => [...prevReports, newReport]);
    setSelectedLocation(null);
  };

  // --- NEW: Function to handle layer visibility toggle ---
  const handleLayerToggle = (layerId) => {
    setKmlLayers(prevLayers =>
      prevLayers.map(layer =>
        layer.id === layerId ? { ...layer, visible: !layer.visible } : layer
      )
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SitRep Map</h1>
        {/* Pass layer data and the toggle handler to the component */}
        <LayerToggle layers={kmlLayers} onToggle={handleLayerToggle} />
      </header>
      <div className="map-container">
        <MapView
          reports={reports}
          onMapClick={handleMapClick}
          selectedLocation={selectedLocation}
          kmlLayers={kmlLayers} // Pass the KML layer data down to the map
        />
        {selectedLocation && (
          <SubmissionForm
            location={selectedLocation}
            onCancel={handleCancel}
            onSubmit={handleSubmit}
          />
        )}
      </div>
    </div>
  );
}

export default App;

