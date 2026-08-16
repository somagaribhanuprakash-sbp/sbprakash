"""
OPS // TRACK — data layer
SQLite via sqlite3 stdlib (zero extra deps for the DB itself).
Single-user app, but structured so multi-user would just mean adding a user_id column.
"""
import sqlite3
import os
import json
import time
from contextlib import contextmanager

DB_PATH = os.environ.get("OPSTRACK_DB", os.path.join(os.path.dirname(__file__), "opstrack.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'other',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- 'adverk' | 'dsa'
    value REAL NOT NULL,
    date TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS security_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    desc TEXT,
    tech TEXT,
    status TEXT NOT NULL DEFAULT 'In Progress',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS restart_progress (
    item_key TEXT PRIMARY KEY,   -- e.g. p1-w0-d3
    done INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    desc TEXT,
    link TEXT,
    tech TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS about (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    bio TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity_days (
    day TEXT PRIMARY KEY   -- any date where the user did *something* (event/log/checkbox) -> streak calc
);

CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL   -- JSON: { "slots": [...], "days": [{"day": "Mon", "cells": [...]}] }
);
"""

DEFAULT_TIMETABLE = {
    "slots": ["09:30-10:30", "10:30-11:30", "11:30-12:30", "12:30-01:10", "01:10-02:10", "02:10-03:10", "03:10-04:10"],
    "days": [
        {"day": "Mon", "cells": ["", "", "", "", "", "", ""]},
        {"day": "Tue", "cells": ["", "", "", "", "", "", ""]},
        {"day": "Wed", "cells": ["", "", "", "", "", "", ""]},
        {"day": "Thu", "cells": ["", "", "", "", "", "", ""]},
        {"day": "Fri", "cells": ["", "", "", "", "", "", ""]},
        {"day": "Sat", "cells": ["", "", "", "", "", "", ""]},
    ],
}


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO about (id, name, email, bio) VALUES (1, '', '', '')")
        conn.execute(
            "INSERT OR IGNORE INTO timetable (id, data) VALUES (1, ?)",
            (json.dumps(DEFAULT_TIMETABLE),),
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def touch_activity(day: str):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO activity_days (day) VALUES (?)", (day,))
        conn.commit()


def now_ms():
    return int(time.time() * 1000)


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]
