import React, { useEffect, useState } from 'react';
import * as analyticsService from '../services/analyticsService';

function formatWindow(hour) {
  if (typeof hour !== 'number') return null;
  const start = String(hour).padStart(2, '0');
  const end = String((hour + 1) % 24).padStart(2, '0');
  return `${start}:00 - ${end}:00`;
}

export default function PeakBanner({ offset = 0 }) {
  const [peakHours, setPeakHours] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      let auth = null;
      try {
        auth = JSON.parse(localStorage.getItem('auth'));
      } catch {
        auth = null;
      }
      if (!auth?.token) {
        setPeakHours([]);
        setError('');
        return;
      }
      try {
        const data = await analyticsService.getPeakForecast();
        setPeakHours(data?.peak_forecast || []);
        setError('');
      } catch (err) {
        setError(err.message || 'Unable to load peak forecast');
      }
    }
    load();
    const interval = setInterval(load, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const ordered = peakHours.length
    ? [...peakHours].sort((a, b) => {
        if (typeof a.hour !== 'number') return 1;
        if (typeof b.hour !== 'number') return -1;
        return a.hour - b.hour;
      })
    : [];

  const featured = ordered.find((entry) => entry.hour === 17) || ordered[0] || null;
  if (!featured || error) return null;
  const windowText = formatWindow(featured.hour);
  if (!windowText) return null;

  return (
    <div className="peak-banner" role="status" style={{ marginTop: offset }}>
      <span className="peak-banner__label">Peak bonus window</span>
      <p className="peak-banner__message">
        Bonus active from {windowText}. Run now to earn extra points.
      </p>
    </div>
  );
}
