"""
pages/2_Incidents.py — Incident list, creation, and detail view.
"""
import streamlit as st
import pandas as pd
from services.auth import is_authenticated
from services.incidents import (
    create_incident, get_incidents, get_incident_detail,
    assign_analyst, update_status,
    get_all_statuses, get_all_attack_types, get_all_analysts, get_all_users,
)

st.set_page_config(page_title="Incidents | CyberSec", page_icon="🚨", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# 🚨 Incident Management")
st.caption("Create, filter, assign, and update cybersecurity incidents.")
st.divider()

# ── Helper: system user for demo actions ──────────────────────────────────────
def _get_demo_user_id() -> int:
    """Return the first user's ID, or 0 if none exist."""
    users = get_all_users()
    return users[0]["user_id"] if users else 0

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_list, tab_new, tab_detail = st.tabs(["📋  Incident List", "➕  New Incident", "🔍  Incident Detail"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — INCIDENT LIST
# ═══════════════════════════════════════════════════════════════════════════════
with tab_list:
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("🔍 Search by title or code", placeholder="INC-2024 or Phishing…")
    with col_f2:
        statuses = ["All"] + [r["status_name"] for r in get_all_statuses()]
        status_filter = st.selectbox("Status", statuses)
    with col_f3:
        severity_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])

    rows = get_incidents(
        status_filter=status_filter if status_filter != "All" else None,
        severity_filter=severity_filter if severity_filter != "All" else None,
        search=search or None,
    )

    if not rows:
        st.info("No incidents found. Use **New Incident** to create one.")
    else:
        df = pd.DataFrame([dict(r) for r in rows])

        # Severity colour column
        def sev_badge(s):
            colors = {"Critical": "🔴", "High": "🟠", "Medium": "🔵", "Low": "🟢"}
            return f"{colors.get(s, '⚪')} {s}"

        df["severity_display"] = df["severity"].apply(sev_badge)

        display_cols = ["incident_code", "title", "severity_display", "status_name",
                        "reporter", "analyst_name", "attack_name", "reported_at"]
        display_cols = [c for c in display_cols if c in df.columns]

        st.dataframe(
            df[display_cols].rename(columns={
                "incident_code": "Code", "title": "Title",
                "severity_display": "Severity", "status_name": "Status",
                "reporter": "Reporter", "analyst_name": "Analyst",
                "attack_name": "Attack Type", "reported_at": "Reported At",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing {len(rows)} incident(s).")

        # Quick-select into detail tab
        st.markdown("**View detail** → enter an Incident Code in the Detail tab.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — NEW INCIDENT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_new:
    users = get_all_users()
    if not users:
        st.warning(
            "⚠️ No users in the database. Go to **Administration** → Create User first."
        )
        st.stop()

    attack_types = get_all_attack_types()
    statuses_raw = get_all_statuses()
    open_status = next((s for s in statuses_raw if s["status_name"] == "Open"), statuses_raw[0])

    with st.form("new_incident_form", clear_on_submit=True):
        st.subheader("Report New Incident")
        title = st.text_input("Incident Title *", placeholder="Phishing email targeting finance team")
        description = st.text_area("Description", placeholder="Detailed description of the incident…", height=120)

        col1, col2 = st.columns(2)
        with col1:
            reporter_options = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users}
            reporter_label = st.selectbox("Reported By *", list(reporter_options.keys()))
            severity = st.selectbox("Severity *", ["Critical", "High", "Medium", "Low"], index=2)

        with col2:
            attack_options = {"— None —": None}
            attack_options.update({f"{a['attack_name']} ({a['category']})": a["attack_type_id"] for a in attack_types})
            attack_label = st.selectbox("Attack Type", list(attack_options.keys()))

        submitted = st.form_submit_button("🚨 Create Incident", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Title is required.")
        else:
            try:
                iid = create_incident(
                    title=title.strip(),
                    description=description.strip(),
                    reported_by=reporter_options[reporter_label],
                    status_id=open_status["status_id"],
                    severity=severity,
                    attack_type_id=attack_options[attack_label],
                )
                detail = get_incident_detail(iid)
                st.success(
                    f"✅ Incident **{detail['incident_code']}** created successfully! "
                    f"View it in the **Incident Detail** tab."
                )
            except Exception as e:
                st.error(f"Failed to create incident: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INCIDENT DETAIL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_detail:
    code_input = st.text_input("Enter Incident Code", placeholder="INC-20240101-0001")

    if code_input.strip():
        rows = get_incidents(search=code_input.strip())
        matched = [r for r in rows if r["incident_code"].upper() == code_input.strip().upper()]

        if not matched:
            st.error("Incident not found.")
        else:
            inc = get_incident_detail(matched[0]["incident_id"])

            # Header
            sev_colors = {"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#10B981"}
            st.markdown(
                f"""
                <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem">
                  <h3 style="margin:0;color:#1E3A5F">{inc['incident_code']} — {inc['title']}</h3>
                  <span style="background:{sev_colors.get(inc['severity'],'#ccc')};color:#fff;
                        padding:2px 12px;border-radius:20px;font-size:.85rem;font-weight:700">
                    {inc['severity']}
                  </span>
                  &nbsp;<span style="color:#64748B">Status: <b>{inc['status_name']}</b></span>
                  &nbsp;|&nbsp;<span style="color:#64748B">Reporter: <b>{inc['reporter']}</b></span>
                  &nbsp;|&nbsp;<span style="color:#64748B">Reported: <b>{inc['reported_at']}</b></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if inc.get("description"):
                st.markdown(f"**Description:** {inc['description']}")

            st.divider()

            action_col1, action_col2 = st.columns(2)

            # ── Assign Analyst ────────────────────────────────────────────────
            with action_col1:
                st.subheader("👤 Assign Analyst")
                analysts = get_all_analysts()
                users_all = get_all_users()

                if not analysts:
                    st.info("No analysts found. Create one in **Administration**.")
                else:
                    with st.form(f"assign_form_{inc['incident_id']}"):
                        analyst_opts = {
                            f"{a['full_name']} – {a['specialization'] or 'General'}": a["analyst_id"]
                            for a in analysts
                        }
                        sel_analyst = st.selectbox("Select Analyst", list(analyst_opts.keys()))
                        changer_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users_all}
                        sel_changer = st.selectbox("Action performed by", list(changer_opts.keys()))

                        if st.form_submit_button("Assign", use_container_width=True):
                            try:
                                assign_analyst(
                                    inc["incident_id"],
                                    analyst_opts[sel_analyst],
                                    changer_opts[sel_changer],
                                )
                                st.success("✅ Analyst assigned successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            # ── Update Status ─────────────────────────────────────────────────
            with action_col2:
                st.subheader("🔄 Update Status")
                statuses_all = get_all_statuses()
                users_all2 = get_all_users()

                with st.form(f"status_form_{inc['incident_id']}"):
                    status_opts = {s["status_name"]: s["status_id"] for s in statuses_all}
                    sel_status = st.selectbox(
                        "New Status",
                        list(status_opts.keys()),
                        index=list(status_opts.keys()).index(inc["status_name"])
                        if inc["status_name"] in status_opts else 0,
                    )
                    changer2_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users_all2}
                    sel_changer2 = st.selectbox("Changed by", list(changer2_opts.keys()))
                    note = st.text_input("Change Note (optional)")

                    if st.form_submit_button("Update Status", use_container_width=True):
                        try:
                            update_status(
                                inc["incident_id"],
                                status_opts[sel_status],
                                changer2_opts[sel_changer2],
                                note,
                            )
                            st.success(f"✅ Status updated to **{sel_status}**!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("Enter an incident code above (e.g. `INC-20240101-0001`) to view its details.")
