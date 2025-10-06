import React, { useState } from 'react';
import './LayerToggle.css';

const LayerToggle = ({ layers, visibility, onToggle }) => {
  const [isOpen, setIsOpen] = useState(false);
  const loadedCount = layers.length;

  return (
    <div className="layer-toggle">
      <button onClick={() => setIsOpen(!isOpen)} className="toggle-button">
        Overlays ({loadedCount})
      </button>
      {isOpen && (
        <div className="layer-menu">
          <h4>Toggle KML Layers</h4>
          {layers.map((layer, index) => (
            <div key={index} className="layer-item">
              <input
                type="checkbox"
                id={`layer-${index}`}
                checked={visibility[index]}
                onChange={() => onToggle(index)}
              />
              <label htmlFor={`layer-${index}`}>
                {/* Attempt to find a name, otherwise use index */}
                {layer.features[0]?.properties?.name || `Layer ${index + 1}`}
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LayerToggle;
