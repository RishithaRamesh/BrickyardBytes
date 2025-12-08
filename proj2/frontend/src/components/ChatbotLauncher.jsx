import React, { useState } from 'react';
import HotspotChat from './HotspotChat';

export default function ChatbotLauncher() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && (
        <div className="chatbot-panel" role="dialog" aria-label="Campus hotspot chatbot">
          <div className="chatbot-panel__header">
            <div>
              <p>Planning a run?</p>
              <h3>Hotspot Assistant</h3>
            </div>
            <button
              type="button"
              className="chatbot-panel__close"
              onClick={() => setOpen(false)}
              aria-label="Close chatbot"
            >
              ×
            </button>
          </div>
          <HotspotChat />
        </div>
      )}

      <button
        type="button"
        className="chatbot-launcher"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-label={open ? 'Close chatbot' : 'Open chatbot'}
      >
        {open ? '×' : '🤖'}
      </button>
    </>
  );
}
