import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { listMyRunsHistory, listJoinedRunsHistory } from '../services/runsService';

export default function History() {
  const { user } = useAuth();
  const [myHistory, setMyHistory] = useState([]);
  const [joinedHistory, setJoinedHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    setError('');
    setLoading(true);
    try {
      const [mine, joined] = await Promise.all([
        listMyRunsHistory(),
        listJoinedRunsHistory(),
      ]);
      const sortByIdDesc = (arr = []) =>
        [...arr].sort((a, b) => Number(b?.id || 0) - Number(a?.id || 0));
      setMyHistory(sortByIdDesc(mine));
      setJoinedHistory(sortByIdDesc(joined));
    } catch (e) {
      setError(e.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>History</h1>
        <button className="btn btn-secondary" onClick={refresh} disabled={loading}>Refresh</button>
      </div>

      {error && (<div style={{ color: 'red', marginBottom: 12 }}>{error}</div>)}

      <section style={{ marginBottom: 24 }}>
        <h2>My Broadcast History</h2>
        {myHistory.length === 0 ? (
          <p>No past broadcasts yet.</p>
        ) : (
          <div className="runs-list">
            {myHistory.map(run => (
              <div key={run.id} className="run-card">
                <div className="run-card-header">
                  <h3>{run.restaurant}</h3>
                  <span className="run-card-runner">Status: {run.status}</span>
                </div>
                <div className="run-card-body">
                  <p><strong>ETA:</strong> {run.eta}</p>
                  <p><strong>Drop:</strong> {run.drop_point}</p>
                  {run.description && (
                    <p className="run-card-description">{run.description}</p>
                  )}
                  {Array.isArray(run.orders) && run.orders.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <h4>Orders</h4>
                      <ul>
                        {run.orders.map(o => (
                          <li key={o.id}>
                            <strong>{o.user_email}:</strong> {o.items} (${Number(o.amount).toFixed(2)}) [{o.status}]
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2>Joined Runs History</h2>
        {joinedHistory.length === 0 ? (
          <p>No past joined runs.</p>
        ) : (
          <div className="runs-list">
            {joinedHistory.map(run => (
              <div key={run.id} className="run-card">
                <div className="run-card-header">
                  <h3>{run.restaurant}</h3>
                  <span className="run-card-runner">by {run.runner_username} — {run.status}</span>
                </div>
                <div className="run-card-body">
                  <p><strong>ETA:</strong> {run.eta}</p>
                  <p><strong>Drop:</strong> {run.drop_point}</p>
                  {run.description && (
                    <p className="run-card-description">{run.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
