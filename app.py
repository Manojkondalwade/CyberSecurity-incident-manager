"""
app.py — CyberSec Incident Manager entry point.
Handles the login gate, sidebar navigation, and a top-level dashboard.
"""
import streamlit as st
from database.connection import get_engine, test_connection
from services.auth import verify_login, is_authenticated
from services.incidents import get_dashboard_metrics
from sqlalchemy import text

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberSec Incident Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Top header strip */
    .main-header {
        background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: #fff;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p  { margin: 0; opacity: 0.85; font-size: 0.95rem; }

    /* KPI cards */
    .kpi-card {
        background: #fff;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,.06);
        transition: box-shadow .2s;
    }
    .kpi-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.12); }
    .kpi-number { font-size: 2.4rem; font-weight: 800; line-height: 1; }
    .kpi-label  { font-size: 0.85rem; color: #64748B; margin-top: .3rem; }

    /* Severity badges */
    .badge-Critical { background:#FEE2E2; color:#991B1B; padding:2px 10px; border-radius:20px; font-size:.8rem; font-weight:600; }
    .badge-High     { background:#FEF3C7; color:#92400E; padding:2px 10px; border-radius:20px; font-size:.8rem; font-weight:600; }
    .badge-Medium   { background:#DBEAFE; color:#1E40AF; padding:2px 10px; border-radius:20px; font-size:.8rem; font-weight:600; }
    .badge-Low      { background:#DCFCE7; color:#166534; padding:2px 10px; border-radius:20px; font-size:.8rem; font-weight:600; }

    /* Login card */
    .login-card {
        max-width: 440px;
        margin: 6vh auto;
        padding: 2.5rem;
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 8px 40px rgba(37,99,235,.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Login gate ────────────────────────────────────────────────────────────────
def show_login():
    st.markdown(
        """
        <div class="login-card">
          <div style="text-align:center;margin-bottom:1.5rem">
            <div style="font-size:3rem">🛡️</div>
            <h2 style="margin:0;color:#1E3A5F">CyberSec Incident Manager</h2>
            <p style="color:#64748B;margin:.3rem 0 0">Cybersecurity Incident Management System</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col = st.columns([1, 2, 1])[1]
    with col:
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Sign In")
            username = st.text_input("Username", placeholder="demo")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🔐  Sign In", use_container_width=True)

        if submitted:
            if verify_login(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("❌  Invalid username or password.")

        st.markdown(
            "<p style='text-align:center;color:#94A3B8;font-size:.8rem;margin-top:.5rem'>"
            "Default credentials: <b>demo</b> / <b>demo123</b></p>",
            unsafe_allow_html=True,
        )


if not is_authenticated():
    show_login()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ CyberSec")
    st.caption("Incident Management System")
    st.divider()

    # DB status
    try:
        db_name = test_connection()
        st.success(f"✓ Connected: `{db_name}`")
    except Exception as e:
        st.error(f"DB Error: {e}")

    st.divider()

    if st.button("🚪  Sign Out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)
        st.rerun()

# ── Dashboard home (app.py itself) ────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
      <h1>🛡️ Security Operations Dashboard</h1>
      <p>Monitor incidents, investigate threats, and track mitigation progress.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# KPI Metrics
try:
    metrics = get_dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)

    for col, label, value, color in [
        (c1, "Total Incidents",  metrics["total"],    "#2563EB"),
        (c2, "Open / Active",    metrics["open"],     "#F59E0B"),
        (c3, "Critical",         metrics["critical"], "#EF4444"),
        (c4, "Resolved / Closed",metrics["resolved"], "#10B981"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-number" style="color:{color}">{value}</div>
                  <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if metrics["total"] == 0:
        st.info(
            "📭 **No incidents yet.**  \n"
            "Go to **Administration** to create a user, then use **Incidents** to log your first incident.",
            icon="ℹ️",
        )
    else:
        import plotly.express as px
        import pandas as pd
        from services.incidents import get_severity_distribution, get_status_distribution, get_recent_incidents

        col_left, col_right = st.columns(2)

        with col_left:
            sev_rows = get_severity_distribution()
            if sev_rows:
                sev_df = pd.DataFrame([dict(r) for r in sev_rows])
                color_map = {"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#3B82F6", "Low": "#10B981"}
                fig = px.pie(
                    sev_df, names="severity", values="cnt",
                    title="Incidents by Severity",
                    color="severity", color_discrete_map=color_map,
                    hole=0.45,
                )
                fig.update_layout(margin=dict(t=40, b=10), legend_orientation="h")
                st.plotly_chart(fig, use_container_width=True)

        with col_right:
            stat_rows = get_status_distribution()
            if stat_rows:
                stat_df = pd.DataFrame([dict(r) for r in stat_rows])
                fig2 = px.bar(
                    stat_df, x="status_name", y="cnt",
                    title="Incidents by Status",
                    color="cnt",
                    color_continuous_scale=["#DBEAFE", "#2563EB"],
                    labels={"status_name": "Status", "cnt": "Count"},
                )
                fig2.update_layout(coloraxis_showscale=False, margin=dict(t=40, b=10))
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Recent Incidents")
        recent = get_recent_incidents(10)
        if recent:
            df = pd.DataFrame([dict(r) for r in recent])
            st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Dashboard error: {e}")
    st.info("Run `python setup.py` to initialise the database.")
