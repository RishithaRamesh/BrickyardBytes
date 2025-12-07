import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { listMyRunsHistory, listJoinedRunsHistory } from '../services/runsService';

function parseOrderItems(raw) {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  try {
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

function formatOrderDescription(order) {
  const parsed = parseOrderItems(order?.items);
  if (Array.isArray(parsed)) {
    return parsed
      .map((item) => {
        const name = item?.item || item?.name || 'Item';
        const qty = item?.qty || item?.quantity || 1;
        return `${name} x${qty}`;
      })
      .join(', ');
  }
  if (parsed && typeof parsed === 'object') {
    const name = parsed.item || parsed.name || 'Item';
    const qty = parsed.qty || parsed.quantity || 1;
    return `${name} x${qty}`;
  }
  return typeof order?.items === 'string' ? order.items : 'Order';
}

function customerLabel(order) {
  if (order?.user_email) {
    const value = order.user_email;
    if (value.includes('@')) return value;
    return `User #${value}`;
  }
  if (order?.user_username) return order.user_username;
  if (order?.user_id) return `User #${order.user_id}`;
  return 'Customer';
}

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
      setMyHistory(mine);
      setJoinedHistory(joined);
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
                  {Array.isArray(run.orders) && run.orders.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <h4>Orders</h4>
                      <ul>
                        {run.orders.map((o) => (
                          <li key={o.id} style={{ marginBottom: 8 }}>
                            <div>
                              <strong>{customerLabel(o)}</strong>{' '}
                              <span>{formatOrderDescription(o)}</span>
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#555' }}>
                              ${Number(o.amount || 0).toFixed(2)} • {o.status}
                            </div>
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
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
