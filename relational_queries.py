import sqlite3
import time
import sys
import os

# Import the data generator ─────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from generate_data import generate_dataset


#  CREATEING FOUR DATABASE TABLES

CREATE_TABLES = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    name      TEXT,
    surname   TEXT,
    birthdate TEXT,
    country   TEXT
);

CREATE TABLE IF NOT EXISTS stations (
    station_id   INTEGER PRIMARY KEY,
    name         TEXT,
    city         TEXT,
    max_capacity INTEGER
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id          INTEGER PRIMARY KEY,
    user_id          INTEGER,
    start_station_id INTEGER,
    end_station_id   INTEGER,
    start_time       TEXT,
    end_time         TEXT,
    total_cost       REAL
);

CREATE TABLE IF NOT EXISTS events (
    event_id   INTEGER PRIMARY KEY,
    trip_id    INTEGER,
    timestamp  TEXT,
    event_type TEXT,
    value      TEXT
);

CREATE INDEX IF NOT EXISTS idx1 ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx2 ON trips(start_station_id);
CREATE INDEX IF NOT EXISTS idx3 ON trips(end_station_id);
CREATE INDEX IF NOT EXISTS idx4 ON events(trip_id);
CREATE INDEX IF NOT EXISTS idx5 ON events(event_type);
"""

# QUERY 1 - Get all trips with who made the trip and station names
Q1 = """
SELECT
    t.trip_id,
    u.name        AS user_name,
    u.surname     AS user_surname,
    u.country,
    ss.name       AS start_station_name,
    es.name       AS end_station_name,
    t.start_time,
    t.end_time,
    t.total_cost
FROM trips t
JOIN users    u  ON u.user_id     = t.user_id
JOIN stations ss ON ss.station_id = t.start_station_id
JOIN stations es ON es.station_id = t.end_station_id
ORDER BY t.trip_id;
"""

# QUERY 2- For every user: how many trips + average trip duration in minutes
Q2 = """
SELECT
    u.user_id,
    u.name,
    u.surname,
    COUNT(t.trip_id) AS num_trips,
    ROUND(
        AVG( (JULIANDAY(t.end_time) - JULIANDAY(t.start_time)) * 1440 ),
    2) AS avg_duration_min
FROM users u
LEFT JOIN trips t ON t.user_id = u.user_id
GROUP BY u.user_id
ORDER BY u.user_id;
"""
# QUERY 3 - For every station: how many trips start and end there
Q3 = """
SELECT
    s.station_id,
    s.name,
    s.city,
    COUNT(DISTINCT ts.trip_id) AS trips_starting,
    COUNT(DISTINCT te.trip_id) AS trips_ending
FROM stations s
LEFT JOIN trips ts ON ts.start_station_id = s.station_id
LEFT JOIN trips te ON te.end_station_id   = s.station_id
GROUP BY s.station_id
ORDER BY s.station_id;
"""

# QUERY 4 - Find all trips that had at least one ERROR event
Q4 = """
SELECT DISTINCT
    t.trip_id,
    t.user_id,
    t.start_time,
    t.end_time,
    t.total_cost
FROM trips t
JOIN events e ON e.trip_id = t.trip_id
WHERE e.event_type = 'ERROR'
ORDER BY t.trip_id;
"""
#CREATING FUNCTIONS
def open_database():
    """Open an in-memory SQLite database and return the connection."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA cache_size   = -64000;")
    return conn


def create_tables(conn):
    """Create all 4 tables in the database."""
    conn.executescript(CREATE_TABLES)
    conn.commit()


def insert_data(conn, data):
    """Insert all generated data into the database tables."""
    cur = conn.cursor()

    # Insert users
    cur.executemany(
        "INSERT OR IGNORE INTO users VALUES (:user_id, :name, :surname, :birthdate, :country)",
        data["users"]
    )

    # Insert stations
    cur.executemany(
        "INSERT OR IGNORE INTO stations VALUES (:station_id, :name, :city, :max_capacity)",
        data["stations"]
    )

    # Insert trips
    cur.executemany(
        "INSERT OR IGNORE INTO trips VALUES (:trip_id, :user_id, :start_station_id, :end_station_id, :start_time, :end_time, :total_cost)",
        data["trips"]
    )

    # Insert events
    cur.executemany(
        "INSERT OR IGNORE INTO events VALUES (:event_id, :trip_id, :timestamp, :event_type, :value)",
        data["events"]
    )

    conn.commit()


def run_query(conn, sql, name):
    """Run one SQL query, measure time, print result."""
    start_time = time.perf_counter()
    rows       = conn.execute(sql).fetchall()
    seconds    = time.perf_counter() - start_time
    print(f"  [{name}]  rows={len(rows):>7,}  time={seconds:.4f}s")
    return seconds


# BENCHMARK FUNCTION

def benchmark(data, label=""):
    """
    Run all 4 queries on the given dataset.
    Returns a dictionary of timing results.
    """
    # Open database and load data
    conn = open_database()
    create_tables(conn)
    insert_data(conn, data)

    # Print header
    print(f"\n{'─' * 55}")
    print(f"  Relational Benchmark  {label}")
    print(f"{'─' * 55}")

    # Run each query and collect timings
    results = {}
    results["Q1"] = run_query(conn, Q1, "Q1")
    results["Q2"] = run_query(conn, Q2, "Q2")
    results["Q3"] = run_query(conn, Q3, "Q3")
    results["Q4"] = run_query(conn, Q4, "Q4")

    conn.close()
    return results

if __name__ == "__main__":

    # These are the 4 dataset sizes we test
    configs = [
        (1_000,   10_000,  0),    # 1k users, 10k trips, 0 events per trip
        (1_000,   10_000,  2),    # 1k users, 10k trips, 2 events per trip
        (10_000,  50_000,  5),    # 10k users, 50k trips, 5 events per trip
        (50_000,  100_000, 10),   # 50k users, 100k trips, 10 events per trip
    ]

    all_results = []

    for n_users, n_trips, n_events in configs:

        # Generate fake data for this config
        data = generate_dataset(n_users, n_trips, n_events)

        # Run the benchmark
        label = f"users={n_users}  trips={n_trips}  events/trip={n_events}"
        res   = benchmark(data, label)

        all_results.append((n_users, n_trips, n_events, res))

    # Print final summary table
    print("\n\n=== Final Summary (seconds) ===")
    print(f"{'Config':<38}  {'Q1':>8}  {'Q2':>8}  {'Q3':>8}  {'Q4':>8}")
    print("─" * 75)

    for n_users, n_trips, n_events, res in all_results:
        config_label = f"u={n_users} t={n_trips} e={n_events}"
        print(
            f"{config_label:<38}  "
            f"{res['Q1']:>8.4f}  "
            f"{res['Q2']:>8.4f}  "
            f"{res['Q3']:>8.4f}  "
            f"{res['Q4']:>8.4f}"
        )
