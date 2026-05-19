import logging


import os
import sys
import time
import sqlite3

# ── Add current folder to path so generate_data can be found ─────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_data import generate_dataset

# ── Suppress warnings on Windows ─────────────────────────────────────────────
os.environ["PYTHONWARNINGS"]            = "ignore"
os.environ["PYSPARK_PYTHON"]           = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"]    = sys.executable

#SQLite Q2 (for comparison baseline)

SQL_Q2 = """
SELECT
    u.user_id,
    u.name,
    u.surname,
    COUNT(t.trip_id) AS num_trips,
    ROUND(
        AVG((JULIANDAY(t.end_time) - JULIANDAY(t.start_time)) * 1440),
    2) AS avg_duration_min
FROM users u
LEFT JOIN trips t ON t.user_id = u.user_id
GROUP BY u.user_id
ORDER BY u.user_id;
"""

def run_sqlite_q2(data):
    """Run Q2 in SQLite and return timing."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE users(user_id INTEGER PRIMARY KEY, name TEXT,
                           surname TEXT, birthdate TEXT, country TEXT);
        CREATE TABLE stations(station_id INTEGER PRIMARY KEY, name TEXT,
                              city TEXT, max_capacity INTEGER);
        CREATE TABLE trips(trip_id INTEGER PRIMARY KEY, user_id INTEGER,
                           start_station_id INTEGER, end_station_id INTEGER,
                           start_time TEXT, end_time TEXT, total_cost REAL);
        CREATE TABLE events(event_id INTEGER PRIMARY KEY, trip_id INTEGER,
                            timestamp TEXT, event_type TEXT, value TEXT);
        CREATE INDEX idx1 ON trips(user_id);
    """)
    cur = conn.cursor()
    cur.executemany("INSERT INTO users VALUES(:user_id,:name,:surname,:birthdate,:country)", data["users"])
    cur.executemany("INSERT INTO stations VALUES(:station_id,:name,:city,:max_capacity)", data["stations"])
    cur.executemany("INSERT INTO trips VALUES(:trip_id,:user_id,:start_station_id,:end_station_id,:start_time,:end_time,:total_cost)", data["trips"])
    cur.executemany("INSERT INTO events VALUES(:event_id,:trip_id,:timestamp,:event_type,:value)", data["events"])
    conn.commit()

    t0   = time.perf_counter()
    rows = conn.execute(SQL_Q2).fetchall()
    sec  = round(time.perf_counter() - t0, 4)
    conn.close()
    return rows, sec


# PART 2 — Spark Q2

def run_spark_q2(data):
    
    """Run Q2 using PySpark DataFrames."""
    
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F

        # ── Start Spark session 
        spark = (
            SparkSession.builder
            .appName("ADM_Q2")
            .master("local[*]")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.driver.memory", "1g")
            .config("spark.ui.enabled", "false")
            .config("spark.ui.showConsoleProgress", "false")
            .getOrCreate()
        )
        logging.getLogger("py4j").setLevel(logging.ERROR)
        spark.sparkContext.setLogLevel("ERROR")

        # Build DataFrames from in-memory data
        trip_rows = [
            (t["trip_id"], t["user_id"], t["start_time"], t["end_time"])
            for t in data["trips"]
        ]
        user_rows = [
            (u["user_id"], u["name"], u["surname"])
            for u in data["users"]
        ]

        trips_df = spark.createDataFrame(
            trip_rows, ["trip_id", "user_id", "start_time", "end_time"]
        )
        users_df = spark.createDataFrame(
            user_rows, ["user_id", "name", "surname"]
        )

        # Calculate duration in minutes
        trips_df = (
            trips_df
            .withColumn("start_ts", F.to_timestamp("start_time", "yyyy-MM-dd HH:mm:ss"))
            .withColumn("end_ts",   F.to_timestamp("end_time",   "yyyy-MM-dd HH:mm:ss"))
            .withColumn("duration_min",
                (F.unix_timestamp("end_ts") - F.unix_timestamp("start_ts")) / 60.0)
        )

        # Group by user and calculate stats
        t0 = time.perf_counter()

        result = (
            trips_df
            .groupBy("user_id")
            .agg(
                F.count("trip_id").alias("num_trips"),
                F.round(F.avg("duration_min"), 2).alias("avg_duration_min")
            )
            .join(users_df, on="user_id", how="right")
            .fillna({"num_trips": 0, "avg_duration_min": 0.0})
            .orderBy("user_id")
        )

        # Force evaluation
        rows = result.collect()
        sec  = round(time.perf_counter() - t0, 4)

        spark.stop()
        return rows, sec

    except Exception as e:
        return None, str(e)


# =============================================================================
# MAIN — Run benchmark for all dataset sizes
# =============================================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("  SPARK vs SQLite — Query 2 Benchmark")
    print("  Q2: Users with Trip Count and Average Duration")
    print("=" * 65)

    # Dataset sizes to test
    configs = [
        (1_000,  10_000,  0),
        (1_000,  10_000,  2),
        (10_000, 50_000,  5),
        (50_000, 100_000, 10),
    ]

    all_results = []

    for n_users, n_trips, n_events in configs:

        label = f"users={n_users:,}  trips={n_trips:,}  events/trip={n_events}"
        print(f"\n{'─'*65}")
        print(f"  Config: {label}")
        print(f"{'─'*65}")

        # Generate data
        print("  Generating data...", end="", flush=True)
        data = generate_dataset(n_users, n_trips, n_events)
        print(" done.")

        # ── SQLite Q2 ──────────────────────────────────────────────────────
        print("  Running SQLite Q2...", end="", flush=True)
        sql_rows, sql_sec = run_sqlite_q2(data)
        print(f" done.  rows={len(sql_rows):,}  time={sql_sec}s")

        # Print first 3 rows as sample
        print("  Sample SQLite results:")
        for r in sql_rows[:3]:
            print(f"    user_id={r[0]}  name={r[1]} {r[2]}  trips={r[3]}  avg_min={r[4]}")

        # ── Spark Q2 ───────────────────────────────────────────────────────
        print("  Running Spark Q2 (this takes 30-60 seconds)...", flush=True)
        spark_rows, spark_sec = run_spark_q2(data)

        if spark_rows is None:
            print(f"  Spark SKIPPED — {spark_sec}")
            print("  Fix: Download winutils.exe and set HADOOP_HOME=C:\\hadoop")
            spark_sec = "SKIP"
        else:
            print(f"  Spark done.  rows={len(spark_rows):,}  time={spark_sec}s")
            print("  Sample Spark results:")
            for r in spark_rows[:3]:
                print(f"    user_id={r['user_id']}  trips={r['num_trips']}  avg_min={r['avg_duration_min']}")

        all_results.append((n_users, n_trips, n_events, sql_sec, spark_sec))

    # ── Final Summary Table ────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  FINAL SUMMARY — SQLite vs Spark Q2 (seconds)")
    print("=" * 65)
    print(f"  {'Config':<38}  {'SQLite':>8}  {'Spark':>8}")
    print(f"  {'─'*38}  {'─'*8}  {'─'*8}")

    for n_users, n_trips, n_events, sql_sec, spark_sec in all_results:
        cfg = f"u={n_users:,} t={n_trips:,} e={n_events}"
        spark_str = f"{spark_sec}s" if spark_sec != "SKIP" else "SKIP"
        print(f"  {cfg:<38}  {sql_sec:>7}s  {spark_str:>8}")

    print()
    print("  Conclusion:")
    print("  SQLite is faster for small datasets because Spark has")
    print("  JVM startup overhead of 30-60 seconds regardless of data size.")
    print("  Spark wins only when data exceeds single machine memory.")
    print("=" * 65)