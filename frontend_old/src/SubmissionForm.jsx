import React from 'react';
import './SubmissionForm.css';

const SubmissionForm = ({ location, onSubmit, onCancel }) => {

  // LOG 4: Check if the form is rendering and what props it's receiving.
  console.log('[SubmissionForm.jsx] Rendering with location:', location);

  const handleSubmit = (e) => {
    e.preventDefault();
    const { title, description } = e.target.elements;
    
    const newReport = {
      title: title.value,
      description: description.value,
      lat: location.lat,
      lng: location.lng,
    };
    onSubmit(newReport);
  };

  return (
    <div className="submission-form-container">
      <form onSubmit={handleSubmit} className="submission-form">
        <h3>New Situation Report</h3>
        <p>
          <strong>Lat:</strong> {location.lat.toFixed(5)} | <strong>Lng:</strong> {location.lng.toFixed(5)}
        </p>
        <div className="form-group">
          <label htmlFor="title">Title:</label>
          <input id="title" name="title" type="text" required />
        </div>
        <div className="form-group">
          <label htmlFor="description">Description:</label>
          <textarea id="description" name="description"></textarea>
        </div>
        <div className="form-buttons">
          <button type="submit" className="btn-submit">Submit</button>
          <button type="button" className="btn-cancel" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default SubmissionForm;

