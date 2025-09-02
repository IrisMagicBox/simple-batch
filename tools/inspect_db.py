#!/usr/bin/env python3
"""
Inspect the current SQLite database schema in this project.

Usage:
  python tools/inspect_db.py [db_path]

- If db_path is omitted, it uses settings.DATABASE_URL.
- Outputs tables, columns, foreign keys, indexes, views, triggers, and key PRAGMAs.
"""
from __future__ import annotations

import os
import sys
import sqlite3
from typing import List, Dict, Any, Tuple

# Try to load the project's default database path and project directory
try:
    import settings as _project_settings
    DEFAULT_DB_PATH = _project_settings.DATABASE_URL
    PROJECT_DIR = os.path.dirname(os.path.abspath(_project_settings.__file__))
except Exception:
    DEFAULT_DB_PATH = "batch_processor.db"
    # Fallback: assume this file is under <project>/tools
    PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetchall(conn: sqlite3.Connection, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def get_pragma(conn: sqlite3.Connection, name: str) -> Any:
    row = fetchall(conn, f"PRAGMA {name}")
    if not row:
        return None
    # Many PRAGMAs return a single-row, single-column result
    first = row[0]
    if len(first.keys()) == 1:
        return list(first)[0] and first[0]
    return dict(first)


def list_tables(conn: sqlite3.Connection) -> List[str]:
    rows = fetchall(
        conn,
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;",
    )
    return [r[0] for r in rows]


def list_views(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = fetchall(
        conn,
        "SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name;",
    )
    return [dict(r) for r in rows]


def list_triggers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = fetchall(
        conn,
        "SELECT name, tbl_name AS table_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name;",
    )
    return [dict(r) for r in rows]


def list_indexes(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    idx_rows = fetchall(conn, f"PRAGMA index_list('{table}')")
    indexes: List[Dict[str, Any]] = []
    for idx in idx_rows:
        idx_name = idx[1]
        unique = bool(idx[2])
        origin = idx[3]
        partial = bool(idx[4]) if len(idx.keys()) > 4 else False
        cols_rows = fetchall(conn, f"PRAGMA index_info('{idx_name}')")
        cols = [c[2] for c in cols_rows]
        indexes.append({
            "name": idx_name,
            "unique": unique,
            "origin": origin,
            "partial": partial,
            "columns": cols,
        })
    return indexes


def table_info(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    rows = fetchall(conn, f"PRAGMA table_info('{table}')")
    cols = []
    for r in rows:
        cols.append({
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": bool(r[3]),
            "dflt_value": r[4],
            "pk": bool(r[5]),
        })
    return cols


def foreign_keys(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    rows = fetchall(conn, f"PRAGMA foreign_key_list('{table}')")
    fks: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        # group by id (composite keys)
        fid = r[0]
        entry = fks.setdefault(fid, {
            "id": fid,
            "seq": [],
            "table": r[2],
            "on_update": r[5],
            "on_delete": r[6],
            "match": r[7],
            "from": [],
            "to": [],
        })
        entry["seq"].append(r[1])
        entry["from"].append(r[3])
        entry["to"].append(r[4])
    # flatten
    return list(fks.values())


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_key_values(items: List[Tuple[str, Any]]):
    width = max((len(k) for k, _ in items), default=0)
    for k, v in items:
        print(f"  {k.ljust(width)} : {v}")


def inspect_database(db_path: str):
    if not os.path.exists(db_path):
        print(f"[Error] Database file not found: {db_path}")
        sys.exit(1)

    conn = connect(db_path)
    try:
        # PRAGMAs
        print_header("Database PRAGMAs & Info")
        pragmas = [
            ("user_version", get_pragma(conn, "user_version")),
            ("journal_mode", get_pragma(conn, "journal_mode")),
            ("foreign_keys", get_pragma(conn, "foreign_keys")),
            ("wal_autocheckpoint", get_pragma(conn, "wal_autocheckpoint")),
            ("page_size", get_pragma(conn, "page_size")),
            ("cache_size", get_pragma(conn, "cache_size")),
        ]
        print_key_values(pragmas)

        # Tables
        tables = list_tables(conn)
        print_header(f"Tables ({len(tables)})")
        if not tables:
            print("  <no tables>")
        for t in tables:
            print(f"\n- {t}")
            cols = table_info(conn, t)
            if cols:
                print("  Columns:")
                for c in cols:
                    nn = "NOT NULL" if c["notnull"] else "NULL"
                    pk = " PK" if c["pk"] else ""
                    dv = f" DEFAULT {c['dflt_value']}" if c["dflt_value"] is not None else ""
                    print(f"    - {c['name']} {c['type']} {nn}{pk}{dv}")
            fks = foreign_keys(conn, t)
            if fks:
                print("  Foreign Keys:")
                for fk in fks:
                    pairs = ", ".join(f"{f} -> {to}" for f, to in zip(fk["from"], fk["to"]))
                    print(f"    - references {fk['table']} ( {pairs} ) ON UPDATE {fk['on_update']} ON DELETE {fk['on_delete']}")
            idxs = list_indexes(conn, t)
            if idxs:
                print("  Indexes:")
                for idx in idxs:
                    u = " UNIQUE" if idx["unique"] else ""
                    cols_str = ", ".join(idx["columns"]) or "<expr>"
                    origin = idx.get("origin", "")
                    part = " PARTIAL" if idx.get("partial") else ""
                    print(f"    - {idx['name']}{u}{part} ON ({cols_str}) [origin={origin}]")

        # Views
        views = list_views(conn)
        print_header(f"Views ({len(views)})")
        if not views:
            print("  <no views>")
        for v in views:
            print(f"- {v['name']}")
            if v.get("sql"):
                print("  SQL:")
                print("    " + v["sql"].replace("\n", "\n    "))

        # Triggers
        triggers = list_triggers(conn)
        print_header(f"Triggers ({len(triggers)})")
        if not triggers:
            print("  <no triggers>")
        for tr in triggers:
            print(f"- {tr['name']} ON {tr.get('table_name', '?')}")
            if tr.get("sql"):
                print("  SQL:")
                print("    " + tr["sql"].replace("\n", "\n    "))

    finally:
        conn.close()


def _resolve_db_path(input_path: str) -> str:
    """Resolve DB path with sensible fallbacks.

    Resolution order for relative paths:
      1) As given (relative to current working dir)
      2) Relative to PROJECT_DIR (where settings.py resides)
      3) Relative to this script's parent dir (same as PROJECT_DIR fallback)
    Returns the first existing path; if none exist, return candidate (2).
    """
    if os.path.isabs(input_path):
        return input_path

    cwd_candidate = os.path.abspath(input_path)
    project_candidate = os.path.abspath(os.path.join(PROJECT_DIR, input_path))
    script_parent_candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", input_path))

    for cand in (cwd_candidate, project_candidate, script_parent_candidate):
        if os.path.exists(cand):
            return cand

    # Prefer project directory location if none exist (for clearer error)
    return project_candidate


def main():
    raw_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    resolved = _resolve_db_path(raw_path)
    print_header("SQLite Schema Inspector")
    print_key_values([
        ("Input Path", raw_path),
        ("Resolved Path", resolved),
        ("Project Dir", PROJECT_DIR),
        ("Working Dir", os.getcwd()),
        ("Exists", os.path.exists(resolved)),
    ])
    inspect_database(resolved)


if __name__ == "__main__":
    main()
