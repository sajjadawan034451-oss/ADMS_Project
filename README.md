# ADM Project – City Mobility Platform
### Advanced Data Management · A.Y. 2025/2026

---

## Project Structure

```
adm_project/
├── data_generation/
│   └── generate_data.py        ← synthetic data generator (no dependencies)
├── sql/
│   └── relational_queries.py   ← Part 1: SQLite schema + Q1–Q4 + benchmark
├── mongodb/
│   └── document_queries.py     ← Part 1: MongoDB document model + Q1–Q4
├── neo4j/
│   └── graph_queries.py        ← Part 2: Neo4j graph model + G1, G2
├── spark/
│   └── spark_queries.py        ← Spark Q2 (DataFrame) + PageRank + ConnComp
├── report/
│   └── generate_report.py      ← generates report.pdf using ReportLab
└── README.md
```

---

## Step-by-Step Setup Guide

### STEP 1 — Install Python dependencies

Open a terminal in the project folder and run:

```bash
pip install pymongo neo4j pyspark reportlab
```

> SQLite is built into Python — no installation needed.

---

### STEP 2 — Start MongoDB

Make sure MongoDB is running on the default port (27017).

**Windows:**
```
# If installed as a service it starts automatically.
# Otherwise open Services → MongoDB → Start
# Or from cmd:
net start MongoDB
```

**Mac/Linux:**
```bash
brew services start mongodb-community   # Mac (Homebrew)
sudo systemctl start mongod             # Linux
```

Verify it works:
```bash
mongosh --eval "db.runCommand({ping:1})"
```

---

### STEP 3 — Start Neo4j

**Windows / Mac / Linux:**
1. Open the Neo4j Desktop application
2. Start your local DBMS (default: bolt://localhost:7687)
3. Default credentials: user = `neo4j`, password = `password`
   (change these in `neo4j/graph_queries.py` if different)

Or via command line:
```bash
neo4j start          # Linux/Mac service
neo4j console        # foreground mode
```

---

### STEP 4 — Set up Java for PySpark

PySpark requires Java 8 or higher. Check if you have it:
```bash
java -version
```

If not installed, download from:
https://adoptium.net/  (Temurin JDK 11 recommended)

Set the environment variable:
```bash
# Mac/Linux — add to ~/.bashrc or ~/.zshrc
export JAVA_HOME=/path/to/jdk

# Windows (PowerShell)
$env:JAVA_HOME = "C:\Program Files\Java\jdk-11"
```

---

### STEP 5 — Run the SQLite queries (Part 1 – Relational)

```bash
cd adm_project
python sql/relational_queries.py
```

This will:
- Generate synthetic datasets at 4 scales
- Create in-memory SQLite databases
- Run Q1, Q2, Q3, Q4 and print timing results

**Expected output:**
```
─────────────────────────────────────────────────────
  Relational Benchmark  users=1000  trips=10000  events/trip=0
─────────────────────────────────────────────────────
  [Q1]  rows=  10,000  time=0.0276s
  [Q2]  rows=   1,000  time=0.0088s
  [Q3]  rows=      50  time=0.4377s
  [Q4]  rows=       0  time=0.0002s
...
```

---

### STEP 6 — Run the MongoDB queries (Part 1 – Document model)

Make sure MongoDB is running (Step 2), then:

```bash
python mongodb/document_queries.py
```

This connects to `mongodb://localhost:27017`, creates the `adm_mobility` database,
loads data, and runs all four queries with timing.

---

### STEP 7 — Run the Neo4j queries (Part 2 – Graph model)

Make sure Neo4j is running (Step 3), then:

```bash
python neo4j/graph_queries.py
```

Set credentials via environment variables if needed:
```bash
# Mac/Linux
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASS=yourpassword

# Windows PowerShell
$env:NEO4J_PASS = "yourpassword"
```

---

### STEP 8 — Run PySpark queries

**Basic Spark Q2 (no GraphFrames needed):**
```bash
python spark/spark_queries.py
```

**Full run with GraphFrames (PageRank + Connected Components):**
```bash
spark-submit \
  --packages graphframes:graphframes:0.8.3-spark3.5-s_2.12 \
  spark/spark_queries.py
```

> Windows: replace `\` with `` ` `` in PowerShell, or use a single line.

---

### STEP 9 — Regenerate the PDF report

```bash
python report/generate_report.py
```

Opens `report/report.pdf` — ready to submit.

---

## Running All Benchmarks at Once

```bash
python - << 'EOF'
import sys, os
sys.path.insert(0, 'data_generation')
from generate_data import generate_dataset

sys.path.insert(0, 'sql')
from relational_queries import benchmark as sql_bm

configs = [
    (1_000, 10_000, 0), (1_000, 10_000, 2),
    (10_000, 50_000, 5), (50_000, 100_000, 10),
]
for n_u, n_t, n_e in configs:
    ds = generate_dataset(n_u, n_t, n_e)
    sql_bm(ds, f"u={n_u} t={n_t} e={n_e}")
EOF
```

---

## Query Quick Reference

| Query | Description | File |
|-------|-------------|------|
| Q1 | All trips with user + station names | `sql/relational_queries.py` → `Q1` |
| Q2 | Users with trip count + avg duration | `sql/relational_queries.py` → `Q2` |
| Q3 | Stations with start/end trip counts | `sql/relational_queries.py` → `Q3` |
| Q4 | Trips with at least one ERROR event | `sql/relational_queries.py` → `Q4` |
| G1 | Stations reachable by a given user | `neo4j/graph_queries.py` → `g1_reachable_stations` |
| G2 | Top-3 stations by trip volume | `neo4j/graph_queries.py` → `g2_top3_stations` |
| Spark Q2 | User stats via PySpark DataFrame | `spark/spark_queries.py` → `spark_q2` |
| PageRank | Station PageRank via GraphFrames | `spark/spark_queries.py` → `spark_pagerank` |
| ConnComp | Connected components of stations | `spark/spark_queries.py` → `spark_connected_components` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: pymongo` | Run `pip install pymongo` |
| `ModuleNotFoundError: neo4j` | Run `pip install neo4j` |
| `ConnectionRefusedError` (MongoDB) | Start MongoDB service (Step 2) |
| `ServiceUnavailable` (Neo4j) | Start Neo4j Desktop DBMS (Step 3) |
| `JAVA_HOME not set` | Install Java 11 and set JAVA_HOME (Step 4) |
| `graphframes not found` | Use `spark-submit --packages graphframes:...` not `python` |
| Q3 very slow | Expected — double self-join. See report Section 2.5 for analysis. |
