import React, { useEffect, useMemo, useState } from 'react';
import { listAvailableRuns } from '../services/runsService';

const fallbackHotspots = [
  { name: 'Talley Student Union', tip: 'Most runs head here around lunch. Expect lots of Port City Java orders.' },
  { name: 'Hunt Library Cafe', tip: 'Common Grounds stays busy during study jams, especially evenings.' },
  { name: 'EB2 Atrium', tip: 'Engineering students often stage drop-offs near the EBII Lobby.' },
];

const STORAGE_KEY = 'hotspotChatHistory';

function ensureMessagePayload(payload) {
  if (!payload) return { text: "I'm not sure yet — try asking about hotspots, seats, or broadcasts." };
  if (typeof payload === 'string') return { text: payload };
  return payload;
}

function formatRunCard(run) {
  if (!run) return null;
  const restaurant = run.restaurant || 'Unknown spot';
  const dropPoint = run.drop_point || 'Drop TBD';
  const filled = Math.max((Number(run.capacity) || 0) - (Number(run.seats_remaining) || 0), 0);
  const seats = Number(run.seats_remaining) ?? 0;
  return {
    id: run.id,
    title: `${restaurant} → ${dropPoint}`,
    subtitle: `ETA ${run.eta || 'TBD'}`,
    detail: `${filled} joined · ${seats} seat${seats === 1 ? '' : 's'} left`,
  };
}

function describeRunInsights(runs = []) {
  if (!Array.isArray(runs) || runs.length === 0) {
    return {
      text: 'No live runs right now. I will stick with campus presets until a runner goes active.',
    };
  }
  const totals = runs.reduce(
    (acc, run) => {
      const seats = Number(run?.seats_remaining) || 0;
      const cap = Number(run?.capacity) || 0;
      acc.openSeats += seats;
      acc.joined += Math.max(cap - seats, 0);
      return acc;
    },
    { openSeats: 0, joined: 0 }
  );
  const dropCounts = runs.reduce((acc, run) => {
    const label = run?.drop_point?.trim() || 'Drop TBD';
    const key = label.toLowerCase();
    acc[key] = acc[key] || { count: 0, label };
    acc[key].count += 1;
    return acc;
  }, {});
  const topDropEntry =
    Object.values(dropCounts).sort((a, b) => b.count - a.count)[0] || null;
  const soonestRun =
    [...runs].sort((a, b) => {
      const aEta = `${a?.eta || ''}`;
      const bEta = `${b?.eta || ''}`;
      return aEta.localeCompare(bEta);
    })[0] || {};
  const fillRate =
    totals.joined + totals.openSeats === 0
      ? 0
      : (totals.joined / (totals.joined + totals.openSeats)) * 100;
  const text =
    `Live snapshot: ${runs.length} runs | fill ${fillRate.toFixed(0)}% | ${totals.openSeats} seats open.\n` +
    `Busiest drop: ${
      topDropEntry?.label || 'collecting data'
    } (${topDropEntry?.count || 0} run${
      topDropEntry?.count === 1 ? '' : 's'
    }).\n` +
    `Soonest departure: ${
      soonestRun?.restaurant
        ? `${soonestRun.restaurant} → ${soonestRun.drop_point} at ${soonestRun.eta || 'TBD'}`
        : 'Waiting for the next ETA'
    }.`;
  return {
    text,
    cards: [...runs]
      .sort(
        (a, b) => {
          const bFill =
            (Number(b?.capacity) || 0) - (Number(b?.seats_remaining) || 0);
          const aFill =
            (Number(a?.capacity) || 0) - (Number(a?.seats_remaining) || 0);
          return bFill - aFill;
        }
      )
      .slice(0, 3)
      .map(formatRunCard)
      .filter(Boolean),
  };
}

function describeLowSeatRuns(runs = []) {
  const urgent = (Array.isArray(runs) ? runs : [])
    .filter((run) => Number(run?.seats_remaining) <= 1)
    .slice(0, 3);
  if (!urgent.length) {
    return {
      text: 'No runs are near capacity right now. Plenty of seats if you hop in soon!',
    };
  }
  return {
    text: 'These runs are almost full — grab a seat quickly:',
    cards: urgent.map(formatRunCard).filter(Boolean),
  };
}

function describeBroadcastIdeas(runs = []) {
  const hotspots = buildHotspotSummary(runs).slice(0, 3);
  const preview = hotspots
    .map((spot, idx) => `${idx + 1}. ${spot.name} — ${spot.tip}`)
    .join('\n');
  return {
    text:
      'Broadcast game-plan:\n' +
      `${preview}\n` +
      'Hardcoded tip: rotate between a study core (Talley/Hunt) and residence-heavy zone (Wolf Ridge) to catch both lunch and dinner traffic.',
  };
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

const defaultGreeting = {
  from: 'ai',
  text: 'Hi! I am your campus-run scout. Ask about hotspots or drop points.',
};

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

function findMatchingRun(cleaned, availableRuns = []) {
  if (!cleaned || !Array.isArray(availableRuns)) return null;
  const normalized = cleaned.toLowerCase();
  return (
    availableRuns.find((run) => {
      const restaurant = `${run?.restaurant || ''}`.toLowerCase();
      const drop = `${run?.drop_point || ''}`.toLowerCase();
      return restaurant && normalized.includes(restaurant);
    }) ||
    availableRuns.find((run) => {
      const drop = `${run?.drop_point || ''}`.toLowerCase();
      return drop && normalized.includes(drop);
    }) ||
    null
  );
}

function craftAiResponse(message, availableRuns) {
  const cleaned = (message || '').toLowerCase();
  const hotspots = buildHotspotSummary(availableRuns);
  if (!cleaned.trim()) {
    return ensureMessagePayload({
      text: 'Try asking me about hotspots, seat alerts, or broadcast strategies — or use the quick buttons below.',
    });
  }
  const targetedRun = findMatchingRun(cleaned, availableRuns);
  if (targetedRun) {
    return ensureMessagePayload({
      text: `Here is the live scoop on ${targetedRun.restaurant} near ${targetedRun.drop_point}:`,
      cards: [formatRunCard(targetedRun)].filter(Boolean),
    });
  }
  if (
    cleaned.includes('insight') ||
    cleaned.includes('stat') ||
    cleaned.includes('summary')
  ) {
    return ensureMessagePayload(describeRunInsights(availableRuns));
  }
  if (cleaned.includes('seat') || cleaned.includes('full') || cleaned.includes('capacity')) {
    return ensureMessagePayload(describeLowSeatRuns(availableRuns));
  }
  if (cleaned.includes('hotspot') || cleaned.includes('where') || cleaned.includes('run')) {
    const previews = hotspots
      .slice(0, 3)
      .map((spot, idx) => `${idx + 1}. ${spot.name} — ${spot.tip}`)
      .join('\n');
    return ensureMessagePayload({
      text: `Here are some run hotspots right now:\n${previews}`,
    });
  }
  if (cleaned.includes('broadcast') || cleaned.includes('tip')) {
    return ensureMessagePayload(describeBroadcastIdeas(availableRuns));
  }
  if (cleaned.includes('thanks') || cleaned.includes('thank')) {
    return ensureMessagePayload({
      text: "Happy to help! Ping me anytime you're scouting for drop points.",
    });
  }
  if (cleaned.includes('suggest') || cleaned.includes('idea')) {
    return ensureMessagePayload({
      text: 'If you want to broadcast, target areas with study spaces (Hunt, Talley) or dorm clusters (Wolf Ridge).',
    });
  }
  return ensureMessagePayload({
    text: "I'm tuned for BrickyardBytes chatter. Want hotspots, seat alerts, or promo tips? I can also break down a specific run if you mention it by name.",
  });
}

export default function HotspotChat({ availableRuns }) {
  const [messages, setMessages] = useState([defaultGreeting]);
  const [input, setInput] = useState('');
  const [runsSnapshot, setRunsSnapshot] = useState(availableRuns || []);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (Array.isArray(parsed) && parsed.length) {
        setMessages(parsed);
      }
    } catch {
      // ignore storage read failures
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const trimmed = messages.slice(-20);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // ignore storage write failures
    }
  }, [messages]);

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
    const aiReply = ensureMessagePayload(action.buildMessage(runsSnapshot));
    setMessages((prev) => [
      ...prev,
      { from: 'user', text: `[Button] ${action.label}` },
      { from: 'ai', ...aiReply },
    ]);
  };

  const handleRunCardClick = (card) => {
    if (!card || !card.id || typeof window === 'undefined') return;
    window.open(`/runs/${card.id}`, '_blank', 'noopener');
  };

  const sendMessage = (evt) => {
    evt.preventDefault();
    const trimmed = input.trim();
    const aiReply = craftAiResponse(trimmed, runsSnapshot);
    setMessages((prev) => [
      ...prev,
      ...(trimmed ? [{ from: 'user', text: trimmed }] : []),
      { from: 'ai', ...aiReply },
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
            {Array.isArray(msg.cards) && msg.cards.length > 0 && (
              <div className="chatbot-message__cards">
                {msg.cards.map((card) => (
                  <button
                    key={`${card.id}-${card.title}`}
                    type="button"
                    className="chatbot-message-card"
                    onClick={() => handleRunCardClick(card)}
                  >
                    <span className="chatbot-message-card__title">{card.title}</span>
                    <span className="chatbot-message-card__subtitle">{card.subtitle}</span>
                    <span className="chatbot-message-card__detail">{card.detail}</span>
                    <span className="chatbot-message-card__cta">
                      View run ↗
                    </span>
                  </button>
                ))}
              </div>
            )}
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
