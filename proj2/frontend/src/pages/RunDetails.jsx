import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getRunById, removeOrder, completeRun, cancelRun, verifyOrderPin, getRunLoadEstimate } from "../services/runsService";
import { useToast } from "../context/ToastContext";

export default function RunDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { showToast } = useToast();
  const [verifyingId, setVerifyingId] = useState(null);
  const [pinValue, setPinValue] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [loadAssessment, setLoadAssessment] = useState("");
  const [loadAssessmentError, setLoadAssessmentError] = useState("");
  const [loadAssessmentLoading, setLoadAssessmentLoading] = useState(false);

  async function load() {
    setError("");
    try {
      const data = await getRunById(id);
      setRun(data);
      setLoadAssessment("");
      setLoadAssessmentError("");
    } catch (e) {
      setError(e.message || "Failed to load run");
    }
  }

  useEffect(() => {
    if (id) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleRemove(orderId) {
    if (!window.confirm("Remove this order from the run?")) return;
    setLoading(true);
    setError("");
    try {
      await removeOrder(run.id, orderId);
      await load();
    } catch (e) {
      setError(e.message || "Failed to remove order");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadAssessment() {
    if (!run) return;
    setLoadAssessment("");
    setLoadAssessmentError("");
    setLoadAssessmentLoading(true);
    try {
      const res = await getRunLoadEstimate({
        restaurant: run.restaurant,
        drop_point: run.drop_point,
        eta: run.eta,
        capacity: run.capacity,
        seats_remaining: run.seats_remaining,
        orders: Array.isArray(run.orders)
          ? run.orders.map((o) => ({
              items: o.items,
              amount: o.amount,
            }))
          : [],
      });
      setLoadAssessment(res?.assessment || "");
    } catch (e) {
      const msg = (e.message || "Unable to fetch load estimate").replace(/\s*\(\d+\)$/, "");
      setLoadAssessmentError(msg);
    } finally {
      setLoadAssessmentLoading(false);
    }
  }

  async function handleComplete() {
    if (!window.confirm("Mark this run complete and award points?")) return;
    setLoading(true);
    setError("");
    try {
      await completeRun(run.id);
      await load();
    } catch (e) {
      setError(e.message || "Failed to complete run");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel() {
    if (!window.confirm("Cancel this run?")) return;
    setLoading(true);
    setError("");
    try {
      await cancelRun(run.id);
      await load();
    } catch (e) {
      setError(e.message || "Failed to cancel run");
    } finally {
      setLoading(false);
    }
  }

  const joinedCount = run ? Math.max((run.capacity || 0) - (run.seats_remaining || 0), 0) : 0;

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Run Details</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link className="btn btn-secondary" to="/your-runs">Back</Link>
          <button className="btn btn-secondary" onClick={load} disabled={loading}>Refresh</button>
        </div>
      </div>

      {error && (<div style={{ color: 'red', marginBottom: 12 }}>{error}</div>)}

      {!run ? (
        <p>Loading…</p>
      ) : (
        <div className="run-card run-card--details" style={{ maxWidth: 800 }}>
          <div className="run-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <h3 style={{ margin: 0 }}>{run.restaurant}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {run.status === 'active' && (
                <span className="badge badge-active">Active</span>
              )}
              <span className="run-card-runner">ETA: {run.eta}</span>
            </div>
          </div>
          <div className="run-card-body">
            <p><strong>Status:</strong> {run.status}</p>
            <p><strong>Drop:</strong> {run.drop_point}</p>
            <p><strong>Max joiners:</strong> {run.capacity}</p>
            <p><strong>Seats left:</strong> {run.seats_remaining}</p>
            <p><strong>Total participants:</strong> {1 + (Array.isArray(run.orders) ? run.orders.length : 0)}</p>

            <div className="card" style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <h4 style={{ margin: 0 }}>AI Load Estimate</h4>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleLoadAssessment}
                  disabled={loadAssessmentLoading}
                >
                  {loadAssessmentLoading ? "Analyzing..." : "Check load"}
                </button>
              </div>
              {loadAssessment && (
                <p style={{ marginTop: 8 }}>{loadAssessment}</p>
              )}
              {loadAssessmentError && (
                <p className="form-error" style={{ marginTop: 8 }}>{loadAssessmentError}</p>
              )}
              {!loadAssessment && !loadAssessmentError && !loadAssessmentLoading && (
                <p style={{ marginTop: 8, color: '#666' }}>
                  Get a quick AI assessment of how heavy this run looks based on current orders.
                </p>
              )}
            </div>

            {run.status === 'active' && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <button className="btn btn-secondary" onClick={handleComplete} disabled={loading}>Complete</button>
                <button className="btn btn-secondary" onClick={handleCancel} disabled={loading}>Cancel</button>
              </div>
            )}

            <h4>Joined Users ({joinedCount})</h4>
            {Array.isArray(run.orders) && run.orders.length > 0 ? (
              <ul>
                {run.orders.map((o) => (
                  <li key={o.id} style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: 8, borderBottom: '1px solid #eee' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <span>
                        <strong>{o.user_email}:</strong> {o.items} (${Number(o.amount).toFixed(2)})
                        {o.status && (
                          <span style={{ marginLeft: 8, fontStyle: 'italic' }}>status: {o.status}</span>
                        )}
                      </span>
                      {run.status === 'active' && (
                        <span style={{ display: 'flex', gap: 8 }}>
                          {o.status !== 'delivered' && (
                            <button
                              className="btn btn-secondary"
                              onClick={() => { setVerifyingId(o.id); setPinValue(""); setShowPin(false); }}
                              disabled={loading}
                            >Verify PIN</button>
                          )}
                          <button className="btn btn-secondary" onClick={() => handleRemove(o.id)} disabled={loading}>Remove</button>
                        </span>
                      )}
                    </div>
                    {verifyingId === o.id && (
                      <div className="card" style={{ padding: '12px', marginTop: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <input
                            type={showPin ? 'text' : 'password'}
                            placeholder="Enter 4-digit PIN"
                            value={pinValue}
                            onChange={(e) => setPinValue(e.target.value)}
                            style={{ flex: 1 }}
                          />
                          <button
                            className="btn btn-secondary"
                            onClick={() => setShowPin((v) => !v)}
                            title={showPin ? 'Hide PIN' : 'Show PIN'}
                          >{showPin ? '🙈' : '👁️'}</button>
                          <button
                            className="btn btn-primary"
                            onClick={async () => {
                              if (!pinValue) { showToast('Please enter a PIN', { type: 'warning' }); return; }
                              setLoading(true);
                              try {
                                await verifyOrderPin(run.id, o.id, pinValue);
                                showToast('PIN verified. Marked delivered.', { type: 'success' });
                                setVerifyingId(null);
                                setPinValue("");
                                await load();
                              } catch (e) {
                                const msg = (e.message || 'Failed to verify PIN').replace(/\s*\(\d+\)$/, '');
                                showToast(msg, { type: 'error' });
                              } finally {
                                setLoading(false);
                              }
                            }}
                          >Submit</button>
                          <button className="btn btn-secondary" onClick={() => { setVerifyingId(null); setPinValue(""); }}>Cancel</button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p>{joinedCount > 0 ? 'Joined users present but not yet visible. Try Refresh.' : 'No joined users yet.'}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}