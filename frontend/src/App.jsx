import React, { useState, useEffect, useCallback } from 'react'; // Import useCallback
import axios from 'axios';
import MapView from './MapView';
import SubmissionForm from './SubmissionForm';
import LayerToggle from './LayerToggle';
import './App.css';

function App() {
  const [reports, setReports] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [kmlLayers, setKmlLayers] = useState([]);
  const [kmlVisibility, setKmlVisibility] = useState([]);

  const fetchReports = () => {
    axios.get('/api/reports')
      .then(response => {
        setReports(response.data);
      })
      .catch(error => console.error("Error fetching reports:", error));
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleMapClick = (latlng) => {
    setSelectedLocation(latlng);
  };

  const handleSubmission = (newReportData) => {
    axios.post('/api/reports', newReportData)
      .then(response => {
        setReports(prevReports => [...prevReports, response.data]);
        setSelectedLocation(null); // Hide form after submission
      })
      .catch(error => console.error("Error submitting report:", error));
  };

  // Wrap the function in useCallback to prevent it from being recreated on every render
  const handleKmlLayersLoad = useCallback((loadedLayers) => {
    setKmlLayers(loadedLayers);
    // Initialize all layers to be visible by default
    setKmlVisibility(new Array(loadedLayers.length).fill(true));
  }, []); // The empty dependency array means this function will never change
  
  const handleLayerToggle = (index) => {
    setKmlVisibility(prevVisibility => {
      const newVisibility = [...prevVisibility];
      newVisibility[index] = !newVisibility[index];
      return newVisibility;
    });
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SitRep Map</h1>
        <LayerToggle 
          layers={kmlLayers}
          visibility={kmlVisibility}
          onToggle={handleLayerToggle}
        />
      </header>
      <div className="map-container">
        <MapView 
          reports={reports} 
          onMapClick={handleMapClick} 
          selectedLocation={selectedLocation}
          onKmlLoad={handleKmlLayersLoad}
          kmlVisibility={kmlVisibility}
        />
        {selectedLocation && (
          <SubmissionForm
            location={selectedLocation}
            onSubmit={handleSubmission}
            onCancel={() => setSelectedLocation(null)}
          />
        )}
      </div>
    </div>
  );
}

export default App;

