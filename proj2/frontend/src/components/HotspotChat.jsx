import React, { useEffect, useMemo, useState } from 'react';
import { listAvailableRuns } from '../services/runsService';

const fallbackHotspots = [
  { name: 'Talley Student Union', tip: 'Most runs head here around lunch. Expect lots of Port City Java orders.' },
  { name: 'Hunt Library Cafe', tip: 'Common Grounds stays busy during study jams, especially evenings.' },
  { name: 'EB2 Atrium', tip: 'Engineering students often stage drop-offs near the EBII Lobby.' },
];

function buildHotspotSummary(availableRuns = []) {
  if (!Array.isArray(availableRuns) || availableRuns.length === 0) {
    return fallbackHotspots;
  }
  const grouped = Object.values(
    availableRuns.reduce((acc, run) => {
      const key = `${run.restaurant}|${run.drop_point}`;
      if (!acc[key]) {
        acc[key] = {
          name: run.restaurant,
          tip: `Drop near ${run.drop_point} · ${run.seats_remaining} seats open`,
        };
      }
      return acc;
    }, {})
  );
  return grouped.length ? grouped : fallbackHotspots;
}

function craftAiResponse(message, availableRuns) {
  const cleaned = (message || '').toLowerCase();
  const hotspots = buildHotspotSummary(availableRuns);
  if (!cleaned.trim()) {
    return 'Try asking me about hotspots or where the next runs are happening!';
  }
  if (cleaned.includes('hotspot') || cleaned.includes('where') || cleaned.includes('run')) {
    const previews = hotspots
      .slice(0, 3)
      .map((spot, idx) => `${idx + 1}. ${spot.name} — ${spot.tip}`)
      .join('\n');
    return `Here are some run hotspots right now:\n${previews}`;
  }
  if (cleaned.includes('thanks') || cleaned.includes('thank')) {
    return "Happy to help! Ping me anytime you're scouting for drop points.";
  }
  if (cleaned.includes('suggest') || cleaned.includes('idea')) {
    return 'If you want to broadcast, target areas with study spaces (Hunt, Talley) or dorm clusters (Wolf Ridge).';
  }
  return "I'm tuned for BrickyardBytes chatter. Ask about hotspots, drop points, or good places to broadcast!";
}

export default function HotspotChat({ availableRuns }) {
  const [messages, setMessages] = useState([
    { from: 'ai', text: 'Hi! I am your campus-run scout. Ask about hotspots or drop points.' },
  ]);
  const [input, setInput] = useState('');
  const [runsSnapshot, setRunsSnapshot] = useState(availableRuns || []);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (availableRuns) {
      setRunsSnapshot(availableRuns);
    }
  }, [availableRuns]);

  useEffect(() => {
    if (availableRuns) return;
    let cancelled = false;
    async function loadRuns() {
      try {
        const data = await listAvailableRuns();
        if (!cancelled) {
          setRunsSnapshot(Array.isArray(data) ? data : []);
          setLoadError('');
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err?.message || 'Unable to fetch runs for now. Showing campus presets.');
          setRunsSnapshot([]);
        }
      }
    }
    loadRuns();
    return () => {
      cancelled = true;
    };
  }, [availableRuns]);

  const hotspots = useMemo(() => buildHotspotSummary(runsSnapshot), [runsSnapshot]);

  const sendMessage = (evt) => {
    evt.preventDefault();
    const trimmed = input.trim();
    const aiReply = craftAiResponse(trimmed, runsSnapshot);
    setMessages((prev) => [
      ...prev,
      ...(trimmed ? [{ from: 'user', text: trimmed }] : []),
      { from: 'ai', text: aiReply },
    ]);
    setInput('');
  };

  return (
    <div className="chatbot-card">
      <div className="chatbot-card__header">
        <div>
          <h4>Campus Hotspot Bot</h4>
          <p>Powered by lightweight AI heuristics</p>
        </div>
        <div className="chatbot-card__hotspots">
          {hotspots.slice(0, 2).map((spot) => (
            <span key={spot.name}>{spot.name}</span>
          ))}
        </div>
      </div>
      {loadError && (
        <div className="chatbot-hint" role="status">
          {loadError}
        </div>
      )}
      <div className="chatbot-messages" aria-live="polite">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chatbot-message chatbot-message--${msg.from}`}>
            {msg.text.split('\n').map((line, lineIdx) => (
              <span key={lineIdx}>{line}</span>
            ))}
          </div>
        ))}
      </div>
      <form className="chatbot-input" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about hotspots or where to broadcast..."
        />
        <button type="submit">Ask</button>
      </form>
    </div>
  );
}
