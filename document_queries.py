"""
mongodb/document_queries.py
============================
Part 1 – Document Model (MongoDB + PyMongo)

• Document schema (embedded design)
• Four required queries (Q1–Q4)
• Benchmark runner

Run standalone (MongoDB must be running on localhost:27017):
    python mongodb/document_queries.py

DOCUMENT DESIGN RATIONALE
──────────────────────────
Collection: trips   ← primary collection

Each trip document EMBEDS:
  • user snapshot   (name, surname, birthdate, country)
  • start_station snapshot (name, city)
  • end_station   snapshot (name, city)
  • events array  [{event_id, timestamp, event_type, value}, ...]

WHY EMBEDDING?
  1. Q1 and Q4 need zero $lookup — data already in one document.
  2. Events are always accessed alongside their trip; embedding avoids a
     separate round-trip to a standalone events collection.
  3. Average document size stays well below MongoDB's 16 MB limit
     (even at 10 events/trip each doc is < 5 KB).

TRADE-OFFS vs REFERENCING
  + Faster reads for the four required queries.
  − If a user's name changes, all embedded snapshots must be updated.
  − Cannot easily query events independently (e.g. "all ERROR events globally")
    without an index on events.event_type.

Separate collections (users, stations) are kept for normalised lookups
(e.g. listing all stations independently of trips).
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data_generation"))
from generate_data import generate_dataset

try:
    from pymongo import MongoClient, ASCENDING
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[WARNING] pymongo not installed. Install with:  pip install pymongo")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = "adm_mobility"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")        # raises if not reachable
    return client[DB_NAME]


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset(db, dataset):
    user_idx    = {u["user_id"]:    u for u in dataset["users"]}
    station_idx = {s["station_id"]: s for s in dataset["stations"]}

    # Group events by trip
    event_idx = {}
    for e in dataset["events"]:
        event_idx.setdefault(e["trip_id"], []).append({
            "event_id":   e["event_id"],
            "timestamp":  e["timestamp"],
            "event_type": e["event_type"],
            "value":      e["value"],
        })

    # ── users ──
    db.users.drop()
    db.users.insert_many([
        {"_id": u["user_id"],
         "name": u["name"], "surname": u["surname"],
         "birthdate": u["birthdate"], "country": u["country"]}
        for u in dataset["users"]
    ])

    # ── stations ──
    db.stations.drop()
    db.stations.insert_many([
        {"_id": s["station_id"],
         "name": s["name"], "city": s["city"], "max_capacity": s["max_capacity"]}
        for s in dataset["stations"]
    ])

    # ── trips (embedded design) ──
    db.trips.drop()
    trip_docs = []
    for t in dataset["trips"]:
        u  = user_idx[t["user_id"]]
        ss = station_idx[t["start_station_id"]]
        es = station_idx[t["end_station_id"]]
        trip_docs.append({
            "_id": t["trip_id"],
            "user": {
                "user_id":  u["user_id"],
                "name":     u["name"],
                "surname":  u["surname"],
                "birthdate": u["birthdate"],
                "country":  u["country"],
            },
            "start_station": {
                "station_id": ss["station_id"],
                "name":       ss["name"],
                "city":       ss["city"],
            },
            "end_station": {
                "station_id": es["station_id"],
                "name":       es["name"],
                "city":       es["city"],
            },
            "start_time": t["start_time"],
            "end_time":   t["end_time"],
            "total_cost": t["total_cost"],
            "events":     event_idx.get(t["trip_id"], []),
        })
    db.trips.insert_many(trip_docs, ordered=False)

    # Indexes
    db.trips.create_index([("user.user_id",          ASCENDING)])
    db.trips.create_index([("start_station.station_id", ASCENDING)])
    db.trips.create_index([("end_station.station_id",   ASCENDING)])
    db.trips.create_index([("events.event_type",         ASCENDING)])


# ─────────────────────────────────────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────────────────────────────────────

def q1_all_trips(db):
    """Q1 – All trips with user info + start/end station names."""
    return list(db.trips.find(
        {},
        {"user": 1,
         "start_station.name": 1,
         "end_station.name":   1,
         "start_time": 1, "end_time": 1, "total_cost": 1}
    ))


def q2_users_stats(db):
    """Q2 – Users with number of trips + average duration (minutes)."""
    pipeline = [
        # Parse ISO strings into dates for arithmetic
        {"$addFields": {
            "start_dt": {"$dateFromString": {"dateString": "$start_time",
                                              "format": "%Y-%m-%d %H:%M:%S"}},
            "end_dt":   {"$dateFromString": {"dateString": "$end_time",
                                              "format": "%Y-%m-%d %H:%M:%S"}},
        }},
        {"$addFields": {
            "duration_min": {
                "$divide": [{"$subtract": ["$end_dt", "$start_dt"]}, 60000]
            }
        }},
        # Group per user
        {"$group": {
            "_id":              "$user.user_id",
            "name":             {"$first": "$user.name"},
            "surname":          {"$first": "$user.surname"},
            "country":          {"$first": "$user.country"},
            "num_trips":        {"$sum": 1},
            "avg_duration_min": {"$avg": "$duration_min"},
        }},
        # Include users with 0 trips via $lookup on users collection
        {"$sort": {"_id": 1}},
    ]
    return list(db.trips.aggregate(pipeline))


def q3_station_stats(db):
    """Q3 – Stations with trips starting + ending there."""
    starts = list(db.trips.aggregate([
        {"$group": {"_id": "$start_station.station_id",
                    "name": {"$first": "$start_station.name"},
                    "city": {"$first": "$start_station.city"},
                    "trips_starting": {"$sum": 1}}}
    ]))
    ends = {r["_id"]: r["trips_ending"]
            for r in db.trips.aggregate([
                {"$group": {"_id": "$end_station.station_id",
                            "trips_ending": {"$sum": 1}}}
            ])}
    return [
        {**s, "trips_ending": ends.get(s["_id"], 0)}
        for s in starts
    ]


def q4_error_trips(db):
    """Q4 – Trips containing at least one ERROR event."""
    return list(db.trips.find(
        {"events": {"$elemMatch": {"event_type": "ERROR"}}},
        {"user.user_id": 1, "start_time": 1, "end_time": 1, "total_cost": 1}
    ))


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def _timed(fn, *args):
    t0 = time.perf_counter()
    r  = fn(*args)
    return r, time.perf_counter() - t0


def benchmark(dataset, label=""):
    if not MONGO_AVAILABLE:
        print("  [SKIP] pymongo not installed.")
        return {}
    try:
        db = get_db()
    except Exception as e:
        print(f"  [SKIP] MongoDB unreachable: {e}")
        return {}

    load_dataset(db, dataset)
    print(f"\n{'─'*55}")
    print(f"  MongoDB Benchmark  {label}")
    print(f"{'─'*55}")
    results = {}
    for name, fn in [("Q1", q1_all_trips), ("Q2", q2_users_stats),
                     ("Q3", q3_station_stats), ("Q4", q4_error_trips)]:
        rows, sec = _timed(fn, db)
        results[name] = sec
        print(f"  [{name}]  rows={len(rows):>7,}  time={sec:.4f}s")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    configs = [
        (1_000,  10_000,  0),
        (1_000,  10_000,  2),
        (10_000, 50_000,  5),
        (50_000, 100_000, 10),
    ]
    for n_users, n_trips, n_events in configs:
        ds = generate_dataset(n_users, n_trips, n_events)
        benchmark(ds, f"users={n_users}  trips={n_trips}  events/trip={n_events}")
