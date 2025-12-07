import React, { useEffect, useMemo, useState } from 'react';
import { listAvailableRuns } from '../services/runsService';

const fallbackHotspots = [
  { name: 'Talley Student Union', tip: 'Most runs head here around lunch. Expect lots of Port City Java orders.' },
  { name: 'Hunt Library Cafe', tip: 'Common Grounds stays busy during study jams, especially evenings.' },
  { name: 'EB2 Atrium', tip: 'Engineering students often stage drop-offs near the EBII Lobby.' },
];

function describeRunInsights(runs = []) {
  if (!Array.isArray(runs) || runs.length === 0) {
    return 'No live runs right now. I will stick with campus presets until a runner goes active.';
  }
  const openSeats = runs.reduce(
    (sum, run) => sum + (Number(run?.seats_remaining) || 0),
    0
  );
  const dropCounts = runs.reduce((acc, run) => {
    const drop = run?.drop_point?.trim() || 'Drop TBD';
    acc[drop] = (acc[drop] || 0) + 1;
    return acc;
  }, {});
  const [topDropName, topDropCount] =
    Object.entries(dropCounts).sort((a, b) => b[1] - a[1])[0] || [];
  const soonestRun =
    [...runs].sort((a, b) => {
      const aEta = `${a?.eta || ''}`;
      const bEta = `${b?.eta || ''}`;
      return aEta.localeCompare(bEta);
    })[0] || {};
  const soonestText = soonestRun?.restaurant
    ? `${soonestRun.restaurant} → ${soonestRun.drop_point} at ${
        soonestRun.eta || 'TBD'
      }`
    : 'Waiting for the next ETA';
  const busiestText = topDropName
    ? `${topDropName} (${topDropCount} run${
        topDropCount === 1 ? '' : 's'
      } live)`
    : 'Still gathering venues';
  return (
    `Live snapshot: ${runs.length} runs • ${openSeats} open seats.\n` +
    `Busiest drop: ${busiestText}.\n` +
    `Soonest departure: ${soonestText}.`
  );
}

function describeLowSeatRuns(runs = []) {
  const urgent = (Array.isArray(runs) ? runs : [])
    .filter((run) => Number(run?.seats_remaining) <= 1)
    .slice(0, 3);
  if (!urgent.length) {
    return 'No runs are near capacity right now. Plenty of seats if you hop in soon!';
  }
  const lines = urgent.map(
    (run) =>
      `${run.restaurant} near ${run.drop_point} — ${run.seats_remaining} seat left`
  );
  return `These runs are almost full:\n${lines.join('\n')}`;
}

function describeBroadcastIdeas(runs = []) {
  const hotspots = buildHotspotSummary(runs).slice(0, 2);
  const preview = hotspots
    .map((spot, idx) => `${idx + 1}. ${spot.name} — ${spot.tip}`)
    .join('\n');
  return (
    'Broadcast game-plan:\n' +
    `${preview}\n` +
    'Hardcoded tip: rotate between a busy academic core (Talley/Hunt) and a residence-heavy zone (Wolf Ridge) to catch both study and dinner crowds.'
  );
}

const quickActions = [
  { id: 'insights', label: 'Run Insights', buildMessage: describeRunInsights },
  { id: 'seat-alerts', label: 'Seat Alerts', buildMessage: describeLowSeatRuns },
  {
    id: 'broadcast',
    label: 'Broadcast Tips',
    buildMessage: describeBroadcastIdeas,
  },
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
  if (
    cleaned.includes('insight') ||
    cleaned.includes('stat') ||
    cleaned.includes('summary')
  ) {
    return describeRunInsights(availableRuns);
  }
  if (cleaned.includes('seat') || cleaned.includes('full') || cleaned.includes('capacity')) {
    return describeLowSeatRuns(availableRuns);
  }
  if (cleaned.includes('hotspot') || cleaned.includes('where') || cleaned.includes('run')) {
    const previews = hotspots
      .slice(0, 3)
      .map((spot, idx) => `${idx + 1}. ${spot.name} — ${spot.tip}`)
      .join('\n');
    return `Here are some run hotspots right now:\n${previews}`;
  }
  if (cleaned.includes('broadcast') || cleaned.includes('tip')) {
    return describeBroadcastIdeas(availableRuns);
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

  const handleActionClick = (action) => {
    const aiReply = action.buildMessage(runsSnapshot);
    setMessages((prev) => [
      ...prev,
      { from: 'user', text: `[Button] ${action.label}` },
      { from: 'ai', text: aiReply },
    ]);
  };

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
      <div className="chatbot-actions" role="group" aria-label="Quick chatbot actions">
        {quickActions.map((action) => (
          <button
            key={action.id}
            type="button"
            className="chatbot-action-button"
            onClick={() => handleActionClick(action)}
          >
            {action.label}
          </button>
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
