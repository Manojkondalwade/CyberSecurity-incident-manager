"""
pages/3_Assets_Vulnerabilities.py — Asset and vulnerability management.
"""
import streamlit as st
import pandas as pd
from services.auth import is_authenticated
from database.connection import execute_query, execute_write

st.set_page_config(page_title="Assets & Vulnerabilities | CyberSec", page_icon="🖥️", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# 🖥️ Assets & Vulnerabilities")
st.caption("Manage the asset inventory and known vulnerabilities.")
st.divider()

tab_assets, tab_vulns, tab_links = st.tabs(["🖥️ Assets", "🐛 Vulnerabilities", "🔗 Link to Incident"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_assets():
    return execute_query("SELECT * FROM assets ORDER BY asset_name")

def get_vulnerabilities():
    return execute_query("SELECT * FROM vulnerabilities ORDER BY vulnerability_name")

def get_incidents_basic():
    return execute_query(
        "SELECT i.incident_id, i.incident_code, i.title FROM incidents i ORDER BY i.reported_at DESC LIMIT 200"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSETS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_assets:
    col_list, col_form = st.columns([3, 2])

    with col_list:
        st.subheader("Asset Inventory")
        assets = get_assets()
        if assets:
            df = pd.DataFrame([dict(r) for r in assets])
            st.dataframe(
                df[["asset_id", "asset_name", "asset_type", "ip_address", "owner_name", "criticality", "created_at"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No assets recorded yet.")

    with col_form:
        st.subheader("Add New Asset")
        with st.form("new_asset_form", clear_on_submit=True):
            a_name = st.text_input("Asset Name *", placeholder="Web Server 01")
            a_type = st.selectbox("Asset Type", ["Server", "Workstation", "Network Device", "Database", "Application", "Mobile Device", "Cloud Resource", "Other"])
            a_ip   = st.text_input("IP Address", placeholder="192.168.1.10")
            a_owner = st.text_input("Owner Name", placeholder="IT Department")
            a_crit = st.selectbox("Criticality", ["Critical", "High", "Medium", "Low"], index=2)
            submitted = st.form_submit_button("Add Asset", use_container_width=True)

        if submitted:
            if not a_name.strip():
                st.error("Asset name is required.")
            else:
                try:
                    execute_write(
                        """
                        INSERT INTO assets (asset_name, asset_type, ip_address, owner_name, criticality)
                        VALUES (:name, :type, :ip, :owner, :crit)
                        """,
                        {"name": a_name.strip(), "type": a_type, "ip": a_ip or None,
                         "owner": a_owner or None, "crit": a_crit},
                    )
                    st.success(f"✅ Asset '{a_name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — VULNERABILITIES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_vulns:
    col_vlist, col_vform = st.columns([3, 2])

    with col_vlist:
        st.subheader("Known Vulnerabilities")
        vulns = get_vulnerabilities()
        if vulns:
            df_v = pd.DataFrame([dict(r) for r in vulns])
            st.dataframe(
                df_v[["vulnerability_id", "vulnerability_name", "cve_id", "cvss_score", "severity"]],
                use_container_width=True, hide_index=True,
            )
            # Expandable details
            for v in vulns[:10]:
                with st.expander(f"📋 {v['vulnerability_name']} ({v['cve_id'] or 'No CVE'})"):
                    st.markdown(f"**Severity:** {v['severity']}  |  **CVSS:** {v['cvss_score'] or 'N/A'}")
                    if v['description']:
                        st.markdown(f"**Description:** {v['description']}")
                    if v['remediation']:
                        st.markdown(f"**Remediation:** {v['remediation']}")
        else:
            st.info("No vulnerabilities recorded yet.")

    with col_vform:
        st.subheader("Add Vulnerability")
        with st.form("new_vuln_form", clear_on_submit=True):
            v_name   = st.text_input("Vulnerability Name *", placeholder="Log4Shell Remote Code Execution")
            v_desc   = st.text_area("Description", height=80)
            v_cve    = st.text_input("CVE ID", placeholder="CVE-2021-44228")
            v_cvss   = st.number_input("CVSS Score (0–10)", min_value=0.0, max_value=10.0, value=5.0, step=0.1)
            v_sev    = st.selectbox("Severity", ["Critical", "High", "Medium", "Low"], index=2)
            v_rem    = st.text_area("Remediation Steps", height=80)
            v_sub    = st.form_submit_button("Add Vulnerability", use_container_width=True)

        if v_sub:
            if not v_name.strip():
                st.error("Name is required.")
            else:
                try:
                    execute_write(
                        """
                        INSERT INTO vulnerabilities
                            (vulnerability_name, description, cve_id, cvss_score, severity, remediation)
                        VALUES (:name, :desc, :cve, :cvss, :sev, :rem)
                        """,
                        {"name": v_name.strip(), "desc": v_desc or None, "cve": v_cve or None,
                         "cvss": v_cvss, "sev": v_sev, "rem": v_rem or None},
                    )
                    st.success(f"✅ Vulnerability '{v_name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LINK ASSETS/VULNS TO INCIDENTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_links:
    st.subheader("Link Assets / Vulnerabilities to an Incident")

    incidents = get_incidents_basic()
    assets_all = get_assets()
    vulns_all  = get_vulnerabilities()

    if not incidents:
        st.info("No incidents found. Create one first.")
    else:
        inc_opts = {f"{i['incident_code']} — {i['title']}": i["incident_id"] for i in incidents}
        sel_inc_label = st.selectbox("Select Incident", list(inc_opts.keys()))
        sel_inc_id    = inc_opts[sel_inc_label]

        link_col1, link_col2 = st.columns(2)

        with link_col1:
            st.markdown("**Link Asset**")
            if assets_all:
                with st.form("link_asset_form"):
                    asset_opts = {f"{a['asset_name']} ({a['asset_type']})": a["asset_id"] for a in assets_all}
                    sel_asset_label = st.selectbox("Asset", list(asset_opts.keys()))
                    impact = st.text_input("Impact Description (optional)")
                    if st.form_submit_button("🔗 Link Asset"):
                        try:
                            execute_write(
                                "INSERT IGNORE INTO incident_assets (incident_id, asset_id, impact_description) VALUES (:iid, :aid, :imp)",
                                {"iid": sel_inc_id, "aid": asset_opts[sel_asset_label], "imp": impact or None},
                            )
                            st.success("Asset linked!")
                        except Exception as e:
                            st.error(f"Error: {e}")

                # Show linked assets
                linked_assets = execute_query(
                    "SELECT a.asset_name, a.asset_type, ia.impact_description FROM incident_assets ia JOIN assets a ON ia.asset_id=a.asset_id WHERE ia.incident_id=:iid",
                    {"iid": sel_inc_id}
                )
                if linked_assets:
                    st.markdown("**Currently linked assets:**")
                    st.dataframe(pd.DataFrame([dict(r) for r in linked_assets]), use_container_width=True, hide_index=True)
            else:
                st.info("No assets in database.")

        with link_col2:
            st.markdown("**Link Vulnerability**")
            if vulns_all:
                with st.form("link_vuln_form"):
                    vuln_opts = {f"{v['vulnerability_name']}": v["vulnerability_id"] for v in vulns_all}
                    sel_vuln_label = st.selectbox("Vulnerability", list(vuln_opts.keys()))
                    if st.form_submit_button("🔗 Link Vulnerability"):
                        try:
                            execute_write(
                                "INSERT IGNORE INTO incident_vulnerabilities (incident_id, vulnerability_id) VALUES (:iid, :vid)",
                                {"iid": sel_inc_id, "vid": vuln_opts[sel_vuln_label]},
                            )
                            st.success("Vulnerability linked!")
                        except Exception as e:
                            st.error(f"Error: {e}")

                # Show linked vulnerabilities
                linked_vulns = execute_query(
                    "SELECT v.vulnerability_name, v.severity, v.cve_id FROM incident_vulnerabilities iv JOIN vulnerabilities v ON iv.vulnerability_id=v.vulnerability_id WHERE iv.incident_id=:iid",
                    {"iid": sel_inc_id}
                )
                if linked_vulns:
                    st.markdown("**Currently linked vulnerabilities:**")
                    st.dataframe(pd.DataFrame([dict(r) for r in linked_vulns]), use_container_width=True, hide_index=True)
            else:
                st.info("No vulnerabilities in database.")
