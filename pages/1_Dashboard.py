"""
pages/1_Dashboard.py — Extended dashboard with Plotly analytics.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.auth import is_authenticated
from services.incidents import (
    get_dashboard_metrics, get_severity_distribution,
    get_status_distribution, get_recent_incidents,
)
from database.connection import execute_query

st.set_page_config(page_title="Dashboard | CyberSec", page_icon="📊", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# 📊 Dashboard & Analytics")
st.caption("Real-time metrics drawn directly from the database.")
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
try:
    m = get_dashboard_metrics()
except Exception as e:
    st.error(f"Cannot load metrics: {e}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
for col, label, val, color, icon in [
    (c1, "Total Incidents",   m["total"],    "#2563EB", "📁"),
    (c2, "Open / Active",     m["open"],     "#F59E0B", "🔓"),
    (c3, "Critical Severity", m["critical"], "#EF4444", "🚨"),
    (c4, "Resolved",          m["resolved"], "#10B981", "✅"),
]:
    with col:
        st.metric(label=f"{icon} {label}", value=val)

st.divider()

if m["total"] == 0:
    st.info("No incidents in the database yet. Create some via the Incidents page.")
    st.stop()

# ── Charts row 1 ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    sev_rows = get_severity_distribution()
    if sev_rows:
        df_sev = pd.DataFrame([dict(r) for r in sev_rows])
        fig = px.pie(
            df_sev, names="severity", values="cnt",
            title="Severity Distribution",
            color="severity",
            color_discrete_map={"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#10B981"},
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    stat_rows = get_status_distribution()
    if stat_rows:
        df_stat = pd.DataFrame([dict(r) for r in stat_rows])
        fig2 = px.bar(
            df_stat, x="status_name", y="cnt",
            title="Incidents by Status",
            color="status_name",
            labels={"status_name": "Status", "cnt": "Count"},
        )
        fig2.update_layout(showlegend=False, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

# ── Charts row 2 ─────────────────────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    rows = execute_query(
        """
        SELECT COALESCE(at.attack_name,'Unknown') AS attack_type, COUNT(*) AS cnt
        FROM incidents i
        LEFT JOIN attack_types at ON i.attack_type_id = at.attack_type_id
        GROUP BY attack_type ORDER BY cnt DESC LIMIT 8
        """
    )
    if rows:
        df_at = pd.DataFrame([dict(r) for r in rows])
        fig3 = px.bar(
            df_at, x="cnt", y="attack_type", orientation="h",
            title="Top Attack Types",
            labels={"cnt": "Incidents", "attack_type": ""},
            color="cnt", color_continuous_scale=["#DBEAFE", "#1E40AF"],
        )
        fig3.update_layout(coloraxis_showscale=False, margin=dict(t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)

with col_d:
    rows2 = execute_query(
        """
        SELECT DATE_FORMAT(reported_at,'%Y-%m') AS month, COUNT(*) AS cnt
        FROM incidents GROUP BY month ORDER BY month
        """
    )
    if rows2:
        df_month = pd.DataFrame([dict(r) for r in rows2])
        fig4 = px.line(
            df_month, x="month", y="cnt",
            title="Incidents Over Time",
            labels={"month": "Month", "cnt": "Incidents"},
            markers=True,
        )
        fig4.update_traces(line_color="#2563EB", line_width=2.5)
        fig4.update_layout(margin=dict(t=40, b=10))
        st.plotly_chart(fig4, use_container_width=True)

# ── Recent Incidents Table ────────────────────────────────────────────────────
st.subheader("🕒 Recent Incidents")
recent = get_recent_incidents(10)
if recent:
    df_r = pd.DataFrame([dict(r) for r in recent])
    st.dataframe(df_r, use_container_width=True, hide_index=True)
else:
    st.info("No recent incidents.")
