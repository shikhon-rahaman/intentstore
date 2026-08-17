import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.intentstore/intentstore.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS file_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            size_bytes INTEGER,
            extension TEXT,
            last_modified REAL,
            first_seen REAL,
            semantic_score REAL DEFAULT 0.0,
            access_entropy REAL DEFAULT 0.0,
            archival_urgency REAL DEFAULT 0.0,
            archival_recommendation TEXT,
            embedding TEXT,
            content_summary TEXT,
            updated_at REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            process_name TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")

def upsert_file(path, size_bytes, extension, last_modified):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().timestamp()
    c.execute("""
        INSERT INTO file_metadata (path, size_bytes, extension, last_modified, first_seen, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            size_bytes=excluded.size_bytes,
            last_modified=excluded.last_modified,
            updated_at=excluded.updated_at
    """, (path, size_bytes, extension, last_modified, now, now))
    conn.commit()
    conn.close()

def update_semantic_data(path, semantic_score, content_summary, embedding_json, archival_rec, urgency):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().timestamp()
    c.execute("""
        UPDATE file_metadata
        SET semantic_score=?, content_summary=?, embedding=?,
            archival_recommendation=?, archival_urgency=?, updated_at=?
        WHERE path=?
    """, (semantic_score, content_summary, embedding_json, archival_rec, urgency, now, path))
    conn.commit()
    conn.close()

def log_access_event(file_path, event_type, process_name=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO access_events (file_path, event_type, timestamp, process_name)
        VALUES (?, ?, ?, ?)
    """, (file_path, event_type, datetime.now().timestamp(), process_name))
    conn.commit()
    conn.close()

def get_all_files():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM file_metadata ORDER BY archival_urgency DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_high_urgency_files(threshold=0.6):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM file_metadata
        WHERE archival_urgency >= ?
        ORDER BY archival_urgency DESC
    """, (threshold,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_access_history(file_path):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM access_events
        WHERE file_path=?
        ORDER BY timestamp DESC
        LIMIT 50
    """, (file_path,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM file_metadata")
    total = c.fetchone()["total"]
    c.execute("SELECT COUNT(*) as urgent FROM file_metadata WHERE archival_urgency >= 0.6")
    urgent = c.fetchone()["urgent"]
    c.execute("SELECT SUM(size_bytes) as total_size FROM file_metadata")
    total_size = c.fetchone()["total_size"] or 0
    c.execute("SELECT COUNT(*) as events FROM access_events")
    events = c.fetchone()["events"]
    conn.close()
    return {
        "total_files": total,
        "urgent_files": urgent,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_events": events
    }