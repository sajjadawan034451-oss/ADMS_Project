"""
run_all_benchmarks.py
=====================
Run this ONE file to get ALL benchmark results for the project.

Command:
    python run_all_benchmarks.py

This will run:
    1. SQLite  - Q1, Q2, Q3, Q4  (all 12 dataset sizes)
    2. MongoDB - Q1, Q2, Q3, Q4  (all 12 dataset sizes)
    3. Neo4j   - G1, G2           (all 12 dataset sizes)
    4. Spark   - Q2 DataFrame     (all 12 dataset sizes)

Results are printed on screen AND saved to:
    benchmark_results.txt  (copy this into your Word document)
"""

import sys
import os
import time
import random
import sqlite3
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATOR  (no external libraries needed)
# ─────────────────────────────────────────────────────────────────────────────

random.seed(42)

CITIES  = ['Milan','Rome','Naples','Turin','Palermo','Genoa',
           'Bologna','Florence','Bari','Catania','Venice','Verona']
FNAMES  = ['Luca','Marco','Sara','Giulia','Anna','Paolo',
           'Maria','Luigi','Elena','Roberto','Chiara','Andrea']
LNAMES  = ['Rossi','Bianchi','Ferrari','Esposito','Romano',
           'Colombo','Ricci','Marino','Greco','Bruno']
COUNTRIES = ['Italy','France','Germany','Spain','UK','Poland']
ETYPES  = ['GPS','ERROR','BATTERY','DELAY']

def _rdate():
    return (datetime(1960,1,1)+timedelta(days=random.randint(0,16000))).strftime('%Y-%m-%d')

def _eval(et):
    if et=='GPS':     return f'{round(random.uniform(36,47),4)},{round(random.uniform(6,18),4)}'
    if et=='ERROR':   return random.choice(['E001','E002','E003','E004','E005'])
    if et=='BATTERY': return str(random.randint(0,100))
    return str(random.randint(1,120))

def generate(n_users, n_trips, n_ev, n_st=50):
    users = [{'user_id':i,'name':random.choice(FNAMES),'surname':random.choice(LNAMES),
               'birthdate':_rdate(),'country':random.choice(COUNTRIES)}
              for i in range(1, n_users+1)]
    stations = [{'station_id':i,'name':f'{random.choice(CITIES)} St {i}',
                  'city':random.choice(CITIES),'max_capacity':random.randint(5,30)}
                 for i in range(1, n_st+1)]
    trips, events = [], []
    base = datetime(2024,1,1)
    eid  = 1
    for i in range(1, n_trips+1):
        u  = random.choice(users)
        ss = random.choice(stations)
        es = random.choice(stations)
        st = base + timedelta(days=random.randint(0,364), minutes=random.randint(0,1439))
        et = st + timedelta(minutes=random.randint(3,180))
        trips.append({
            'trip_id':i, 'user_id':u['user_id'],
            'start_station_id':ss['station_id'], 'end_station_id':es['station_id'],
            'start_time':st.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time':et.strftime('%Y-%m-%d %H:%M:%S'),
            'total_cost':round(random.uniform(0.5,50),2)
        })
        dur = (et-st).total_seconds()
        for _ in range(n_ev):
            etype = random.choice(ETYPES)
            ts    = st + timedelta(seconds=random.uniform(0,dur))
            events.append({
                'event_id':eid, 'trip_id':i,
                'timestamp':ts.strftime('%Y-%m-%d %H:%M:%S'),
                'event_type':etype, 'value':_eval(etype)
            })
            eid += 1
    return dict(users=users, stations=stations, trips=trips, events=events)

# ─────────────────────────────────────────────────────────────────────────────
# SQLITE BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,name TEXT,surname TEXT,birthdate TEXT,country TEXT);
CREATE TABLE IF NOT EXISTS stations(station_id INTEGER PRIMARY KEY,name TEXT,city TEXT,max_capacity INTEGER);
CREATE TABLE IF NOT EXISTS trips(trip_id INTEGER PRIMARY KEY,user_id INTEGER,start_station_id INTEGER,end_station_id INTEGER,start_time TEXT,end_time TEXT,total_cost REAL);
CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY,trip_id INTEGER,timestamp TEXT,event_type TEXT,value TEXT);
CREATE INDEX IF NOT EXISTS idx_tu    ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_ts    ON trips(start_station_id);
CREATE INDEX IF NOT EXISTS idx_te    ON trips(end_station_id);
CREATE INDEX IF NOT EXISTS idx_et    ON events(trip_id);
CREATE INDEX IF NOT EXISTS idx_etype ON events(event_type);
"""

Q1 = "SELECT t.trip_id,u.name,u.surname,ss.name,es.name,t.start_time,t.end_time,t.total_cost FROM trips t JOIN users u ON u.user_id=t.user_id JOIN stations ss ON ss.station_id=t.start_station_id JOIN stations es ON es.station_id=t.end_station_id"
Q2 = "SELECT u.user_id,u.name,COUNT(t.trip_id),ROUND(AVG((JULIANDAY(t.end_time)-JULIANDAY(t.start_time))*1440),2) FROM users u LEFT JOIN trips t ON t.user_id=u.user_id GROUP BY u.user_id"
Q3 = "SELECT s.station_id,s.name,COUNT(DISTINCT ts.trip_id),COUNT(DISTINCT te.trip_id) FROM stations s LEFT JOIN trips ts ON ts.start_station_id=s.station_id LEFT JOIN trips te ON te.end_station_id=s.station_id GROUP BY s.station_id"
Q4 = "SELECT DISTINCT t.trip_id,t.user_id,t.total_cost FROM trips t JOIN events e ON e.trip_id=t.trip_id WHERE e.event_type='ERROR'"

def run_sqlite(ds):
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.executescript(DDL)
    conn.commit()
    cur = conn.cursor()
    cur.executemany("INSERT OR IGNORE INTO users VALUES(:user_id,:name,:surname,:birthdate,:country)", ds['users'])
    cur.executemany("INSERT OR IGNORE INTO stations VALUES(:station_id,:name,:city,:max_capacity)", ds['stations'])
    cur.executemany("INSERT OR IGNORE INTO trips VALUES(:trip_id,:user_id,:start_station_id,:end_station_id,:start_time,:end_time,:total_cost)", ds['trips'])
    cur.executemany("INSERT OR IGNORE INTO events VALUES(:event_id,:trip_id,:timestamp,:event_type,:value)", ds['events'])
    conn.commit()
    results = {}
    for name, sql in [('Q1',Q1),('Q2',Q2),('Q3',Q3),('Q4',Q4)]:
        t0 = time.perf_counter()
        rows = conn.execute(sql).fetchall()
        results[name] = round(time.perf_counter()-t0, 4)
    conn.close()
    return results

# ─────────────────────────────────────────────────────────────────────────────
# MONGODB BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def run_mongodb(ds):
    try:
        from pymongo import MongoClient, ASCENDING
        client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        db = client['adm_benchmark']

        user_idx    = {u['user_id']:u    for u in ds['users']}
        station_idx = {s['station_id']:s for s in ds['stations']}
        event_idx   = {}
        for e in ds['events']:
            event_idx.setdefault(e['trip_id'],[]).append({
                'event_id':e['event_id'],'timestamp':e['timestamp'],
                'event_type':e['event_type'],'value':e['value']
            })

        db.trips.drop()
        trip_docs = []
        for t in ds['trips']:
            u  = user_idx[t['user_id']]
            ss = station_idx[t['start_station_id']]
            es = station_idx[t['end_station_id']]
            trip_docs.append({
                '_id': t['trip_id'],
                'user': {'user_id':u['user_id'],'name':u['name'],'surname':u['surname'],
                         'birthdate':u['birthdate'],'country':u['country']},
                'start_station': {'station_id':ss['station_id'],'name':ss['name'],'city':ss['city']},
                'end_station':   {'station_id':es['station_id'],'name':es['name'],'city':es['city']},
                'start_time': t['start_time'], 'end_time': t['end_time'],
                'total_cost': t['total_cost'],
                'events': event_idx.get(t['trip_id'],[])
            })
        db.trips.insert_many(trip_docs, ordered=False)
        db.trips.create_index([('user.user_id', ASCENDING)])
        db.trips.create_index([('events.event_type', ASCENDING)])

        results = {}

        # Q1
        t0 = time.perf_counter()
        list(db.trips.find({},{'user':1,'start_station.name':1,'end_station.name':1,'start_time':1,'end_time':1,'total_cost':1}))
        results['Q1'] = round(time.perf_counter()-t0, 4)

        # Q2
        t0 = time.perf_counter()
        list(db.trips.aggregate([
            {'$addFields':{'start_dt':{'$dateFromString':{'dateString':'$start_time','format':'%Y-%m-%d %H:%M:%S'}},'end_dt':{'$dateFromString':{'dateString':'$end_time','format':'%Y-%m-%d %H:%M:%S'}}}},
            {'$addFields':{'dur':{'$divide':[{'$subtract':['$end_dt','$start_dt']},60000]}}},
            {'$group':{'_id':'$user.user_id','num_trips':{'$sum':1},'avg_dur':{'$avg':'$dur'}}}
        ]))
        results['Q2'] = round(time.perf_counter()-t0, 4)

        # Q3
        t0 = time.perf_counter()
        list(db.trips.aggregate([{'$group':{'_id':'$start_station.station_id','trips_starting':{'$sum':1}}}]))
        list(db.trips.aggregate([{'$group':{'_id':'$end_station.station_id','trips_ending':{'$sum':1}}}]))
        results['Q3'] = round(time.perf_counter()-t0, 4)

        # Q4
        t0 = time.perf_counter()
        list(db.trips.find({'events':{'$elemMatch':{'event_type':'ERROR'}}},{'user.user_id':1,'total_cost':1}))
        results['Q4'] = round(time.perf_counter()-t0, 4)

        return results

    except Exception as e:
        return {'Q1':'SKIP','Q2':'SKIP','Q3':'SKIP','Q4':'SKIP','error':str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# NEO4J BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def run_neo4j(ds):
    try:
        from neo4j import GraphDatabase
        uri  = os.getenv('NEO4J_URI',  'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        pw   = os.getenv('NEO4J_PASS', 'password')
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        driver.verify_connectivity()

        BATCH = 500
        def chunks(lst, n):
            for i in range(0, len(lst), n): yield lst[i:i+n]

        with driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
            for chunk in chunks(ds['users'], BATCH):
                s.run("UNWIND $rows AS r MERGE (u:USER {user_id:r.user_id}) SET u.name=r.name,u.surname=r.surname,u.birthdate=r.birthdate,u.country=r.country", rows=chunk)
            for chunk in chunks(ds['stations'], BATCH):
                s.run("UNWIND $rows AS r MERGE (s:STATION {station_id:r.station_id}) SET s.name=r.name,s.city=r.city,s.max_capacity=r.max_capacity", rows=chunk)
            for chunk in chunks(ds['trips'], BATCH):
                s.run("UNWIND $rows AS r MATCH (u:USER {user_id:r.user_id}) MATCH (ss:STATION {station_id:r.start_station_id}) MATCH (es:STATION {station_id:r.end_station_id}) MERGE (t:TRIP {trip_id:r.trip_id}) SET t.start_time=r.start_time,t.end_time=r.end_time,t.total_cost=r.total_cost MERGE (u)-[:PERFORMED]->(t) MERGE (t)-[:STARTS_AT]->(ss) MERGE (t)-[:ENDS_AT]->(es)", rows=chunk)

        sample_uid = ds['users'][0]['user_id']

        with driver.session() as s:
            t0 = time.perf_counter()
            s.run("MATCH (u:USER {user_id:$uid})-[:PERFORMED]->(t:TRIP)-[:STARTS_AT|ENDS_AT]->(s:STATION) RETURN DISTINCT s.station_id,s.name,s.city", uid=sample_uid).data()
            g1 = round(time.perf_counter()-t0, 4)

            t0 = time.perf_counter()
            s.run("MATCH (s:STATION) OPTIONAL MATCH (:TRIP)-[:STARTS_AT]->(s) WITH s,COUNT(*) AS out OPTIONAL MATCH (:TRIP)-[:ENDS_AT]->(s) WITH s,out,COUNT(*) AS inc RETURN s.station_id,s.name,out+inc AS total ORDER BY total DESC LIMIT 3").data()
            g2 = round(time.perf_counter()-t0, 4)

        driver.close()
        return {'G1': g1, 'G2': g2}

    except Exception as e:
        return {'G1':'SKIP','G2':'SKIP','error':str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# SPARK BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def run_spark(ds):
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F

        spark = (SparkSession.builder
                 .appName('ADM_Benchmark')
                 .master('local[*]')
                 .config('spark.sql.shuffle.partitions','8')
                 .config('spark.driver.memory','2g')
                 .getOrCreate())
        spark.sparkContext.setLogLevel('ERROR')

        trip_rows = [(t['trip_id'],t['user_id'],t['start_time'],t['end_time']) for t in ds['trips']]
        user_rows = [(u['user_id'],u['name'],u['surname']) for u in ds['users']]

        trips_df = spark.createDataFrame(trip_rows,['trip_id','user_id','start_time','end_time'])
        users_df = spark.createDataFrame(user_rows,['user_id','name','surname'])

        trips_df = (trips_df
            .withColumn('start_ts', F.to_timestamp('start_time','yyyy-MM-dd HH:mm:ss'))
            .withColumn('end_ts',   F.to_timestamp('end_time',  'yyyy-MM-dd HH:mm:ss'))
            .withColumn('dur_min',  (F.unix_timestamp('end_ts')-F.unix_timestamp('start_ts'))/60.0))

        t0 = time.perf_counter()
        result = (trips_df.groupBy('user_id')
            .agg(F.count('trip_id').alias('num_trips'), F.round(F.avg('dur_min'),2).alias('avg_min'))
            .join(users_df,'user_id','right')
            .fillna({'num_trips':0,'avg_min':0.0}))
        result.count()
        spark_q2 = round(time.perf_counter()-t0, 4)

        spark.stop()
        return {'Spark_Q2': spark_q2}

    except Exception as e:
        return {'Spark_Q2':'SKIP','error':str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# PRINT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def line(char='-', n=90): return char * n

def print_and_save(text, f):
    print(text)
    f.write(text + '\n')

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

CONFIGS = [
    (1_000,   10_000,  0),
    (1_000,   10_000,  2),
    (1_000,   10_000,  5),
    (1_000,   10_000,  10),
    (10_000,  50_000,  0),
    (10_000,  50_000,  2),
    (10_000,  50_000,  5),
    (10_000,  50_000,  10),
    (50_000,  100_000, 0),
    (50_000,  100_000, 2),
    (50_000,  100_000, 5),
    (50_000,  100_000, 10),
]

if __name__ == '__main__':

    out_file = open('benchmark_results.txt', 'w', encoding='utf-8')

    def p(text): print_and_save(text, out_file)

    p(line('='))
    p('  ADM PROJECT - FULL BENCHMARK RESULTS')
    p('  City Mobility Platform - A.Y. 2025/2026')
    p(f'  Run at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p(line('='))

    sqlite_all  = []
    mongo_all   = []
    neo4j_all   = []
    spark_all   = []

    # ── SQLITE ────────────────────────────────────────────────────────────────
    p('\n' + line())
    p('  1.  RELATIONAL MODEL - SQLite Queries (Q1, Q2, Q3, Q4)')
    p('      Command: python relational_queries.py')
    p(line())
    p(f'  {"Config":<40}  {"Q1":>8}  {"Q2":>8}  {"Q3":>8}  {"Q4":>8}')
    p(f'  {"":<40}  {"(sec)":>8}  {"(sec)":>8}  {"(sec)":>8}  {"(sec)":>8}')
    p('  ' + line('-', 80))

    for nu, nt, ne in CONFIGS:
        cfg = f'users={nu:,}  trips={nt:,}  events/trip={ne}'
        print(f'  Running SQLite: {cfg} ...', end='', flush=True)
        ds = generate(nu, nt, ne)
        r  = run_sqlite(ds)
        sqlite_all.append((nu, nt, ne, r, ds))
        p(f'\n  {cfg:<40}  {r["Q1"]:>8}  {r["Q2"]:>8}  {r["Q3"]:>8}  {r["Q4"]:>8}')

    # ── MONGODB ───────────────────────────────────────────────────────────────
    p('\n\n' + line())
    p('  2.  DOCUMENT MODEL - MongoDB Queries (Q1, Q2, Q3, Q4)')
    p('      Command: python document_queries.py')
    p(line())
    p(f'  {"Config":<40}  {"Q1":>8}  {"Q2":>8}  {"Q3":>8}  {"Q4":>8}')
    p(f'  {"":<40}  {"(sec)":>8}  {"(sec)":>8}  {"(sec)":>8}  {"(sec)":>8}')
    p('  ' + line('-', 80))

    for nu, nt, ne, _, ds in sqlite_all:
        cfg = f'users={nu:,}  trips={nt:,}  events/trip={ne}'
        print(f'  Running MongoDB: {cfg} ...', end='', flush=True)
        r   = run_mongodb(ds)
        mongo_all.append((nu, nt, ne, r))
        if 'error' in r:
            p(f'\n  {cfg:<40}  SKIPPED - MongoDB not running')
            p(f'  Error: {r["error"][:60]}')
        else:
            p(f'\n  {cfg:<40}  {r["Q1"]:>8}  {r["Q2"]:>8}  {r["Q3"]:>8}  {r["Q4"]:>8}')

    # ── NEO4J ─────────────────────────────────────────────────────────────────
    p('\n\n' + line())
    p('  3.  GRAPH MODEL - Neo4j Queries (G1, G2)')
    p('      Command: python graph_queries.py')
    p(line())
    p(f'  {"Config":<40}  {"G1":>10}  {"G2":>10}')
    p(f'  {"":<40}  {"(sec)":>10}  {"(sec)":>10}')
    p('  ' + line('-', 66))

    for nu, nt, ne, _, ds in sqlite_all:
        cfg = f'users={nu:,}  trips={nt:,}  events/trip={ne}'
        print(f'  Running Neo4j: {cfg} ...', end='', flush=True)
        r   = run_neo4j(ds)
        neo4j_all.append((nu, nt, ne, r))
        if 'error' in r:
            p(f'\n  {cfg:<40}  SKIPPED - Neo4j not running')
            p(f'  Error: {r["error"][:60]}')
            p(f'  Fix: Set $env:NEO4J_PASS="yourpassword" then rerun')
        else:
            p(f'\n  {cfg:<40}  {r["G1"]:>10}  {r["G2"]:>10}')

    # ── SPARK ─────────────────────────────────────────────────────────────────
    p('\n\n' + line())
    p('  4.  SPARK - Query 2 DataFrame vs SQLite')
    p('      Command: python spark_queries.py')
    p(line())
    p(f'  {"Config":<40}  {"SQLite Q2":>12}  {"Spark Q2":>12}')
    p(f'  {"":<40}  {"(sec)":>12}  {"(sec)":>12}')
    p('  ' + line('-', 70))

    for nu, nt, ne, sql_r, ds in sqlite_all:
        cfg = f'users={nu:,}  trips={nt:,}  events/trip={ne}'
        print(f'  Running Spark: {cfg} ...', end='', flush=True)
        r   = run_spark(ds)
        spark_all.append((nu, nt, ne, r))
        if 'error' in r:
            p(f'\n  {cfg:<40}  {sql_r["Q2"]:>12}  {"SKIPPED":>12}')
            p(f'  Spark error: {r["error"][:60]}')
        else:
            p(f'\n  {cfg:<40}  {sql_r["Q2"]:>12}  {r["Spark_Q2"]:>12}')

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    p('\n\n' + line('='))
    p('  SUMMARY - All results saved to: benchmark_results.txt')
    p('  Copy the numbers from above into your Word benchmark table.')
    p(line('='))

    out_file.close()
    print('\n\nDone! Results saved to benchmark_results.txt')
    print('Open that file and copy the numbers into your Word table.')
