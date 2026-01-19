# ABOUTME: Database module for AIO optimization tracking
# ABOUTME: Supports both SQLite (local dev) and PostgreSQL via Supabase (CI/production)

import os
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager

# Detect database backend
DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3
    from pathlib import Path
    # Database path - only used for SQLite
    DB_PATH = Path(__file__).parent.parent.parent / "aio_optimizations.db"


@contextmanager
def get_connection():
    """Get database connection - PostgreSQL if SUPABASE_DATABASE_URL is set, else SQLite"""
    if USE_POSTGRES:
        # Force IPv4 for GitHub Actions compatibility
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(DATABASE_URL)
        hostname = parsed.hostname

        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or 5432, socket.AF_INET)
            if addr_info:
                ipv4_addr = addr_info[0][4][0]
                conn = psycopg2.connect(DATABASE_URL, hostaddr=ipv4_addr)
            else:
                conn = psycopg2.connect(DATABASE_URL)
        except (socket.gaierror, IndexError):
            conn = psycopg2.connect(DATABASE_URL)

        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def _get_cursor(conn):
    """Get appropriate cursor for the database backend"""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def _placeholder():
    """Return the correct placeholder for the database backend"""
    return "%s" if USE_POSTGRES else "?"


def _row_to_dict(row):
    """Convert a row to a dictionary"""
    if row is None:
        return None
    return dict(row)


def init_database():
    """Initialize the AIO optimization tracking database"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        # PostgreSQL uses SERIAL, SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT
        if USE_POSTGRES:
            id_type = "SERIAL PRIMARY KEY"
            timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
        else:
            id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            timestamp_default = "DEFAULT CURRENT_TIMESTAMP"

        # Main optimization experiments table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS aio_experiments (
                id {id_type},

                -- Page identification
                page_url TEXT NOT NULL,
                page_slug TEXT NOT NULL,
                wp_post_id INTEGER NOT NULL,

                -- Pre-optimization metrics (from GSC)
                pre_impressions INTEGER,
                pre_clicks INTEGER,
                pre_ctr REAL,
                pre_position REAL,
                pre_start_date TEXT,
                pre_end_date TEXT,

                -- Structure score before optimization
                pre_structure_score INTEGER,

                -- Changes made
                changes_summary TEXT NOT NULL,
                hypothesis TEXT NOT NULL,

                -- Post-optimization metrics (filled in later)
                post_impressions INTEGER,
                post_clicks INTEGER,
                post_ctr REAL,
                post_position REAL,
                post_start_date TEXT,
                post_end_date TEXT,
                post_structure_score INTEGER,

                -- Outcome
                outcome TEXT,
                outcome_notes TEXT,

                -- Timestamps
                created_at TIMESTAMP {timestamp_default},
                evaluated_at TIMESTAMP,

                -- Status
                status TEXT DEFAULT 'active'
            )
        """)

        # Individual changes within an experiment
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS aio_changes (
                id {id_type},
                experiment_id INTEGER NOT NULL,

                change_type TEXT NOT NULL,
                element_name TEXT NOT NULL,
                element_content TEXT NOT NULL,
                insertion_point TEXT,

                created_at TIMESTAMP {timestamp_default},

                FOREIGN KEY (experiment_id) REFERENCES aio_experiments(id)
            )
        """)

        # Structure score history
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS aio_structure_scores (
                id {id_type},
                page_url TEXT NOT NULL,
                page_slug TEXT NOT NULL,
                score_date DATE NOT NULL,
                total_score INTEGER NOT NULL,
                has_definition INTEGER,
                has_list INTEGER,
                has_question_headings INTEGER,
                has_faq_schema INTEGER,
                has_howto_schema INTEGER,
                has_author_credentials INTEGER,
                has_citations INTEGER,
                has_summary_box INTEGER,
                created_at TIMESTAMP {timestamp_default}
            )
        """)

        conn.commit()
        db_location = "PostgreSQL (Supabase)" if USE_POSTGRES else f"SQLite ({DB_PATH})"
        print(f"Database initialized at: {db_location}")


def create_experiment(
    page_url: str,
    page_slug: str,
    wp_post_id: int,
    changes_summary: str,
    hypothesis: str,
    pre_impressions: int = None,
    pre_clicks: int = None,
    pre_ctr: float = None,
    pre_position: float = None,
    pre_start_date: str = None,
    pre_end_date: str = None,
    pre_structure_score: int = None
) -> int:
    """Create a new AIO optimization experiment"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute(f"""
                INSERT INTO aio_experiments
                (page_url, page_slug, wp_post_id, changes_summary, hypothesis,
                 pre_impressions, pre_clicks, pre_ctr, pre_position,
                 pre_start_date, pre_end_date, pre_structure_score)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id
            """, (
                page_url, page_slug, wp_post_id, changes_summary, hypothesis,
                pre_impressions, pre_clicks, pre_ctr, pre_position,
                pre_start_date, pre_end_date, pre_structure_score
            ))
            experiment_id = cursor.fetchone()['id']
        else:
            cursor.execute(f"""
                INSERT INTO aio_experiments
                (page_url, page_slug, wp_post_id, changes_summary, hypothesis,
                 pre_impressions, pre_clicks, pre_ctr, pre_position,
                 pre_start_date, pre_end_date, pre_structure_score)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                page_url, page_slug, wp_post_id, changes_summary, hypothesis,
                pre_impressions, pre_clicks, pre_ctr, pre_position,
                pre_start_date, pre_end_date, pre_structure_score
            ))
            experiment_id = cursor.lastrowid

        conn.commit()

    return experiment_id


def log_change(
    experiment_id: int,
    change_type: str,
    element_name: str,
    element_content: str,
    insertion_point: str = None
) -> int:
    """Log an individual change within an experiment"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute(f"""
                INSERT INTO aio_changes
                (experiment_id, change_type, element_name, element_content, insertion_point)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id
            """, (experiment_id, change_type, element_name, element_content, insertion_point))
            change_id = cursor.fetchone()['id']
        else:
            cursor.execute(f"""
                INSERT INTO aio_changes
                (experiment_id, change_type, element_name, element_content, insertion_point)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (experiment_id, change_type, element_name, element_content, insertion_point))
            change_id = cursor.lastrowid

        conn.commit()

    return change_id


def update_experiment_post_metrics(
    experiment_id: int,
    post_impressions: int,
    post_clicks: int,
    post_ctr: float,
    post_position: float,
    post_start_date: str,
    post_end_date: str,
    post_structure_score: int = None,
    outcome: str = None,
    outcome_notes: str = None
):
    """Update experiment with post-optimization metrics"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"""
            UPDATE aio_experiments
            SET post_impressions = {ph},
                post_clicks = {ph},
                post_ctr = {ph},
                post_position = {ph},
                post_start_date = {ph},
                post_end_date = {ph},
                post_structure_score = {ph},
                outcome = {ph},
                outcome_notes = {ph},
                evaluated_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (
            post_impressions, post_clicks, post_ctr, post_position,
            post_start_date, post_end_date, post_structure_score,
            outcome, outcome_notes, experiment_id
        ))

        conn.commit()


def get_experiment(experiment_id: int) -> Optional[Dict]:
    """Get a specific experiment"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"SELECT * FROM aio_experiments WHERE id = {ph}", (experiment_id,))
        row = cursor.fetchone()

    return _row_to_dict(row)


def get_experiment_changes(experiment_id: int) -> List[Dict]:
    """Get all changes for an experiment"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"""
            SELECT * FROM aio_changes
            WHERE experiment_id = {ph}
            ORDER BY created_at
        """, (experiment_id,))

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_active_experiments() -> List[Dict]:
    """Get all active experiments awaiting evaluation"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute("""
            SELECT * FROM aio_experiments
            WHERE status = 'active' AND evaluated_at IS NULL
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_all_experiments() -> List[Dict]:
    """Get all experiments"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute("""
            SELECT * FROM aio_experiments
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_last_experiment_for_page(page_url: str) -> Optional[Dict]:
    """Get the most recent experiment for a page"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"""
            SELECT * FROM aio_experiments
            WHERE page_url = {ph}
            ORDER BY created_at DESC
            LIMIT 1
        """, (page_url,))

        row = cursor.fetchone()

    return _row_to_dict(row)


def get_experiments_for_page(page_url: str) -> List[Dict]:
    """Get all experiments for a specific page"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"""
            SELECT * FROM aio_experiments
            WHERE page_url = {ph}
            ORDER BY created_at DESC
        """, (page_url,))

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_successful_patterns() -> List[Dict]:
    """Get patterns from successful experiments for learning"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute("""
            SELECT changes_summary, hypothesis, outcome_notes,
                   COUNT(*) as count,
                   AVG(CASE WHEN outcome = 'improved' THEN 1 ELSE 0 END) as success_rate
            FROM aio_experiments
            WHERE outcome IS NOT NULL
            GROUP BY changes_summary
            HAVING AVG(CASE WHEN outcome = 'improved' THEN 1 ELSE 0 END) > 0.5
            ORDER BY COUNT(*) DESC
        """)

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_experiments_by_change_type() -> List[Dict]:
    """Get performance statistics by change type"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute("""
            SELECT
                c.element_name,
                COUNT(*) as total_experiments,
                SUM(CASE WHEN e.outcome = 'improved' THEN 1 ELSE 0 END) as improved,
                SUM(CASE WHEN e.outcome = 'worsened' THEN 1 ELSE 0 END) as worsened,
                SUM(CASE WHEN e.outcome = 'no_change' THEN 1 ELSE 0 END) as no_change
            FROM aio_changes c
            JOIN aio_experiments e ON c.experiment_id = e.id
            WHERE e.outcome IS NOT NULL
            GROUP BY c.element_name
        """)

        rows = cursor.fetchall()

    results = []
    for row in rows:
        row_dict = _row_to_dict(row)
        total = row_dict["total_experiments"]
        success_rate = (row_dict["improved"] / total * 100) if total > 0 else 0
        results.append({
            "element_name": row_dict["element_name"],
            "total_experiments": total,
            "improved": row_dict["improved"],
            "worsened": row_dict["worsened"],
            "no_change": row_dict["no_change"],
            "success_rate": success_rate,
        })

    return results


def store_structure_score(
    page_url: str,
    page_slug: str,
    total_score: int,
    elements: Dict,
) -> int:
    """Store a structure score snapshot"""
    ph = _placeholder()

    # SQLite uses date('now'), PostgreSQL uses CURRENT_DATE
    date_func = "CURRENT_DATE" if USE_POSTGRES else "date('now')"

    with get_connection() as conn:
        cursor = _get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute(f"""
                INSERT INTO aio_structure_scores
                (page_url, page_slug, score_date, total_score,
                 has_definition, has_list, has_question_headings,
                 has_faq_schema, has_howto_schema, has_author_credentials,
                 has_citations, has_summary_box)
                VALUES ({ph}, {ph}, {date_func}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id
            """, (
                page_url,
                page_slug,
                total_score,
                elements.get("has_definition_block", {}).get("present", False),
                elements.get("has_numbered_list", {}).get("present", False) or
                elements.get("has_bulleted_list", {}).get("present", False),
                elements.get("has_question_headings", {}).get("present", False),
                elements.get("has_faq_schema", {}).get("present", False),
                elements.get("has_howto_schema", {}).get("present", False),
                False,  # has_author_credentials - not currently tracked
                elements.get("has_citations", {}).get("present", False),
                False,  # has_summary_box - not currently tracked
            ))
            score_id = cursor.fetchone()['id']
        else:
            cursor.execute(f"""
                INSERT INTO aio_structure_scores
                (page_url, page_slug, score_date, total_score,
                 has_definition, has_list, has_question_headings,
                 has_faq_schema, has_howto_schema, has_author_credentials,
                 has_citations, has_summary_box)
                VALUES ({ph}, {ph}, {date_func}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                page_url,
                page_slug,
                total_score,
                elements.get("has_definition_block", {}).get("present", False),
                elements.get("has_numbered_list", {}).get("present", False) or
                elements.get("has_bulleted_list", {}).get("present", False),
                elements.get("has_question_headings", {}).get("present", False),
                elements.get("has_faq_schema", {}).get("present", False),
                elements.get("has_howto_schema", {}).get("present", False),
                False,  # has_author_credentials - not currently tracked
                elements.get("has_citations", {}).get("present", False),
                False,  # has_summary_box - not currently tracked
            ))
            score_id = cursor.lastrowid

        conn.commit()

    return score_id


def get_structure_score_history(page_url: str) -> List[Dict]:
    """Get structure score history for a page"""
    ph = _placeholder()
    with get_connection() as conn:
        cursor = _get_cursor(conn)

        cursor.execute(f"""
            SELECT * FROM aio_structure_scores
            WHERE page_url = {ph}
            ORDER BY score_date DESC
        """, (page_url,))

        rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


if __name__ == '__main__':
    init_database()
