"""
services/incidents.py
Create, retrieve, assign, and update incidents.
"""
from datetime import datetime
from database.connection import execute_query, execute_write, get_engine
from sqlalchemy import text


# ── Code generation ──────────────────────────────────────────────────────────

def _next_incident_code() -> str:
    """Generate INC-YYYYMMDD-NNNN style codes atomically."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INC-{today}-"
    rows = execute_query(
        "SELECT incident_code FROM incidents WHERE incident_code LIKE :p ORDER BY incident_code DESC LIMIT 1",
        {"p": f"{prefix}%"},
    )
    if rows:
        last_seq = int(rows[0]["incident_code"].split("-")[-1])
        seq = last_seq + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_incident(
    title: str,
    description: str,
    reported_by: int,
    status_id: int,
    severity: str,
    attack_type_id: int = None,
) -> int:
    """Insert a new incident and return its incident_id."""
    code = _next_incident_code()
    incident_id = execute_write(
        """
        INSERT INTO incidents
            (incident_code, title, description, reported_by,
             attack_type_id, status_id, severity)
        VALUES
            (:code, :title, :desc, :reported_by,
             :attack_type_id, :status_id, :severity)
        """,
        {
            "code": code,
            "title": title,
            "desc": description,
            "reported_by": reported_by,
            "attack_type_id": attack_type_id,
            "status_id": status_id,
            "severity": severity,
        },
    )
    # Record initial status history
    execute_write(
        """
        INSERT INTO incident_status_history
            (incident_id, old_status_id, new_status_id, changed_by, change_note)
        VALUES (:iid, NULL, :new_sid, :by, 'Incident created')
        """,
        {"iid": incident_id, "new_sid": status_id, "by": reported_by},
    )
    return incident_id


def get_incidents(
    status_filter: str = None,
    severity_filter: str = None,
    search: str = None,
    limit: int = 500,
) -> list:
    """Return incidents with joined status, analyst, and attack type names."""
    where_clauses = []
    params = {"limit": limit}

    if status_filter and status_filter != "All":
        where_clauses.append("s.status_name = :status")
        params["status"] = status_filter

    if severity_filter and severity_filter != "All":
        where_clauses.append("i.severity = :severity")
        params["severity"] = severity_filter

    if search:
        where_clauses.append(
            "(i.title LIKE :search OR i.incident_code LIKE :search)"
        )
        params["search"] = f"%{search}%"

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = f"""
        SELECT
            i.incident_id,
            i.incident_code,
            i.title,
            i.severity,
            i.reported_at,
            i.resolved_at,
            s.status_name,
            u.full_name   AS reporter,
            a.full_name   AS analyst_name,
            at.attack_name
        FROM incidents i
        JOIN incident_status s ON i.status_id = s.status_id
        JOIN users u           ON i.reported_by = u.user_id
        LEFT JOIN analysts al  ON i.assigned_analyst = al.analyst_id
        LEFT JOIN users a      ON al.user_id = a.user_id
        LEFT JOIN attack_types at ON i.attack_type_id = at.attack_type_id
        {where_sql}
        ORDER BY i.reported_at DESC
        LIMIT :limit
    """
    return execute_query(sql, params)


def get_incident_detail(incident_id: int) -> dict:
    """Return a single incident with all related data."""
    rows = execute_query(
        """
        SELECT
            i.*,
            s.status_name,
            u.full_name   AS reporter,
            a.full_name   AS analyst_name,
            al.analyst_id,
            at.attack_name
        FROM incidents i
        JOIN incident_status s ON i.status_id = s.status_id
        JOIN users u           ON i.reported_by = u.user_id
        LEFT JOIN analysts al  ON i.assigned_analyst = al.analyst_id
        LEFT JOIN users a      ON al.user_id = a.user_id
        LEFT JOIN attack_types at ON i.attack_type_id = at.attack_type_id
        WHERE i.incident_id = :iid
        """,
        {"iid": incident_id},
    )
    return dict(rows[0]) if rows else None


def assign_analyst(incident_id: int, analyst_id: int, changed_by: int) -> None:
    """Assign an analyst and update status to Assigned."""
    current = get_incident_detail(incident_id)
    if not current:
        return

    # Get "Assigned" status_id
    status_rows = execute_query(
        "SELECT status_id FROM incident_status WHERE status_name = 'Assigned'"
    )
    assigned_status_id = status_rows[0]["status_id"] if status_rows else current["status_id"]

    execute_write(
        """
        UPDATE incidents
        SET assigned_analyst = :analyst_id, status_id = :status_id
        WHERE incident_id = :iid
        """,
        {"analyst_id": analyst_id, "status_id": assigned_status_id, "iid": incident_id},
    )

    execute_write(
        """
        INSERT INTO incident_status_history
            (incident_id, old_status_id, new_status_id, changed_by, change_note)
        VALUES (:iid, :old, :new, :by, 'Analyst assigned')
        """,
        {
            "iid": incident_id,
            "old": current["status_id"],
            "new": assigned_status_id,
            "by": changed_by,
        },
    )


def update_status(
    incident_id: int,
    new_status_id: int,
    changed_by: int,
    note: str = "",
) -> None:
    """Change the incident status and append a history record."""
    current = get_incident_detail(incident_id)
    if not current:
        return

    # Mark resolved_at when closing
    resolved_sql_fragment = ""
    params_extra = {}
    if new_status_id:
        status_rows = execute_query(
            "SELECT status_name FROM incident_status WHERE status_id = :sid",
            {"sid": new_status_id},
        )
        if status_rows and status_rows[0]["status_name"] in ("Resolved", "Closed"):
            resolved_sql_fragment = ", resolved_at = NOW()"

    execute_write(
        f"UPDATE incidents SET status_id = :sid{resolved_sql_fragment} WHERE incident_id = :iid",
        {"sid": new_status_id, "iid": incident_id, **params_extra},
    )

    execute_write(
        """
        INSERT INTO incident_status_history
            (incident_id, old_status_id, new_status_id, changed_by, change_note)
        VALUES (:iid, :old, :new, :by, :note)
        """,
        {
            "iid": incident_id,
            "old": current["status_id"],
            "new": new_status_id,
            "by": changed_by,
            "note": note or "Status updated",
        },
    )


# ── Reference data helpers ────────────────────────────────────────────────────

def get_all_statuses() -> list:
    return execute_query("SELECT status_id, status_name FROM incident_status ORDER BY status_id")


def get_all_attack_types() -> list:
    return execute_query(
        "SELECT attack_type_id, attack_name, category FROM attack_types ORDER BY attack_name"
    )


def get_all_analysts() -> list:
    return execute_query(
        """
        SELECT al.analyst_id, u.full_name, u.username, al.specialization
        FROM analysts al JOIN users u ON al.user_id = u.user_id
        ORDER BY u.full_name
        """
    )


def get_all_users() -> list:
    return execute_query(
        "SELECT user_id, full_name, username, role FROM users ORDER BY full_name"
    )


# ── Dashboard metrics ─────────────────────────────────────────────────────────

def get_dashboard_metrics() -> dict:
    rows = execute_query(
        """
        SELECT
            COUNT(*)                                            AS total,
            SUM(s.status_name NOT IN ('Resolved','Closed'))    AS open_count,
            SUM(i.severity = 'Critical')                       AS critical,
            SUM(s.status_name IN ('Resolved','Closed'))        AS resolved
        FROM incidents i
        JOIN incident_status s ON i.status_id = s.status_id
        """
    )
    row = rows[0] if rows else {}
    return {
        "total":    int(row.get("total", 0) or 0),
        "open":     int(row.get("open_count", 0) or 0),
        "critical": int(row.get("critical", 0) or 0),
        "resolved": int(row.get("resolved", 0) or 0),
    }


def get_severity_distribution() -> list:
    return execute_query(
        """
        SELECT severity, COUNT(*) AS cnt
        FROM incidents
        GROUP BY severity
        ORDER BY FIELD(severity,'Critical','High','Medium','Low')
        """
    )


def get_status_distribution() -> list:
    return execute_query(
        """
        SELECT s.status_name, COUNT(i.incident_id) AS cnt
        FROM incident_status s
        LEFT JOIN incidents i ON i.status_id = s.status_id
        GROUP BY s.status_name
        ORDER BY s.status_id
        """
    )


def get_recent_incidents(n: int = 5) -> list:
    return execute_query(
        """
        SELECT i.incident_code, i.title, i.severity, s.status_name, i.reported_at
        FROM incidents i
        JOIN incident_status s ON i.status_id = s.status_id
        ORDER BY i.reported_at DESC
        LIMIT :n
        """,
        {"n": n},
    )
