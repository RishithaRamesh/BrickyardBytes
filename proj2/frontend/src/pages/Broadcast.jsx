import React, { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";
import restaurantsData from "./restaurants.json";
import { createRun, getRunDescriptionSuggestion } from "../services/runsService";

export default function Broadcast() {
  /* Broadcast page component
    Allows users to broadcast a new food run
    Error handling: ensures restaurant and ETA are provided
  */
  const [restaurant, setRestaurant] = useState("");
  const [eta, setEta] = useState("");
  const [dropPoint, setDropPoint] = useState("");
  const [capacity, setCapacity] = useState(5);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState("");
  const [suggestionError, setSuggestionError] = useState("");
  const [suggestionLoading, setSuggestionLoading] = useState(false);

  const { user } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!restaurant || !eta) {
      setError("Please fill out both the restaurant and ETA!");
      return;
    }
    if (!dropPoint) {
      setError("Please provide a drop point!");
      return;
    }

    setError("");
    setLoading(true);
    try {
      await createRun({
        restaurant,
        drop_point: dropPoint,
        eta,
        capacity: Number(capacity),
        description: suggestion,
      });
      // Keep the user on this tab, but you can navigate to Your Runs if preferred
      setRestaurant("");
      setEta("");
      setDropPoint("");
      setCapacity(5);
      setSuggestion("");
      setSuggestionError("");
      alert("Run broadcasted successfully!");
      navigate("/your-runs");
    } catch (e) {
      setError(e.message || "Failed to broadcast run");
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestDescription = async () => {
    if (!restaurant || !dropPoint || !eta) {
      setSuggestionError("Select a restaurant, drop point, and ETA to generate a blurb.");
      return;
    }
    setSuggestionError("");
    setSuggestionLoading(true);
    try {
      const res = await getRunDescriptionSuggestion({
        restaurant,
        drop_point: dropPoint,
        eta,
      });
      setSuggestion(res?.suggestion || "");
    } catch (e) {
      setSuggestionError(e.message || "Unable to fetch a suggestion.");
    } finally {
      setSuggestionLoading(false);
    }
  };

  return (
    <div className="broadcast-container">
      <div className="card broadcast-card">
        <h2 className="card-title">Broadcast a New Run</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="restaurant">Restaurant</label>
            <select
              id="restaurant"
              value={restaurant}
              onChange={(e) => setRestaurant(e.target.value)}
            >
              <option value="">-- Select a restaurant --</option>
              {Array.isArray(restaurantsData?.restaurants) &&
                restaurantsData.restaurants.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="drop">Drop Point</label>
            <input
              id="drop"
              type="text"
              value={dropPoint}
              onChange={(e) => setDropPoint(e.target.value)}
              placeholder="e.g., EBII Lobby"
              // required
            />
          </div>

          <div className="form-group">
            <label htmlFor="eta">ETA</label>
            <input
              id="eta"
              type="text"
              value={eta}
              onChange={(e) => setEta(e.target.value)}
              placeholder="e.g., 2:30 PM"
            />
          </div>

          <div className="form-group">
            <label htmlFor="capacity">Max joiners</label>
            <input
              id="capacity"
              type="number"
              value={capacity}
              onChange={(e) => setCapacity(Number(e.target.value))}
              min="1"
            />
          </div>

          <div className="form-group">
            <label htmlFor="ai-suggestion">Need a quick description?</label>
            <div className="ai-suggestion-row">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleSuggestDescription}
                disabled={suggestionLoading}
              >
                {suggestionLoading ? "Generating..." : "Smart Suggest description"}
              </button>
            </div>
            <textarea
              id="ai-suggestion"
              className="ai-suggestion"
              value={suggestion}
              onChange={(e) => setSuggestion(e.target.value)}
              placeholder="Generate a blurb or type your own run description"
              rows={3}
            />
            {suggestionError && <p className="form-error">{suggestionError}</p>}
          </div>

          {error && <p className="form-error">{error}</p>}

          <button type="submit" className="btn btn-primary full-width" disabled={loading}>
            {loading ? "Broadcasting..." : "Broadcast"}
          </button>
        </form>
      </div>
    </div>
  );
}
