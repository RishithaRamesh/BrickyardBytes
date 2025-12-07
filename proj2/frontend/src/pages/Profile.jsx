import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import * as authServices from '../services/authServices';
import * as analyticsService from '../services/analyticsService';

export default function Profile() {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [peakHours, setPeakHours] = useState([]);
  const [peakLoading, setPeakLoading] = useState(true);
  const [peakError, setPeakError] = useState(null);
  const orderedPeakHours = peakHours.length
    ? [...peakHours].sort((a, b) => {
        if (typeof a.hour !== 'number') return 1;
        if (typeof b.hour !== 'number') return -1;
        return a.hour - b.hour;
      })
    : [];
  const featuredPeak =
    orderedPeakHours.find((entry) => entry.hour === 17) || orderedPeakHours[0] || null;

  useEffect(() => {
    async function loadProfileData() {
      try {
        const points = await authServices.getPoints();
        setProfileData({ points });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    async function loadPeakWindows() {
      try {
        const data = await analyticsService.getPeakForecast();
        setPeakHours(data?.peak_forecast || []);
      } catch (err) {
        setPeakError(err.message);
      } finally {
        setPeakLoading(false);
      }
    }

    if (user) {
      loadProfileData();
      loadPeakWindows();
    }
  }, [user]);

  function formatPeakWindow(hour) {
    if (typeof hour !== 'number') return '—';
    const start = String(hour).padStart(2, '0');
    const endHour = (hour + 1) % 24;
    const end = String(endHour).padStart(2, '0');
    return `${start}:00 - ${end}:00`;
  }

  if (!user) return <p className="p-4">No user logged in.</p>;
  if (loading) return <p className="p-4">Loading...</p>;
  if (error) return <p className="p-4 text-red-500">Error: {error}</p>;

  return (
  <div className="profile-container">
    {featuredPeak && (
      <div className="peak-banner" role="status">
        <span className="peak-banner__label">Peak bonus windows</span>
        <p className="peak-banner__message">
          Bonus active from {formatPeakWindow(featuredPeak.hour)} — run now to earn extra points.
        </p>
      </div>
    )}
    <div className="profile-section">
      <h2>Profile Information</h2>
      <p><strong>Username:</strong> {user.username}</p>
    </div>

    <div className="profile-points">
      <h2>Rewards Points</h2>
      <p><strong>Current Points:</strong> {profileData?.points?.points || 0}</p>
      <p><strong>Points Value:</strong> ${profileData?.points?.points_value || 0}</p>
      <p className="text-sm">
        Earn 1 point for every $10 in orders you deliver. 
        Redeem 10 points for $5 credit!
      </p>
    </div>

    <div className="profile-rewards">
      <div className="flex justify-between items-center">
        <h2>Peak Hour Bonuses</h2>
        <span className="text-sm text-gray-500">Updates hourly</span>
      </div>
      {peakLoading ? (
        <p>Loading peak windows…</p>
      ) : peakError ? (
        <p className="text-red-500 text-sm">Unable to load forecast: {peakError}</p>
      ) : !featuredPeak ? (
        <p className="text-sm">No peak windows yet. Check back soon for bonus opportunities.</p>
      ) : (
        <>
          <p className="text-sm text-gray-600 mt-2">
            Bonus window currently active from {formatPeakWindow(featuredPeak.hour)}.
            </p>
          <div className="peak-highlight mt-3">
            <span className="font-semibold">{formatPeakWindow(featuredPeak.hour)}</span>
            <span className="text-sm text-green-700">Peak-hour bonus available</span>
          </div>
        </>
      )}
    </div>

    <div className="profile-link-card">
      <div className="flex justify-between items-center">
        <h2>Your Food Runs</h2>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/your-runs">Manage</Link>
          <Link to="/history">History</Link>
        </div>
      </div>
      <p>Manage your broadcasts and see your run history.</p>
    </div>
  </div>

  );
}
