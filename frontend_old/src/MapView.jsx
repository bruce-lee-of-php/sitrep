import React from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./MapView.css";
import booleanPointInPolygon from "@turf/boolean-point-in-polygon";
import pointToLineDistance from "@turf/point-to-line-distance";
import distance from "@turf/distance";
import { point, lineString, polygon } from "@turf/helpers";

// Helper component to render descriptions in popups
const DescriptionPopup = ({ content }) => {
  if (typeof content !== 'object' || content === null) {
    return <div>{content}</div>;
  }
  return (
    <div className="description-table">
      {Object.entries(content).map(([key, value]) => (
        <div key={key} className="description-row">
          <strong>{key}:</strong>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
};

// Error Boundary to gracefully skip features that fail to render
class GeoJsonErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Error rendering GeoJSON feature:", this.props.featureName, error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return null;
    }
    return this.props.children;
  }
}

// This component handles the custom map click logic
const MapClickHandler = ({ layers }) => {
  const map = useMap();

  map.off('click'); // Remove previous click handlers to avoid duplicates
  map.on('click', (e) => {
    const clickedPoint = point([e.latlng.lng, e.latlng.lat]);
    const clickedFeatures = [];
    
    const clickThresholdPixels = 10;
    const thresholdInKm = map.containerPointToLatLng([0, 0]).distanceTo(map.containerPointToLatLng([clickThresholdPixels, 0])) / 1000;

    layers.forEach(layerData => {
      if (!layerData.visible || !layerData.geometry) return;

      const geom = layerData.geometry;
      let isMatch = false;

      try {
        switch (geom.type) {
          case "Polygon":
            isMatch = booleanPointInPolygon(clickedPoint, polygon(geom.coordinates));
            break;
          case "MultiPolygon":
            // Check if the point is inside any of the polygons
            isMatch = geom.coordinates.some(p => booleanPointInPolygon(clickedPoint, polygon(p)));
            break;
          case "LineString":
            isMatch = pointToLineDistance(clickedPoint, lineString(geom.coordinates), { units: 'kilometers' }) < thresholdInKm;
            break;
          case "MultiLineString":
            // Check if the point is close to any of the lines
            isMatch = geom.coordinates.some(l => pointToLineDistance(clickedPoint, lineString(l), { units: 'kilometers' }) < thresholdInKm);
            break;
          case "Point":
            isMatch = distance(clickedPoint, point(geom.coordinates), { units: 'kilometers' }) < thresholdInKm;
            break;
          case "MultiPoint":
            // Check if the point is close to any of the points
            isMatch = geom.coordinates.some(p => distance(clickedPoint, point(p), { units: 'kilometers' }) < thresholdInKm);
            break;
        }
      } catch (err) {
        console.error(`Error processing geometry for feature '${layerData.name}':`, err);
      }


      if (isMatch) {
        clickedFeatures.push(layerData);
      }
    });

    if (clickedFeatures.length > 0) {
      const popupContent = `
        <div class="custom-popup">
          <h4>${clickedFeatures.length} Feature(s) Found</h4>
          <ul>
            ${clickedFeatures.map(f => `<li>${f.name || 'Unnamed Feature'}</li>`).join('')}
          </ul>
        </div>
      `;
      map.openPopup(popupContent, e.latlng);
    }
  });

  return null;
};

const MapView = ({ kmlLayers }) => {
  const position = [45.5231, -122.6765]; // Portland, OR coordinates

  return (
    <MapContainer center={position} zoom={10} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      
      <MapClickHandler layers={kmlLayers} />
      
      {kmlLayers.map((layerData) => {
        if (!layerData.visible || !layerData.geometry) {
          return null;
        }

        const geoJsonFeature = {
          type: "Feature",
          properties: {
            name: layerData.name,
            description: layerData.description,
            sourceFile: layerData.sourceFile,
          },
          geometry: layerData.geometry,
        };

        return (
          <GeoJsonErrorBoundary key={`${layerData.sourceFile}-${layerData.id}`} featureName={geoJsonFeature.properties.name}>
            <GeoJSON 
              data={geoJsonFeature} 
              style={() => ({
                color: '#ff0000',
                weight: 2,
                fillColor: '#ff6666',
                fillOpacity: 0.4,
              })}
            />
          </GeoJsonErrorBoundary>
        );
      })}
    </MapContainer>
  );
};

export default MapView;

