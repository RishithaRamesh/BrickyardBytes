import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { listMyRuns, completeRun, cancelRun } from "../services/runsService";

export default function YourRuns() {
  const { user } = useAuth();
  const [myRuns, setMyRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    try {
      const mine = await listMyRuns();
      setMyRuns(mine);
    } catch (e) {
      setError(e.message || "Failed to load runs");
    }
  }

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  async function handleComplete(run) {
    if (!window.confirm("Mark this run complete and award points?")) return;
    setLoading(true);
    setError("");
    try {
      await completeRun(run.id);
      await refresh();
    } catch (e) {
      setError(e.message || "Failed to complete run");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel(run) {
    if (!window.confirm("Cancel this run?")) return;
    setLoading(true);
    setError("");
    try {
      await cancelRun(run.id);
      await refresh();
    } catch (e) {
      setError(e.message || "Failed to cancel run");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Your Runs</h1>
        <button className="btn btn-secondary" onClick={refresh} disabled={loading}>Refresh</button>
      </div>

      {error && (<div style={{ color: 'red', marginBottom: 12 }}>{error}</div>)}

      <section style={{ marginBottom: 24 }}>
        <h2>My Runs</h2>
        {myRuns.length === 0 ? (
          <p>You haven’t broadcasted any runs yet.</p>
        ) : (
          <div className="runs-list">
            {myRuns.map((run) => {
              const tipValues = Array.isArray(run.orders)
                ? run.orders.map((o) => Math.max(Number(o.tip) || 0, 0))
                : [];
              const highestTip = tipValues.reduce(
                (max, val) => (val > max ? val : max),
                0
              );
              return (
                <div key={run.id} className="run-card run-card--auto">
                <div className="run-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <h3 style={{ margin: 0 }}><Link to={`/your-runs/${run.id}`}>{run.restaurant}</Link></h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {run.status === 'active' && (
                      <span className="badge badge-active">Active</span>
                    )}
                    <span className="run-card-runner">ETA: {run.eta}</span>
                  </div>
                </div>
                <div className="run-card-body">
                  <p><strong>Drop:</strong> {run.drop_point}</p>
                  <p><strong>Max joiners:</strong> {run.capacity}</p>
                  <p><strong>Joined:</strong> {Array.isArray(run.orders) ? run.orders.length : 0}</p>
                  <p><strong>Seats left:</strong> {run.seats_remaining}</p>
                  {highestTip > 0 && (
                    <p><strong>Highest tip:</strong> ${highestTip.toFixed(2)}</p>
                  )}
                  {run.description && (
                    <p className="run-card-description">{run.description}</p>
                  )}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <Link className="btn btn-secondary" to={`/your-runs/${run.id}`}>Manage</Link>
                    {run.status === 'active' && (
                      <>
                        <button className="btn btn-secondary" onClick={() => handleComplete(run)} disabled={loading}>Complete</button>
                        <button className="btn btn-secondary" onClick={() => handleCancel(run)} disabled={loading}>Cancel</button>
                      </>
                    )}
                  </div>
                </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

    </div>
  );
}
