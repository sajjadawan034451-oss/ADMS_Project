

import random
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)

ITALIAN_CITIES = [
    "Milan", "Rome", "Naples", "Turin", "Palermo",
    "Genoa", "Bologna", "Florence", "Bari", "Catania",
    "Venice", "Verona", "Padua", "Trieste", "Brescia",
]

FIRST_NAMES = [
    "Luca", "Marco", "Sara", "Giulia", "Anna", "Paolo",
    "Maria", "Luigi", "Elena", "Roberto", "Chiara", "Andrea",
    "Francesca", "Antonio", "Valentina", "Stefano", "Martina", "Davide",
]

LAST_NAMES = [
    "Rossi", "Bianchi", "Ferrari", "Esposito", "Romano",
    "Colombo", "Ricci", "Marino", "Greco", "Bruno",
    "Gallo", "Conti", "De Luca", "Costa", "Mancini",
]

COUNTRIES = ["Italy", "France", "Germany", "Spain", "UK", "Poland", "Romania"]

EVENT_TYPES = ["GPS", "ERROR", "BATTERY", "DELAY"]

ERROR_CODES = ["E001", "E002", "E003", "E004", "E005"]


def _rand_date(start_year=1960, end_year=2005):
    start = datetime(start_year, 1, 1)
    delta = datetime(end_year, 12, 31) - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def _event_value(etype):
    if etype == "GPS":
        lat = round(random.uniform(36.0, 47.0), 6)
        lon = round(random.uniform(6.0, 18.0), 6)
        return f"{lat},{lon}"
    elif etype == "ERROR":
        return random.choice(ERROR_CODES)
    elif etype == "BATTERY":
        return str(random.randint(0, 100))
    else:  # DELAY
        return str(random.randint(1, 120))


# ── Public generators ─────────────────────────────────────────────────────────

def generate_users(n):
    return [
        {
            "user_id":   i,
            "name":      random.choice(FIRST_NAMES),
            "surname":   random.choice(LAST_NAMES),
            "birthdate": _rand_date(),
            "country":   random.choice(COUNTRIES),
        }
        for i in range(1, n + 1)
    ]


def generate_stations(n=50):
    stations = []
    for i in range(1, n + 1):
        city = random.choice(ITALIAN_CITIES)
        stations.append({
            "station_id":   i,
            "name":         f"{city} Station {i}",
            "city":         city,
            "max_capacity": random.randint(5, 30),
        })
    return stations


def generate_trips(n, users, stations):
    trips = []
    base = datetime(2024, 1, 1)
    for i in range(1, n + 1):
        user    = random.choice(users)
        start_s = random.choice(stations)
        end_s   = random.choice(stations)
        # Allow same start/end (round trip) — realistic for scooter share
        start_t = base + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        dur_min = random.randint(3, 180)
        end_t   = start_t + timedelta(minutes=dur_min)
        trips.append({
            "trip_id":          i,
            "user_id":          user["user_id"],
            "start_station_id": start_s["station_id"],
            "end_station_id":   end_s["station_id"],
            "start_time":       start_t.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time":         end_t.strftime("%Y-%m-%d %H:%M:%S"),
            "total_cost":       round(random.uniform(0.50, 50.00), 2),
        })
    return trips


def generate_events(trips, events_per_trip):
    events = []
    eid = 1
    for trip in trips:
        start_t = datetime.strptime(trip["start_time"], "%Y-%m-%d %H:%M:%S")
        end_t   = datetime.strptime(trip["end_time"],   "%Y-%m-%d %H:%M:%S")
        dur_sec = (end_t - start_t).total_seconds()
        for _ in range(events_per_trip):
            etype = random.choice(EVENT_TYPES)
            ts    = start_t + timedelta(seconds=random.uniform(0, dur_sec))
            events.append({
                "event_id":   eid,
                "trip_id":    trip["trip_id"],
                "timestamp":  ts.strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": etype,
                "value":      _event_value(etype),
            })
            eid += 1
    return events


def generate_dataset(n_users, n_trips, events_per_trip, n_stations=50):
    """
    Returns a dict with keys: users, stations, trips, events.
    All values are lists of plain dicts.
    """
    users    = generate_users(n_users)
    stations = generate_stations(n_stations)
    trips    = generate_trips(n_trips, users, stations)
    events   = generate_events(trips, events_per_trip)
    return {
        "users":    users,
        "stations": stations,
        "trips":    trips,
        "events":   events,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    n_users        = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000
    n_trips        = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
    events_per_trip = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    ds = generate_dataset(n_users, n_trips, events_per_trip)
    print(f"users={len(ds['users'])}  stations={len(ds['stations'])}  "
          f"trips={len(ds['trips'])}  events={len(ds['events'])}")

    fname = f"dataset_u{n_users}_t{n_trips}_e{events_per_trip}.json"
    with open(fname, "w") as f:
        json.dump(ds, f)
    print(f"Saved → {fname}")
