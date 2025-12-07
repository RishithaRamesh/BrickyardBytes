"""
Aggregate historical food run + order data and forecast peak demand hours.

This CLI leverages the shared analytics helpers used by the API so you can run
forecasts on demand or export them as JSON for downstream experimentation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlmodel import Session, create_engine

from backend.app.analytics import generate_peak_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate foodrun/order activity and forecast peak hours."
    )
    parser.add_argument(
        "--db",
        default="backend/dev.db",
        help="Path to the SQLite database (default: backend/dev.db)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the aggregated data + forecast as JSON.",
    )
    return parser.parse_args()


def summarize_to_console(payload) -> None:
    series = payload["hourly_timeseries"]
    profile = payload["hourly_profile"]
    peaks = payload["peak_forecast"]
    total_runs = sum(entry["run_count"] for entry in series)
    total_orders = sum(entry["order_count"] for entry in series)
    print(
        f"Observed {len(series)} hourly buckets | runs={total_runs} orders={total_orders}"
    )

    top_hours = sorted(profile, key=lambda e: e["demand_score"], reverse=True)[:5]
    print("\nTop hours by demand score:")
    for entry in top_hours:
        hour = entry["hour"]
        score = entry["demand_score"]
        avg_orders = entry["avg_orders_per_day"]
        avg_runs = entry["avg_runs_per_day"]
        print(
            f"  Hour {hour:02d}: score={score:.3f} | avg_orders={avg_orders:.2f} | avg_runs={avg_runs:.2f}"
        )

    print("\nForecast peak windows (sorted):")
    for entry in peaks:
        hour = entry["hour"]
        score = entry["demand_score"]
        util = entry["utilization_ratio"]
        print(f"  Hour {hour:02d} → demand_score={score:.3f} | utilization={util:.2f}")


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    with Session(engine) as session:
        payload = generate_peak_payload(session)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2))
        print(f"Wrote aggregated data + forecast → {args.output}")

    summarize_to_console(payload)


if __name__ == "__main__":
    main()
