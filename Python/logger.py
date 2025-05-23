import os
import re
import pyodbc
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()
DB_CONN_STR = os.getenv("DB_CONN_STR")

BACKEND_LOG_PATH = 'app.log'
FRONTEND_LOG_PATH = 'frontend.log'

def create_tables_and_indexes(cursor):
    # Create BackendLogs table (no StackTrace)
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='BackendLogs' AND xtype='U')
        CREATE TABLE BackendLogs (
            LogID INT IDENTITY(1,1) PRIMARY KEY,
            LogTimestamp DATETIME NOT NULL,
            LogLevel NVARCHAR(20) NOT NULL,
            Message NVARCHAR(MAX) NOT NULL,
            LogHash CHAR(64) NULL
        )
    """)

    # Create FrontendLogs table
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FrontendLogs' AND xtype='U')
        CREATE TABLE FrontendLogs (
            LogID INT IDENTITY(1,1) PRIMARY KEY,
            LogTimestamp DATETIME NOT NULL,
            LogLevel NVARCHAR(20) NOT NULL,
            Message NVARCHAR(MAX) NOT NULL,
            Metadata NVARCHAR(MAX) NULL,
            LogHash CHAR(64) NULL
        )
    """)

    # Ensure LogHash column exists
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE Name = N'LogHash' AND Object_ID = Object_ID(N'BackendLogs')
        )
        ALTER TABLE BackendLogs ADD LogHash CHAR(64) NULL
    """)

    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE Name = N'LogHash' AND Object_ID = Object_ID(N'FrontendLogs')
        )
        ALTER TABLE FrontendLogs ADD LogHash CHAR(64) NULL
    """)

    # Create unique index on LogHash
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.indexes 
            WHERE name = 'UQ_BackendLogs_LogHash' AND object_id = OBJECT_ID('BackendLogs')
        )
        CREATE UNIQUE INDEX UQ_BackendLogs_LogHash ON BackendLogs(LogHash)
    """)

    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.indexes 
            WHERE name = 'UQ_FrontendLogs_LogHash' AND object_id = OBJECT_ID('FrontendLogs')
        )
        CREATE UNIQUE INDEX UQ_FrontendLogs_LogHash ON FrontendLogs(LogHash)
    """)

def parse_log_line(line):
    # Example: 2025-05-22 15:22:30,123 - ERROR - Something bad happened
    match = re.match(r'^(?P<timestamp>[\d\-:\s,.]+) - (?P<level>\w+) - (?P<message>.*)$', line)
    if not match:
        return None
    ts_str = match.group('timestamp')
    try:
        timestamp = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
    except ValueError:
        try:
            timestamp = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    level = match.group('level')
    message = match.group('message')
    return timestamp, level, message

def extract_metadata(message):
    match = re.search(r'({.*})', message)
    if match:
        try:
            return json.dumps(json.loads(match.group(1)))  # return as stringified JSON
        except json.JSONDecodeError:
            return None
    return None

def compute_log_hash(timestamp, level, message):
    combined = f"{timestamp.isoformat()}|{level}|{message}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def insert_logs(cursor, filepath, table_name, has_metadata=False):
    if not os.path.exists(filepath):
        print(f"⚠️ Log file not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                parsed = parse_log_line(line.strip())
                if not parsed:
                    continue

                timestamp, level, raw_message = parsed
                log_hash = compute_log_hash(timestamp, level, raw_message)

                # Skip duplicates
                cursor.execute(f"SELECT 1 FROM {table_name} WHERE LogHash = ?", (log_hash,))
                if cursor.fetchone():
                    continue

                if has_metadata and " | Metadata:" in raw_message:
                    message_text, metadata_part = raw_message.split(" | Metadata:", 1)
                    message_text = message_text.strip()

                    try:
                        metadata_dict = json.loads(metadata_part.strip().replace("'", '"'))
                        metadata_json = json.dumps(metadata_dict)
                    except json.JSONDecodeError:
                        metadata_json = None

                    # cursor.execute(f"""
                    #     INSERT INTO {table_name}
                    #       (LogTimestamp, LogLevel, Message, Metadata, LogHash)
                    #     VALUES (?, ?, ?, ?, ?)
                    # """, (timestamp, level, message_text, metadata_json, log_hash))
                    cursor.execute(f"""
    INSERT INTO {table_name}
      (LogTimestamp, LogLevel, Message, Metadata, LogHash)
    VALUES (?, ?, ?, ?, ?)
""", (timestamp, level, message_text, metadata_json, log_hash))


                else:
                    # cursor.execute(f"""
                    #     INSERT INTO {table_name}
                    #       (LogTimestamp, LogLevel, Message, LogHash)
                    #     VALUES (?, ?, ?, ?)
                    # """, (timestamp, level, raw_message, log_hash))
                    cursor.execute("""
    EXEC InsertBackendLog ?, ?, ?, ?
""", (timestamp, level, raw_message, log_hash))


            except Exception as e:
                print(f"❌ Failed to process line: {line.strip()}")
                print(f"    Reason: {e}")

def process_logs():
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()

        create_tables_and_indexes(cursor)

        print("📥 Processing Backend Logs...")
        insert_logs(cursor, BACKEND_LOG_PATH, 'BackendLogs')
        print("✅ Backend logs complete.")

        print("📥 Processing Frontend Logs...")
        insert_logs(cursor, FRONTEND_LOG_PATH, 'FrontendLogs', has_metadata=True)
        print("✅ Frontend logs complete.")

        conn.commit()
        print("✅ Logs successfully inserted into the database.")
    except Exception as e:
        print("❌ Error during log processing:", str(e))
        print(traceback.format_exc())
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    process_logs()


