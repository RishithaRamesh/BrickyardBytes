import React, { useEffect, useState } from 'react';
import RunCard from "../components/RunCard";
import Menu from "../components/Menu";
import { useAuth } from '../hooks/useAuth';
import menuData from "../mock_data/menuData.json";
import { listAvailableRuns, listJoinedRuns, joinRun, unjoinRun } from "../services/runsService";
import { useToast } from "../context/ToastContext";

export default function Home() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [available, setAvailable] = useState([]);
  const [joined, setJoined] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeRun, setActiveRun] = useState(null);
  const [activeMenuItems, setActiveMenuItems] = useState([]);
  const [pinVisible, setPinVisible] = useState({}); // map runId -> bool
  

  const DUMMY_MENU = [
    { id: 1, name: 'Classic Combo', price: 9.99 },
    { id: 2, name: 'Veggie Special', price: 8.49 },
    { id: 3, name: 'Chicken Wrap', price: 7.99 },
    { id: 4, name: 'Iced Coffee', price: 3.49 },
  ];

  function getMenuForRestaurant(name) {
    const direct = menuData?.[name];
    if (Array.isArray(direct) && direct.length > 0) return direct;
    const n = (name || '').toLowerCase();
    if (n.includes('common grounds')) return menuData['Common Grounds Cafe Hunt Library'] || DUMMY_MENU;
    if (n.includes('port city') || n.includes('pcj')) return menuData['Port City Java EBII'] || menuData['PCJ'] || DUMMY_MENU;
    if (n.includes('hill of beans')) return menuData['Hill of Beans Hill Library'] || DUMMY_MENU;
    if (n.includes('jason')) return menuData["Jason's"] || DUMMY_MENU;
    return DUMMY_MENU;
  }
  

  async function refresh() {
    setError("");
    try {
      const [a, j] = await Promise.all([listAvailableRuns(), listJoinedRuns()]);
      setAvailable(a);
      setJoined(j);
    } catch (e) {
      setError(e.message || "Failed to load runs");
    }
  }

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  function handleJoinClick(run) {
    if (run.runner_username === user.username) {
      showToast("You cannot join your own run.", { type: 'warning' });
      return;
    }
    const items = getMenuForRestaurant(run.restaurant);
    setActiveMenuItems(items);
    setActiveRun(run);
  }

  async function handleConfirmOrder(cart = [], tipAmount = 0) {
    if (!activeRun) return;
    // cart: [{id, name, price, qty}]
    const amount = cart.reduce((sum, i) => sum + (Number(i.price) || 0) * (Number(i.qty) || 0), 0);
    const safeTip = Math.max(Number(tipAmount) || 0, 0);
    const items = cart
      .filter(i => (Number(i.qty) || 0) > 0)
      .map(i => `${i.qty}x ${i.name}`)
      .join(", ");
    setLoading(true);
    setError("");
    try {
      const resp = await joinRun(activeRun.id, { items, amount, tip: safeTip });
      if (resp?.pin) {
        showToast(`Your pickup PIN is ${resp.pin}`, { type: 'info', duration: 7000 });
      }
      await refresh();
    } catch (e) {
      setError(e.message || "Failed to join run");
    } finally {
      setLoading(false);
      setActiveRun(null);
    }
  }

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Active Runs</h1>
        <button className="btn btn-secondary" onClick={refresh} disabled={loading}>Refresh</button>
      </div>

      {error && (<div style={{ color: 'red', marginBottom: 12 }}>{error}</div>)}

      <div className="runs-columns">
        <div className="runs-section">
          <h3>Available Runs</h3>
          <div className="runs-list scrollable">
            {available.length > 0 ? (
              available.map((run) => (
                <RunCard
                  key={run.id}
                  run={run}
                  onJoin={handleJoinClick}
                  joinedRuns={joined}
                />
              ))
            ) : (
              <p>No available runs.</p>
            )}
          </div>
        </div>

        <div className="runs-section">
          <h3>Joined Runs</h3>
          <div className="runs-list scrollable">
            {joined.length > 0 ? (
              joined.map((run) => (
                <div key={run.id} className="run-card">
                  <div className="run-card-header">
                    <h3>{run.restaurant}</h3>
                    <span className="run-card-runner">by {run.runner_username}</span>
                  </div>
                  <div className="run-card-body">
                    <p><strong>ETA:</strong> {run.eta}</p>
                    <p><strong>Seats left:</strong> {run.seats_remaining}</p>
                    {run.description && (
                      <p className="run-card-description">{run.description}</p>
                    )}
                    {run.my_order?.pin && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <strong>Your PIN:</strong>
                        <code>{pinVisible[run.id] ? run.my_order.pin : '••••'}</code>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '6px 10px' }}
                          onClick={() => setPinVisible((v) => ({ ...v, [run.id]: !v[run.id] }))}
                          title={pinVisible[run.id] ? 'Hide PIN' : 'Show PIN'}
                        >{pinVisible[run.id] ? '🙈' : '👁️'}</button>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '6px 10px' }}
                          onClick={async () => {
                            try {
                              await navigator.clipboard.writeText(run.my_order.pin);
                              showToast('PIN copied to clipboard', { type: 'success' });
                            } catch {
                              showToast('Copy failed. Please copy manually.', { type: 'warning' });
                            }
                          }}
                        >Copy</button>
                      </div>
                    )}
                    {typeof run.my_order?.tip === "number" && (
                      <p style={{ marginTop: 8 }}>
                        <strong>Your tip:</strong> ${Number(run.my_order.tip).toFixed(2)}
                      </p>
                    )}
                  </div>
                  <div className="run-card-footer">
                    <button className="btn btn-secondary" disabled>
                      Joined
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ marginLeft: 8 }}
                      onClick={async () => {
                        setLoading(true);
                        setError("");
                        try { await unjoinRun(run.id); await refresh(); } catch (e) { setError(e.message || "Failed to unjoin"); } finally { setLoading(false); }
                      }}
                    >
                      Unjoin
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p>You haven’t joined any runs yet.</p>
            )}
          </div>
        </div>
      </div>

      {activeRun && (
        <Menu
          restaurant={activeRun.restaurant}
          menuItems={activeMenuItems || []}
          onClose={() => setActiveRun(null)}
          onConfirm={handleConfirmOrder}
        />
      )}
    </div>
  );
}
