import mysql.connector
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv("config.env")

def get_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            autocommit=False  # Explicit transaction control
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def run_query(query, params=None, fetch=True, conn=None):
    """Enhanced with transaction support"""
    cursor = None
    close_conn = False
    
    try:
        if not conn:
            conn = get_db()
            close_conn = True
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid  # Return last inserted ID for INSERTs
            conn.commit()  # Explicit commit for write operations
            
        return result
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query failed: {str(e)}\nQuery: {query}\nParams: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if close_conn and conn and conn.is_connected():
            conn.close()

def execute_transaction(queries):
    """Execute multiple queries as an atomic transaction"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        results = []
        for query, params in queries:
            cursor.execute(query, params or ())
            if cursor.with_rows:
                results.append(cursor.fetchall())
            else:
                results.append(cursor.lastrowid)
        
        conn.commit()
        return results
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Transaction failed: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()