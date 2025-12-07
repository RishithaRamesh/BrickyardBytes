import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import * as authServices from '../services/authServices';

export default function Profile() {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

    if (user) {
      loadProfileData();
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
