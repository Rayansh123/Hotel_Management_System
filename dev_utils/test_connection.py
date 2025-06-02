from db_utils import get_db

def test_connection():
    try:
        print(" Attempting to connect to MySQL...")
        conn = get_db()
        
        if conn.is_connected():
            print("Connection successful!")
            print("\nDatabase details:")
            print(f"- Host: {conn.server_host}")
            print(f"- Schema: {conn.database}")
            
            # Verify tables exist
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("\n Tables in your database:")
            for table in tables:
                print(f"- {table[0]}")
            
        else:
            print(" Connection failed (no error thrown)")
            
    except Exception as e:
        print(f"Connection failed: {str(e)}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("\n🔌 Connection closed.")

if __name__ == "__main__":
    test_connection()