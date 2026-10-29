"""
services/reports.py
SQL aggregates, report data, and CSV export helpers.
"""
import pandas as pd
from database.connection import execute_query, execute_write


# ── Summary Queries ───────────────────────────────────────────────────────────

def incidents_by_attack_type() -> pd.DataFrame:
    rows = execute_query(
        """
        SELECT
            COALESCE(at.attack_name, 'Unknown') AS attack_type,
            at.category,
            COUNT(i.incident_id) AS total,
            SUM(i.severity = 'Critical') AS critical_count
        FROM incidents i
        LEFT JOIN attack_types at ON i.attack_type_id = at.attack_type_id
        GROUP BY at.attack_name, at.category
        ORDER BY total DESC
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def incidents_by_severity() -> pd.DataFrame:
    rows = execute_query(
        """
        SELECT severity, COUNT(*) AS total
        FROM incidents
        GROUP BY severity
        ORDER BY FIELD(severity,'Critical','High','Medium','Low')
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def incidents_by_month() -> pd.DataFrame:
    rows = execute_query(
        """
        SELECT
            DATE_FORMAT(reported_at, '%Y-%m') AS month,
            COUNT(*) AS total,
            SUM(severity = 'Critical') AS critical
        FROM incidents
        GROUP BY month
        ORDER BY month
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def analyst_workload() -> pd.DataFrame:
    rows = execute_query(
        """
        SELECT
            u.full_name    AS analyst,
            al.specialization,
            COUNT(i.incident_id)               AS total_assigned,
            SUM(s.status_name = 'Resolved')    AS resolved,
            AVG(TIMESTAMPDIFF(HOUR, i.reported_at, i.resolved_at)) AS avg_resolve_hours
        FROM analysts al
        JOIN users u ON al.user_id = u.user_id
        LEFT JOIN incidents i ON i.assigned_analyst = al.analyst_id
        LEFT JOIN incident_status s ON i.status_id = s.status_id
        GROUP BY al.analyst_id, u.full_name, al.specialization
        ORDER BY total_assigned DESC
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def full_incident_report() -> pd.DataFrame:
    rows = execute_query(
        """
        SELECT
            i.incident_code,
            i.title,
            i.severity,
            s.status_name   AS status,
            at.attack_name  AS attack_type,
            u.full_name     AS reported_by,
            an.full_name    AS assigned_analyst,
            i.reported_at,
            i.resolved_at,
            TIMESTAMPDIFF(HOUR, i.reported_at, i.resolved_at) AS resolve_hours
        FROM incidents i
        JOIN incident_status s ON i.status_id = s.status_id
        JOIN users u           ON i.reported_by = u.user_id
        LEFT JOIN analysts al  ON i.assigned_analyst = al.analyst_id
        LEFT JOIN users an     ON al.user_id = an.user_id
        LEFT JOIN attack_types at ON i.attack_type_id = at.attack_type_id
        ORDER BY i.reported_at DESC
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def get_saved_reports() -> list:
    return execute_query(
        """
        SELECT r.report_id, r.report_title, r.generated_at, r.report_notes,
               u.full_name AS generated_by_name,
               i.incident_code
        FROM reports r
        JOIN users u ON r.generated_by = u.user_id
        LEFT JOIN incidents i ON r.incident_id = i.incident_id
        ORDER BY r.generated_at DESC
        """
    )


def save_report(
    report_title: str,
    generated_by: int,
    incident_id: int = None,
    notes: str = "",
) -> int:
    return execute_write(
        """
        INSERT INTO reports (report_title, generated_by, incident_id, report_notes)
        VALUES (:title, :by, :iid, :notes)
        """,
        {
            "title": report_title,
            "by": generated_by,
            "iid": incident_id or None,
            "notes": notes,
        },
    )


def df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
