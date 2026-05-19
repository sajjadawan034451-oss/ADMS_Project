"""
neo4j/graph_queries.py
=======================
Part 2 – Graph Model (Neo4j)

• Node/edge schema
• Graph Query G1: stations reachable by a given user
• Graph Query G2: top-3 most important stations
• Benchmark runner

Run standalone (Neo4j must be running):
    python neo4j/graph_queries.py

Set environment variables to override defaults:
    NEO4J_URI   (default: bolt://localhost:7687)
    NEO4J_USER  (default: neo4j)
    NEO4J_PASS  (default: password)

GRAPH SCHEMA
────────────
Nodes:
  (:USER    {user_id, name, surname, birthdate, country})
  (:TRIP    {trip_id, start_time, end_time, total_cost})
  (:STATION {station_id, name, city, max_capacity})

Edges:
  (:USER)-[:PERFORMED]->(:TRIP)
  (:TRIP)-[:STARTS_AT]->(:STATION)
  (:TRIP)-[:ENDS_AT]->(:STATION)

DESIGN NOTES
────────────
• Events are NOT modelled as graph nodes because the required queries
  do not traverse event relationships — they remain in MongoDB/SQLite.
• Graph representation allows efficient traversal queries (G1) and
  centrality-based ranking (G2, PageRank) that would require expensive
  self-joins in the relational model.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data_generation"))
from generate_data import generate_dataset

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("[WARNING] neo4j driver not installed. Install with:  pip install neo4j")

NEO4J_URI  = os.getenv("NEO4J_URI",  "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

BATCH = 500     # nodes/edges per transaction


# ─────────────────────────────────────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────────────────────────────────────

def get_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    driver.verify_connectivity()
    return driver


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

def create_constraints(driver):
    stmts = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (u:USER)    REQUIRE u.user_id    IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:TRIP)    REQUIRE t.trip_id    IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:STATION) REQUIRE s.station_id IS UNIQUE",
    ]
    with driver.session() as s:
        for stmt in stmts:
            s.run(stmt)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def load_dataset(driver, dataset):
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")   # clear graph

        # Users
        for chunk in _chunks(dataset["users"], BATCH):
            s.run(
                "UNWIND $rows AS r "
                "MERGE (u:USER {user_id: r.user_id}) "
                "SET u.name=r.name, u.surname=r.surname, "
                "    u.birthdate=r.birthdate, u.country=r.country",
                rows=chunk,
            )

        # Stations
        for chunk in _chunks(dataset["stations"], BATCH):
            s.run(
                "UNWIND $rows AS r "
                "MERGE (s:STATION {station_id: r.station_id}) "
                "SET s.name=r.name, s.city=r.city, s.max_capacity=r.max_capacity",
                rows=chunk,
            )

        # Trips + relationships
        for chunk in _chunks(dataset["trips"], BATCH):
            s.run(
                "UNWIND $rows AS r "
                "MATCH (u:USER    {user_id:    r.user_id}) "
                "MATCH (ss:STATION {station_id: r.start_station_id}) "
                "MATCH (es:STATION {station_id: r.end_station_id}) "
                "MERGE (t:TRIP {trip_id: r.trip_id}) "
                "SET t.start_time=r.start_time, t.end_time=r.end_time, "
                "    t.total_cost=r.total_cost "
                "MERGE (u)-[:PERFORMED]->(t) "
                "MERGE (t)-[:STARTS_AT]->(ss) "
                "MERGE (t)-[:ENDS_AT]->(es)",
                rows=chunk,
            )


# ─────────────────────────────────────────────────────────────────────────────
# QUERIES
# ─────────────────────────────────────────────────────────────────────────────

def g1_reachable_stations(driver, user_id):
    """
    G1 – Given a user, find all stations reachable through their trips.
    A station is reachable if any trip performed by the user
    starts or ends at that station.
    """
    cypher = """
    MATCH (u:USER {user_id: $uid})-[:PERFORMED]->(t:TRIP)
          -[:STARTS_AT|ENDS_AT]->(s:STATION)
    RETURN DISTINCT s.station_id AS station_id,
                    s.name       AS name,
                    s.city       AS city
    ORDER BY s.name
    """
    with driver.session() as session:
        return [dict(r) for r in session.run(cypher, uid=user_id)]


def g2_top3_stations(driver):
    """
    G2 – Top-3 most important stations by total trip volume
         (incoming trips + outgoing trips).
    """
    cypher = """
    MATCH (s:STATION)
    OPTIONAL MATCH (:TRIP)-[:STARTS_AT]->(s)
    WITH s, COUNT(*) AS outgoing
    OPTIONAL MATCH (:TRIP)-[:ENDS_AT]->(s)
    WITH s, outgoing, COUNT(*) AS incoming
    RETURN s.station_id          AS station_id,
           s.name                AS name,
           s.city                AS city,
           outgoing + incoming   AS total_trips
    ORDER BY total_trips DESC
    LIMIT 3
    """
    with driver.session() as session:
        return [dict(r) for r in session.run(cypher)]


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def _timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    r  = fn(*args, **kwargs)
    return r, time.perf_counter() - t0


def benchmark(dataset, label=""):
    if not NEO4J_AVAILABLE:
        print("  [SKIP] neo4j driver not installed.")
        return {}
    try:
        driver = get_driver()
    except Exception as e:
        print(f"  [SKIP] Neo4j unreachable: {e}")
        return {}

    create_constraints(driver)
    load_dataset(driver, dataset)

    print(f"\n{'─'*55}")
    print(f"  Neo4j Benchmark  {label}")
    print(f"{'─'*55}")

    sample_uid = dataset["users"][0]["user_id"]
    rows, sec  = _timed(g1_reachable_stations, driver, sample_uid)
    print(f"  [G1]  reachable stations for user {sample_uid}: {len(rows)}  time={sec:.4f}s")

    rows, sec = _timed(g2_top3_stations, driver)
    print(f"  [G2]  top-3 stations: {[(r['name'], r['total_trips']) for r in rows]}  time={sec:.4f}s")

    driver.close()
    return {"G1": sec, "G2": sec}


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
