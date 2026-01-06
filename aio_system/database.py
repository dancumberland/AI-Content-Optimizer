# ABOUTME: Database module for AIO optimization tracking
# ABOUTME: Logs changes, GSC metrics, and hypotheses for measurement

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "aio_optimizations.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the AIO optimization tracking database"""
    conn = get_connection()
    cursor = conn.cursor()

    # Main optimization experiments table (similar to CTR system)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aio_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            evaluated_at TIMESTAMP,

            -- Status
            status TEXT DEFAULT 'active'
        )
    """)

    # Individual changes within an experiment
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aio_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,

            change_type TEXT NOT NULL,
            element_name TEXT NOT NULL,
            element_content TEXT NOT NULL,
            insertion_point TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (experiment_id) REFERENCES aio_experiments(id)
        )
    """)

    # Structure score history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aio_structure_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO aio_experiments
        (page_url, page_slug, wp_post_id, changes_summary, hypothesis,
         pre_impressions, pre_clicks, pre_ctr, pre_position,
         pre_start_date, pre_end_date, pre_structure_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        page_url, page_slug, wp_post_id, changes_summary, hypothesis,
        pre_impressions, pre_clicks, pre_ctr, pre_position,
        pre_start_date, pre_end_date, pre_structure_score
    ))

    experiment_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return experiment_id


def log_change(
    experiment_id: int,
    change_type: str,
    element_name: str,
    element_content: str,
    insertion_point: str = None
) -> int:
    """Log an individual change within an experiment"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO aio_changes
        (experiment_id, change_type, element_name, element_content, insertion_point)
        VALUES (?, ?, ?, ?, ?)
    """, (experiment_id, change_type, element_name, element_content, insertion_point))

    change_id = cursor.lastrowid
    conn.commit()
    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE aio_experiments
        SET post_impressions = ?,
            post_clicks = ?,
            post_ctr = ?,
            post_position = ?,
            post_start_date = ?,
            post_end_date = ?,
            post_structure_score = ?,
            outcome = ?,
            outcome_notes = ?,
            evaluated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        post_impressions, post_clicks, post_ctr, post_position,
        post_start_date, post_end_date, post_structure_score,
        outcome, outcome_notes, experiment_id
    ))

    conn.commit()
    conn.close()


def get_experiment(experiment_id: int) -> Optional[Dict]:
    """Get a specific experiment"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM aio_experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_experiment_changes(experiment_id: int) -> List[Dict]:
    """Get all changes for an experiment"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_changes
        WHERE experiment_id = ?
        ORDER BY created_at
    """, (experiment_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_active_experiments() -> List[Dict]:
    """Get all active experiments awaiting evaluation"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_experiments
        WHERE status = 'active' AND evaluated_at IS NULL
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_experiments() -> List[Dict]:
    """Get all experiments"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_experiments
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_last_experiment_for_page(page_url: str) -> Optional[Dict]:
    """Get the most recent experiment for a page"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_experiments
        WHERE page_url = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (page_url,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_experiments_for_page(page_url: str) -> List[Dict]:
    """Get all experiments for a specific page"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_experiments
        WHERE page_url = ?
        ORDER BY created_at DESC
    """, (page_url,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_successful_patterns() -> List[Dict]:
    """Get patterns from successful experiments for learning"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT changes_summary, hypothesis, outcome_notes,
               COUNT(*) as count,
               AVG(CASE WHEN outcome = 'improved' THEN 1 ELSE 0 END) as success_rate
        FROM aio_experiments
        WHERE outcome IS NOT NULL
        GROUP BY changes_summary
        HAVING success_rate > 0.5
        ORDER BY count DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_experiments_by_change_type() -> List[Dict]:
    """Get performance statistics by change type"""
    conn = get_connection()
    cursor = conn.cursor()

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
    conn.close()

    results = []
    for row in rows:
        total = row["total_experiments"]
        success_rate = (row["improved"] / total * 100) if total > 0 else 0
        results.append({
            "element_name": row["element_name"],
            "total_experiments": total,
            "improved": row["improved"],
            "worsened": row["worsened"],
            "no_change": row["no_change"],
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO aio_structure_scores
        (page_url, page_slug, score_date, total_score,
         has_definition, has_list, has_question_headings,
         has_faq_schema, has_howto_schema, has_author_credentials,
         has_citations, has_summary_box)
        VALUES (?, ?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    conn.close()

    return score_id


def get_structure_score_history(page_url: str) -> List[Dict]:
    """Get structure score history for a page"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM aio_structure_scores
        WHERE page_url = ?
        ORDER BY score_date DESC
    """, (page_url,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


if __name__ == '__main__':
    init_database()
