import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    station_name_to_check = 'Congress Avenue'

    print(f"Checking trips for station: {station_name_to_check}\n")

    # First, get the station_id for "Congress Avenue"
    cur.execute("""
        SELECT station_id FROM stations
        WHERE station_name = %s
    """, (station_name_to_check,))
    result = cur.fetchone()

    if not result:
        print(f"No station found with name '{station_name_to_check}'")
    else:
        station_id = result[0]
        print(f"Station ID for '{station_name_to_check}': {station_id}\n")

        # Get all trips that start or end at this station
        cur.execute("""
            SELECT trip_id, bike_id, started_at, ended_at, start_station_id, end_station_id, trip_distance_km
            FROM trips
            WHERE start_station_id = %s OR end_station_id = %s
        """, (station_id, station_id))

        trips = cur.fetchall()
        if not trips:
            print(f"No trips found for station '{station_name_to_check}'")
        else:
            print(f"Found {len(trips)} trips involving '{station_name_to_check}':\n")
            for trip in trips:
                print(trip)

    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
