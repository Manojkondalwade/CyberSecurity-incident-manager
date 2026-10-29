"""
pages/5_Reports.py — Aggregated reports, Plotly charts, and CSV exports.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from services.auth import is_authenticated
from services.incidents import get_all_users
from services.reports import (
    incidents_by_attack_type, incidents_by_severity, incidents_by_month,
    analyst_workload, full_incident_report, get_saved_reports, save_report, df_to_csv,
)

st.set_page_config(page_title="Reports | CyberSec", page_icon="📈", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# 📈 Reports & Analytics")
st.caption("SQL-powered aggregated reports with chart visualisations and CSV export.")
st.divider()

tab_overview, tab_analysts, tab_full, tab_saved = st.tabs(
    ["📊 Overview", "👤 Analyst Performance", "📋 Full Incident Report", "🗂️ Saved Reports"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    col1, col2 = st.columns(2)

    # By Attack Type
    with col1:
        st.subheader("Incidents by Attack Type")
        df_at = incidents_by_attack_type()
        if df_at.empty:
            st.info("No data yet.")
        else:
            fig = px.bar(
                df_at, x="attack_type", y="total",
                color="category",
                labels={"attack_type": "Attack Type", "total": "Incidents"},
                title="Incidents per Attack Type",
            )
            fig.update_layout(margin=dict(t=40, b=10), xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)
            st.download_button(
                "⬇️ Download CSV",
                df_to_csv(df_at),
                file_name="incidents_by_attack_type.csv",
                mime="text/csv",
            )

    # By Severity
    with col2:
        st.subheader("Incidents by Severity")
        df_sev = incidents_by_severity()
        if df_sev.empty:
            st.info("No data yet.")
        else:
            fig2 = px.pie(
                df_sev, names="severity", values="total",
                color="severity",
                color_discrete_map={"Critical": "#EF4444", "High": "#F59E0B",
                                    "Medium": "#3B82F6", "Low": "#10B981"},
                title="Severity Breakdown",
                hole=0.4,
            )
            fig2.update_traces(textinfo="percent+label")
            fig2.update_layout(margin=dict(t=40, b=10))
            st.plotly_chart(fig2, use_container_width=True)

    # Over Time
    st.subheader("Incidents Over Time (Monthly)")
    df_month = incidents_by_month()
    if not df_month.empty:
        fig3 = px.area(
            df_month, x="month", y="total",
            title="Monthly Incident Volume",
            labels={"month": "Month", "total": "Incidents"},
            color_discrete_sequence=["#2563EB"],
        )
        fig3.update_layout(margin=dict(t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No monthly data yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYST PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analysts:
    st.subheader("Analyst Workload & Performance")
    df_an = analyst_workload()
    if df_an.empty:
        st.info("No analyst data yet.")
    else:
        st.dataframe(df_an, use_container_width=True, hide_index=True)

        if "total_assigned" in df_an.columns and df_an["total_assigned"].sum() > 0:
            fig4 = px.bar(
                df_an[df_an["total_assigned"] > 0], x="analyst", y="total_assigned",
                color="resolved",
                labels={"analyst": "Analyst", "total_assigned": "Assigned", "resolved": "Resolved"},
                title="Incidents Assigned vs Resolved",
                barmode="overlay",
                color_continuous_scale=["#DBEAFE", "#10B981"],
            )
            fig4.update_layout(margin=dict(t=40, b=10))
            st.plotly_chart(fig4, use_container_width=True)

        st.download_button(
            "⬇️ Download Analyst Report CSV",
            df_to_csv(df_an),
            file_name="analyst_performance.csv",
            mime="text/csv",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FULL INCIDENT REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_full:
    st.subheader("Full Incident Export")

    # Filters
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        sev_filter = st.multiselect("Filter by Severity", ["Critical", "High", "Medium", "Low"])
    with fcol2:
        status_filter = st.multiselect(
            "Filter by Status",
            ["Open", "Assigned", "Investigating", "Contained", "Resolved", "Closed"],
        )

    df_full = full_incident_report()

    if not df_full.empty:
        if sev_filter:
            df_full = df_full[df_full["severity"].isin(sev_filter)]
        if status_filter:
            df_full = df_full[df_full["status"].isin(status_filter)]

        st.dataframe(df_full, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_full)} incident(s).")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Download Full Report CSV",
                df_to_csv(df_full),
                file_name="full_incident_report.csv",
                mime="text/csv",
            )

        with col_dl2:
            users = get_all_users()
            if users:
                user_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users}
                with st.form("save_report_form"):
                    report_title = st.text_input("Report Title", value="Full Incident Report")
                    gen_by_lbl   = st.selectbox("Generated By", list(user_opts.keys()))
                    notes        = st.text_area("Notes", height=60)
                    if st.form_submit_button("💾 Save Report Record"):
                        try:
                            save_report(
                                report_title=report_title,
                                generated_by=user_opts[gen_by_lbl],
                                notes=notes,
                            )
                            st.success("Report saved to database!")
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("No incidents in the database yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SAVED REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_saved:
    st.subheader("Saved Report Records")
    saved = get_saved_reports()
    if saved:
        df_saved = pd.DataFrame([dict(r) for r in saved])
        st.dataframe(df_saved, use_container_width=True, hide_index=True)
    else:
        st.info("No saved reports yet. Generate and save one from the Full Report tab.")
