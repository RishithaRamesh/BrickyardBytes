import { useAuth } from '../hooks/useAuth';


export default function RunCard({ run, onJoin, joinedRuns, onCheckLoad, loadInsight, loadLoading }) {
  const { user } = useAuth();
  const hasJoined = joinedRuns.some((r) => r.id === run.id);
  const isOwner = run.runner_username === user?.username;

  return (
    <div className="run-card">
      <div className="run-card-header">
        <h3>{run.restaurant}</h3>
        <span className="run-card-runner">by {run.runner_username}</span>
      </div>

      <div className="run-card-body">
        <p><strong>ETA:</strong> {run.eta}</p>
        <p><strong>Available Seats:</strong> {run.seats_remaining}</p>
        {run.description && (
          <p className="run-card-description">{run.description}</p>
        )}
      </div>

      <div className="run-card-footer">
        {onCheckLoad && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6, marginBottom: 8, width: '100%' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCheckLoad}
              disabled={loadLoading}
            >
              {loadLoading ? "Analyzing..." : "Check load"}
            </button>
            {loadInsight?.text && (
              <p
                style={{ margin: 0 }}
                className={loadInsight.error ? "form-error" : ""}
              >
                {loadInsight.text}
              </p>
            )}
          </div>
        )}
        <button
          className="btn btn-primary"
          onClick={() => onJoin(run)}
          disabled={run.seats_remaining <= 0 || hasJoined || isOwner}
        >
          {isOwner
            ? "Your Run"
            : hasJoined
            ? "Joined"
            : run.seats_remaining > 0
            ? "Join Run"
            : "Full"}
        </button>
      </div>
    </div>
  );
}
