"""
services/investigation.py
Evidence, comments, mitigation actions, and status history.
"""
from database.connection import execute_query, execute_write


# ── Evidence ──────────────────────────────────────────────────────────────────

def add_evidence(
    incident_id: int,
    evidence_type: str,
    file_name: str,
    file_hash: str,
    description: str,
    collected_by: int,
) -> int:
    return execute_write(
        """
        INSERT INTO evidence
            (incident_id, evidence_type, file_name, file_hash, description, collected_by)
        VALUES
            (:iid, :etype, :fname, :fhash, :desc, :by)
        """,
        {
            "iid": incident_id,
            "etype": evidence_type,
            "fname": file_name,
            "fhash": file_hash or None,
            "desc": description,
            "by": collected_by,
        },
    )


def get_evidence(incident_id: int) -> list:
    return execute_query(
        """
        SELECT e.*, u.full_name AS collected_by_name
        FROM evidence e
        JOIN users u ON e.collected_by = u.user_id
        WHERE e.incident_id = :iid
        ORDER BY e.collected_at DESC
        """,
        {"iid": incident_id},
    )


def delete_evidence(evidence_id: int) -> None:
    execute_write("DELETE FROM evidence WHERE evidence_id = :eid", {"eid": evidence_id})


# ── Mitigation Actions ────────────────────────────────────────────────────────

def add_mitigation_action(
    incident_id: int,
    action_description: str,
    performed_by: int,
) -> int:
    return execute_write(
        """
        INSERT INTO mitigation_actions
            (incident_id, action_description, performed_by)
        VALUES (:iid, :desc, :by)
        """,
        {"iid": incident_id, "desc": action_description, "by": performed_by},
    )


def get_mitigation_actions(incident_id: int) -> list:
    return execute_query(
        """
        SELECT m.*, u.full_name AS performed_by_name
        FROM mitigation_actions m
        JOIN users u ON m.performed_by = u.user_id
        WHERE m.incident_id = :iid
        ORDER BY m.created_at DESC
        """,
        {"iid": incident_id},
    )


def update_mitigation_status(
    action_id: int, new_status: str
) -> None:
    completed_sql = ", completed_at = NOW()" if new_status == "Completed" else ""
    execute_write(
        f"UPDATE mitigation_actions SET action_status = :s{completed_sql} WHERE action_id = :aid",
        {"s": new_status, "aid": action_id},
    )


# ── Comments ──────────────────────────────────────────────────────────────────

def add_comment(incident_id: int, user_id: int, comment_text: str) -> int:
    return execute_write(
        """
        INSERT INTO incident_comments (incident_id, user_id, comment_text)
        VALUES (:iid, :uid, :text)
        """,
        {"iid": incident_id, "uid": user_id, "text": comment_text},
    )


def get_comments(incident_id: int) -> list:
    return execute_query(
        """
        SELECT c.*, u.full_name AS author
        FROM incident_comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.incident_id = :iid
        ORDER BY c.created_at ASC
        """,
        {"iid": incident_id},
    )


# ── Status History ────────────────────────────────────────────────────────────

def get_status_history(incident_id: int) -> list:
    return execute_query(
        """
        SELECT
            h.changed_at,
            h.change_note,
            old_s.status_name AS old_status,
            new_s.status_name AS new_status,
            u.full_name       AS changed_by_name
        FROM incident_status_history h
        LEFT JOIN incident_status old_s ON h.old_status_id = old_s.status_id
        JOIN  incident_status new_s ON h.new_status_id = new_s.status_id
        JOIN  users u               ON h.changed_by = u.user_id
        WHERE h.incident_id = :iid
        ORDER BY h.changed_at ASC
        """,
        {"iid": incident_id},
    )


# ── Incident-Asset Links ──────────────────────────────────────────────────────

def link_asset(incident_id: int, asset_id: int, impact: str = "") -> None:
    execute_write(
        """
        INSERT IGNORE INTO incident_assets (incident_id, asset_id, impact_description)
        VALUES (:iid, :aid, :impact)
        """,
        {"iid": incident_id, "aid": asset_id, "impact": impact},
    )


def unlink_asset(incident_id: int, asset_id: int) -> None:
    execute_write(
        "DELETE FROM incident_assets WHERE incident_id=:iid AND asset_id=:aid",
        {"iid": incident_id, "aid": asset_id},
    )


def get_incident_assets(incident_id: int) -> list:
    return execute_query(
        """
        SELECT a.*, ia.impact_description
        FROM incident_assets ia
        JOIN assets a ON ia.asset_id = a.asset_id
        WHERE ia.incident_id = :iid
        """,
        {"iid": incident_id},
    )


# ── Incident-Vulnerability Links ─────────────────────────────────────────────

def link_vulnerability(incident_id: int, vuln_id: int) -> None:
    execute_write(
        """
        INSERT IGNORE INTO incident_vulnerabilities (incident_id, vulnerability_id)
        VALUES (:iid, :vid)
        """,
        {"iid": incident_id, "vid": vuln_id},
    )


def unlink_vulnerability(incident_id: int, vuln_id: int) -> None:
    execute_write(
        "DELETE FROM incident_vulnerabilities WHERE incident_id=:iid AND vulnerability_id=:vid",
        {"iid": incident_id, "vid": vuln_id},
    )


def get_incident_vulnerabilities(incident_id: int) -> list:
    return execute_query(
        """
        SELECT v.*
        FROM incident_vulnerabilities iv
        JOIN vulnerabilities v ON iv.vulnerability_id = v.vulnerability_id
        WHERE iv.incident_id = :iid
        """,
        {"iid": incident_id},
    )
