"""
pages/4_Investigation.py — Evidence, comments, mitigation, and status history.
"""
import streamlit as st
import pandas as pd
from services.auth import is_authenticated
from services.incidents import get_incidents, get_incident_detail, get_all_users
from services.investigation import (
    add_evidence, get_evidence, delete_evidence,
    add_mitigation_action, get_mitigation_actions, update_mitigation_status,
    add_comment, get_comments,
    get_status_history,
)

st.set_page_config(page_title="Investigation | CyberSec", page_icon="🔬", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# 🔬 Investigation Workbench")
st.caption("Collect evidence, track mitigation actions, and review the full incident timeline.")
st.divider()

# ── Select incident ───────────────────────────────────────────────────────────
incidents = get_incidents()
if not incidents:
    st.info("No incidents found. Create one in the **Incidents** page first.")
    st.stop()

inc_opts = {f"{r['incident_code']} — {r['title']} [{r['status_name']}]": r["incident_id"] for r in incidents}
sel_label = st.selectbox("🔎 Select Incident", list(inc_opts.keys()))
sel_id    = inc_opts[sel_label]
inc       = get_incident_detail(sel_id)

sev_colors = {"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#10B981"}
st.markdown(
    f"""
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:1rem 1.5rem;margin-bottom:1rem">
      <b>{inc['incident_code']}</b> — {inc['title']}
      &nbsp;|&nbsp;
      <span style="background:{sev_colors.get(inc['severity'],'#ccc')};color:#fff;
            padding:1px 10px;border-radius:20px;font-size:.8rem">{inc['severity']}</span>
      &nbsp;|&nbsp; Status: <b>{inc['status_name']}</b>
      &nbsp;|&nbsp; Analyst: <b>{inc['analyst_name'] or '— Unassigned —'}</b>
    </div>
    """,
    unsafe_allow_html=True,
)

users = get_all_users()
user_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users}

tab_ev, tab_mit, tab_com, tab_hist = st.tabs(
    ["📁 Evidence", "🛡️ Mitigation Actions", "💬 Comments", "🕰️ Status History"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EVIDENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ev:
    col_elist, col_eform = st.columns([3, 2])

    with col_elist:
        st.subheader("Collected Evidence")
        evidence = get_evidence(sel_id)
        if evidence:
            df_e = pd.DataFrame([dict(r) for r in evidence])
            cols = ["evidence_id", "evidence_type", "file_name", "file_hash", "description",
                    "collected_by_name", "collected_at"]
            cols = [c for c in cols if c in df_e.columns]
            st.dataframe(df_e[cols], use_container_width=True, hide_index=True)

            with st.expander("🗑️ Delete Evidence"):
                ev_del_opts = {f"#{e['evidence_id']} {e['evidence_type']} – {e['file_name'] or 'no file'}": e["evidence_id"] for e in evidence}
                sel_del = st.selectbox("Select evidence to delete", list(ev_del_opts.keys()))
                if st.button("Delete selected evidence", type="secondary"):
                    delete_evidence(ev_del_opts[sel_del])
                    st.success("Evidence deleted.")
                    st.rerun()
        else:
            st.info("No evidence collected yet.")

    with col_eform:
        st.subheader("Add Evidence")
        if not users:
            st.warning("No users in database. Create one in Administration.")
        else:
            with st.form("add_evidence_form", clear_on_submit=True):
                e_type = st.selectbox("Evidence Type", [
                    "Log File", "Screenshot", "Network Capture",
                    "Malware Sample", "Email Header", "Memory Dump",
                    "Forensic Image", "Other",
                ])
                e_fname = st.text_input("File Name", placeholder="firewall_log_2024.txt")
                e_hash  = st.text_input("File Hash (SHA-256)", placeholder="a3f5…")
                e_desc  = st.text_area("Description", height=100)
                e_by_label = st.selectbox("Collected By", list(user_opts.keys()))
                e_sub   = st.form_submit_button("📁 Add Evidence", use_container_width=True)

            if e_sub:
                try:
                    add_evidence(
                        incident_id=sel_id,
                        evidence_type=e_type,
                        file_name=e_fname or None,
                        file_hash=e_hash or None,
                        description=e_desc,
                        collected_by=user_opts[e_by_label],
                    )
                    st.success("✅ Evidence recorded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MITIGATION ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_mit:
    col_mlist, col_mform = st.columns([3, 2])

    with col_mlist:
        st.subheader("Mitigation Actions")
        actions = get_mitigation_actions(sel_id)
        if actions:
            status_icon = {"Pending": "⏳", "In Progress": "🔄", "Completed": "✅"}
            for action in actions:
                icon = status_icon.get(action["action_status"], "•")
                with st.container(border=True):
                    col_a1, col_a2 = st.columns([4, 1])
                    with col_a1:
                        st.markdown(f"**{icon} #{action['action_id']}** — {action['action_description']}")
                        st.caption(
                            f"By: {action['performed_by_name']} | Created: {action['created_at']} "
                            + (f"| Completed: {action['completed_at']}" if action['completed_at'] else "")
                        )
                    with col_a2:
                        new_s = st.selectbox(
                            "Status",
                            ["Pending", "In Progress", "Completed"],
                            index=["Pending", "In Progress", "Completed"].index(action["action_status"]),
                            key=f"mit_status_{action['action_id']}",
                        )
                        if new_s != action["action_status"]:
                            if st.button("Update", key=f"mit_upd_{action['action_id']}"):
                                update_mitigation_status(action["action_id"], new_s)
                                st.success("Updated!")
                                st.rerun()
        else:
            st.info("No mitigation actions yet.")

    with col_mform:
        st.subheader("Add Mitigation Action")
        if not users:
            st.warning("No users in database.")
        else:
            with st.form("add_mitigation_form", clear_on_submit=True):
                m_desc   = st.text_area("Action Description *", placeholder="Blocked IP range 203.0.113.0/24 on firewall.", height=120)
                m_by_lbl = st.selectbox("Performed By", list(user_opts.keys()))
                m_sub    = st.form_submit_button("🛡️ Add Action", use_container_width=True)

            if m_sub:
                if not m_desc.strip():
                    st.error("Description is required.")
                else:
                    try:
                        add_mitigation_action(
                            incident_id=sel_id,
                            action_description=m_desc.strip(),
                            performed_by=user_opts[m_by_lbl],
                        )
                        st.success("✅ Mitigation action added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMMENTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_com:
    st.subheader("💬 Incident Discussion")
    comments = get_comments(sel_id)

    if comments:
        for c in comments:
            with st.chat_message("user"):
                st.markdown(f"**{c['author']}** · {c['created_at']}")
                st.markdown(c["comment_text"])
    else:
        st.info("No comments yet. Be the first to add one!")

    st.divider()
    if users:
        with st.form("add_comment_form", clear_on_submit=True):
            c_author_lbl = st.selectbox("Commenting as", list(user_opts.keys()))
            c_text       = st.text_area("Comment", placeholder="Investigation notes…", height=100)
            c_sub        = st.form_submit_button("💬 Post Comment", use_container_width=True)

        if c_sub:
            if not c_text.strip():
                st.error("Comment cannot be empty.")
            else:
                try:
                    add_comment(sel_id, user_opts[c_author_lbl], c_text.strip())
                    st.success("Comment posted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STATUS HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    st.subheader("🕰️ Incident Timeline")
    history = get_status_history(sel_id)

    if not history:
        st.info("No status history recorded.")
    else:
        for h in history:
            old = h["old_status"] or "—"
            new = h["new_status"]
            st.markdown(
                f"""
                <div style="border-left:3px solid #2563EB;padding:.5rem 1rem;margin:.5rem 0;background:#F8FAFC;border-radius:0 8px 8px 0">
                  <b>{h['changed_at']}</b> — {old} → <b style="color:#2563EB">{new}</b><br>
                  <span style="color:#64748B;font-size:.9rem">By: {h['changed_by_name']}
                  {(" | Note: " + h["change_note"]) if h["change_note"] else ""}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
