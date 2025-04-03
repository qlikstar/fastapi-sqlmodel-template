#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection using environment variables.
This script will attempt both synchronous and asynchronous connections.
"""

import os
import asyncio
import urllib.parse
from dotenv import load_dotenv
import asyncpg
import psycopg2
from enum import Enum

# Load environment variables
load_dotenv()

# Define DB options enum (similar to your app)
class DBOption(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"

# Get DB settings from environment
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "")

print(f"Database Engine: {DB_ENGINE}")

if DB_ENGINE != "postgres":
    print("Not using PostgreSQL. Exiting.")
    exit(0)

# URL encode the password to handle special characters
encoded_password = urllib.parse.quote_plus(POSTGRES_PASSWORD)

# Test synchronous connection with psycopg2
def test_sync_connection():
    print("\n--- Testing Synchronous Connection (psycopg2) ---")
    try:
        # Connection string
        conn_string = f"host={POSTGRES_SERVER} port={POSTGRES_PORT} dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
        print(f"Connecting to: postgresql://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")
        
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(conn_string)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a test query
        cur.execute("SELECT version();")
        
        # Get the result
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        # Close the cursor and connection
        cur.close()
        conn.close()
        print("Synchronous connection test: SUCCESS")
        return True
    except Exception as e:
        print(f"Synchronous connection test: FAILED")
        print(f"Error: {str(e)}")
        return False

# Test asynchronous connection with asyncpg
async def test_async_connection():
    print("\n--- Testing Asynchronous Connection (asyncpg) ---")
    try:
        # Try with SSL enabled (default)
        print("Attempting connection with SSL enabled...")
        print(f"Connecting to: postgresql://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")
        
        conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_SERVER,
            port=POSTGRES_PORT,
            database=POSTGRES_DB
        )
        
        # Execute a test query
        version = await conn.fetchval("SELECT version();")
        print(f"PostgreSQL version: {version}")
        
        # Close the connection
        await conn.close()
        print("Asynchronous connection test (with SSL): SUCCESS")
        return True
    except Exception as e:
        print(f"Asynchronous connection test (with SSL): FAILED")
        print(f"Error: {str(e)}")
        
        # Try again with SSL disabled
        try:
            print("\nAttempting connection with SSL disabled...")
            print(f"Connecting to: postgresql://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=disable")
            
            conn = await asyncpg.connect(
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_SERVER,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                ssl=False
            )
            
            # Execute a test query
            version = await conn.fetchval("SELECT version();")
            print(f"PostgreSQL version: {version}")
            
            # Close the connection
            await conn.close()
            print("Asynchronous connection test (without SSL): SUCCESS")
            return True
        except Exception as e2:
            print(f"Asynchronous connection test (without SSL): FAILED")
            print(f"Error: {str(e2)}")
            return False

# Test connection string format
def test_connection_string_formats():
    print("\n--- Connection String Formats ---")
    
    # Standard format
    std_format = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    print(f"Standard format: postgresql://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")
    
    # asyncpg format
    asyncpg_format = f"postgresql+asyncpg://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    print(f"asyncpg format: postgresql+asyncpg://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")
    
    # With SSL mode
    ssl_format = f"postgresql+asyncpg://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=require"
    print(f"With SSL mode: postgresql+asyncpg://{POSTGRES_USER}:***@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=require")

# Main function
async def main():
    print("=== PostgreSQL Connection Test ===")
    print(f"Server: {POSTGRES_SERVER}")
    print(f"Port: {POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DB}")
    print(f"User: {POSTGRES_USER}")
    
    # Test connection string formats
    test_connection_string_formats()
    
    # Test synchronous connection
    sync_result = test_sync_connection()
    
    # Test asynchronous connection
    async_result = await test_async_connection()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Synchronous connection (psycopg2): {'SUCCESS' if sync_result else 'FAILED'}")
    print(f"Asynchronous connection (asyncpg): {'SUCCESS' if async_result else 'FAILED'}")
    
    if sync_result and not async_result:
        print("\nDIAGNOSIS: The issue appears to be specific to asyncpg. Your database credentials are correct.")
        print("RECOMMENDATION: Check your application's asyncpg configuration, especially SSL settings.")
    elif not sync_result and not async_result:
        print("\nDIAGNOSIS: Unable to connect with either method. Check your database credentials and network.")
    elif sync_result and async_result:
        print("\nDIAGNOSIS: Both connection methods work. The issue might be in your application code.")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
