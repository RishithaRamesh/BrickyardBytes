import React, { useState ,useEffect} from "react";

export default function Menu({ restaurant, menuItems, onClose, onConfirm }) {
  const [selectedId, setSelectedId] = useState("");
  const [qty, setQty] = useState(1);
  const [cart, setCart] = useState([]); // [{id, name, price, qty}]
  const [tip, setTip] = useState("0");

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "auto";
    };
  }, []);

  const addToCart = () => {
    const idNum = Number(selectedId);
    const item = menuItems.find((m) => m.id === idNum);
    if (!item || qty <= 0) return;
    setCart((prev) => {
      const existing = prev.find((p) => p.id === idNum);
      if (existing) {
        return prev.map((p) => p.id === idNum ? { ...p, qty: p.qty + qty } : p);
      }
      return [...prev, { id: item.id, name: item.name, price: Number(item.price) || 0, qty }];
    });
    setQty(1);
  };

  const updateQty = (id, newQty) => {
    setCart((prev) => prev.map((p) => p.id === id ? { ...p, qty: Math.max(Number(newQty) || 0, 0) } : p));
  };

  const removeItem = (id) => {
    setCart((prev) => prev.filter((p) => p.id !== id));
  };

  const total = cart.reduce((sum, i) => sum + i.qty * i.price, 0);
  const parsedTip = Math.max(Number(tip) || 0, 0);

  const handleConfirm = () => {
    if (cart.length > 0) {
      onConfirm(cart, parsedTip);
      setCart([]);
      setTip("0");
    }
    onClose();
  };

  return (
    <div className="menu-popup">
      <div className="menu-popup-content">
        <h4>Select items from {restaurant}</h4>

        <div className="form-group" style={{ display: 'flex', gap: 8 }}>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} style={{ flex: 1 }}>
            <option value="">-- choose an item --</option>
            {menuItems.map((m) => (
              <option key={m.id} value={m.id}>{m.name} — ${Number(m.price).toFixed(2)}</option>
            ))}
          </select>
          <input type="number" min="1" value={qty} onChange={(e) => setQty(Math.max(Number(e.target.value) || 1, 1))} style={{ width: 90 }} />
          <button className="btn btn-secondary" onClick={addToCart}>Add</button>
        </div>

        {cart.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h5>Order summary</h5>
            <ul className="order-list">
              {cart.map((i) => (
                <li key={i.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span>{i.qty}x {i.name} — ${(i.price * i.qty).toFixed(2)}</span>
                  <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input type="number" min="0" value={i.qty} onChange={(e) => updateQty(i.id, e.target.value)} style={{ width: 70 }} />
                    <button className="btn btn-secondary" onClick={() => removeItem(i.id)}>Remove</button>
                  </span>
                </li>
              ))}
            </ul>
            <div style={{ display: 'flex', justifyContent: 'flex-end', fontWeight: 700 }}>
              <div style={{ textAlign: 'right' }}>
                <div>Items total: ${total.toFixed(2)}</div>
                <div style={{ marginTop: 4 }}>
                  <label htmlFor="tip-input" style={{ fontWeight: 400, marginRight: 8 }}>
                    Tip for broadcaster (optional):
                  </label>
                  <input
                    id="tip-input"
                    type="number"
                    min="0"
                    step="0.5"
                    value={tip}
                    onChange={(e) => setTip(e.target.value)}
                    style={{ width: 100 }}
                  />
                </div>
                <div style={{ marginTop: 4, fontWeight: 700 }}>
                  Grand total: ${(total + parsedTip).toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="menu-actions" style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleConfirm} disabled={cart.length === 0}>
            Confirm Order{cart.length ? ` ($${(total + parsedTip).toFixed(2)})` : ''}
          </button>
        </div>
      </div>
    </div>
  );
}
