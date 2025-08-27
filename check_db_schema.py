#cat > check_db_schema.py << 'EOF'
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    print("=== CHECKING ASSIGNMENT DATABASE SCHEMA ===")
    
    # Show all tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
    tables = cur.fetchall()
    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Show columns for each table
    for table in tables:
        table_name = table[0]
        print(f"\n=== Table: {table_name} ===")
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
        
        # Show sample data
        try:
            cur.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cur.fetchall()
            if rows:
                print(f"  Sample data: {len(rows)} rows")
                for i, row in enumerate(rows):
                    print(f"    Row {i+1}: {row}")
        except Exception as e:
            print(f"  Could not fetch sample data: {e}")
    
    cur.close()
    conn.close()
    print("\n=== SCHEMA CHECK COMPLETE ===")
    
except Exception as e:
    print(f"Error connecting to database: {e}")
    print("Please check your DATABASE_URL in the .env file")
