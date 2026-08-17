import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

from src.logger import get_logger

logger = get_logger("database")

DB_PATH = os.path.expanduser("~/.intentstore/intentstore.db")


@contextmanager
def _connection():
    conn = None
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        if conn:
            conn.rollback()
        logger.error("Database error: %s", exc)
        raise
    finally:
        if conn:
            conn.close()


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        with _connection() as conn:
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
        logger.info("Initialized database at %s", DB_PATH)
    except sqlite3.Error as exc:
        logger.error("Failed to initialize database: %s", exc)
        raise


def upsert_file(path, size_bytes, extension, last_modified):
    try:
        now = datetime.now().timestamp()
        with _connection() as conn:
            conn.cursor().execute("""
                INSERT INTO file_metadata (path, size_bytes, extension, last_modified, first_seen, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size_bytes=excluded.size_bytes,
                    last_modified=excluded.last_modified,
                    updated_at=excluded.updated_at
            """, (path, size_bytes, extension, last_modified, now, now))
        logger.debug("Upserted file: %s", path)
    except sqlite3.Error as exc:
        logger.error("Failed to upsert file %s: %s", path, exc)


def update_semantic_data(path, semantic_score, content_summary, embedding_json, archival_rec, urgency):
    try:
        now = datetime.now().timestamp()
        with _connection() as conn:
            conn.cursor().execute("""
                UPDATE file_metadata
                SET semantic_score=?, content_summary=?, embedding=?,
                    archival_recommendation=?, archival_urgency=?, updated_at=?
                WHERE path=?
            """, (semantic_score, content_summary, embedding_json, archival_rec, urgency, now, path))
        logger.debug("Updated semantic data for %s (urgency=%.2f)", path, urgency)
    except sqlite3.Error as exc:
        logger.error("Failed to update semantic data for %s: %s", path, exc)


def log_access_event(file_path, event_type, process_name=None):
    try:
        with _connection() as conn:
            conn.cursor().execute("""
                INSERT INTO access_events (file_path, event_type, timestamp, process_name)
                VALUES (?, ?, ?, ?)
            """, (file_path, event_type, datetime.now().timestamp(), process_name))
        logger.debug("Logged access event: %s %s", event_type, file_path)
    except sqlite3.Error as exc:
        logger.error("Failed to log access event for %s: %s", file_path, exc)


def get_all_files():
    try:
        with _connection() as conn:
            rows = [dict(r) for r in conn.cursor().execute(
                "SELECT * FROM file_metadata ORDER BY archival_urgency DESC"
            ).fetchall()]
        return rows
    except sqlite3.Error as exc:
        logger.error("Failed to fetch all files: %s", exc)
        return []


def get_high_urgency_files(threshold=0.6):
    try:
        with _connection() as conn:
            rows = [dict(r) for r in conn.cursor().execute("""
                SELECT * FROM file_metadata
                WHERE archival_urgency >= ?
                ORDER BY archival_urgency DESC
            """, (threshold,)).fetchall()]
        return rows
    except sqlite3.Error as exc:
        logger.error("Failed to fetch high urgency files: %s", exc)
        return []


def get_access_history(file_path):
    try:
        with _connection() as conn:
            rows = [dict(r) for r in conn.cursor().execute("""
                SELECT * FROM access_events
                WHERE file_path=?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (file_path,)).fetchall()]
        return rows
    except sqlite3.Error as exc:
        logger.error("Failed to fetch access history for %s: %s", file_path, exc)
        return []


def get_stats():
    defaults = {
        "total_files": 0,
        "urgent_files": 0,
        "total_size_mb": 0.0,
        "total_events": 0,
    }
    try:
        with _connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as total FROM file_metadata")
            total = c.fetchone()["total"]
            c.execute("SELECT COUNT(*) as urgent FROM file_metadata WHERE archival_urgency >= 0.6")
            urgent = c.fetchone()["urgent"]
            c.execute("SELECT SUM(size_bytes) as total_size FROM file_metadata")
            total_size = c.fetchone()["total_size"] or 0
            c.execute("SELECT COUNT(*) as events FROM access_events")
            events = c.fetchone()["events"]
        return {
            "total_files": total,
            "urgent_files": urgent,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_events": events,
        }
    except sqlite3.Error as exc:
        logger.error("Failed to fetch stats: %s", exc)
        return defaults
