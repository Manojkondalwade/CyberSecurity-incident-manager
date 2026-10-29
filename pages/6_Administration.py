"""
pages/6_Administration.py — User, analyst, and reference data management.
"""
import streamlit as st
import pandas as pd
from services.auth import is_authenticated
from database.connection import execute_query, execute_write, get_engine
from sqlalchemy import text

st.set_page_config(page_title="Administration | CyberSec", page_icon="⚙️", layout="wide")

if not is_authenticated():
    st.warning("Please sign in from the home page.")
    st.stop()

st.markdown("# ⚙️ Administration")
st.caption("Manage users, analysts, attack types, and system information.")
st.divider()

tab_users, tab_analysts, tab_attacks, tab_system = st.tabs(
    ["👤 Users", "🔍 Analysts", "⚔️ Attack Types", "🖥️ System Info"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — USERS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_users:
    col_ulist, col_uform = st.columns([3, 2])

    with col_ulist:
        st.subheader("All Users")
        users = execute_query("SELECT user_id, full_name, username, email, role, created_at FROM users ORDER BY full_name")
        if users:
            df_u = pd.DataFrame([dict(r) for r in users])
            st.dataframe(df_u, use_container_width=True, hide_index=True)
        else:
            st.info("No users yet. Create one using the form.")

    with col_uform:
        st.subheader("Create User")
        with st.form("create_user_form", clear_on_submit=True):
            u_name     = st.text_input("Full Name *", placeholder="Alice Johnson")
            u_username = st.text_input("Username *", placeholder="alice.j")
            u_email    = st.text_input("Email", placeholder="alice@example.com")
            u_role     = st.selectbox("Role", ["Employee", "Analyst", "Manager", "Administrator"])
            u_sub      = st.form_submit_button("👤 Create User", use_container_width=True)

        if u_sub:
            if not u_name.strip() or not u_username.strip():
                st.error("Full name and username are required.")
            else:
                try:
                    execute_write(
                        """
                        INSERT INTO users (full_name, username, email, role)
                        VALUES (:name, :username, :email, :role)
                        """,
                        {
                            "name": u_name.strip(),
                            "username": u_username.strip(),
                            "email": u_email.strip() or None,
                            "role": u_role,
                        },
                    )
                    st.success(f"✅ User '{u_name}' created!")
                    st.rerun()
                except Exception as e:
                    if "Duplicate" in str(e):
                        st.error(f"Username or email already exists.")
                    else:
                        st.error(f"Error: {e}")

        # Delete user
        st.divider()
        st.markdown("**Delete User**")
        users_del = execute_query("SELECT user_id, full_name, username FROM users ORDER BY full_name")
        if users_del:
            with st.form("delete_user_form"):
                del_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in users_del}
                sel_del_user = st.selectbox("Select user to delete", list(del_opts.keys()))
                confirm = st.checkbox("I understand this will delete the user.")
                if st.form_submit_button("🗑️ Delete User", type="secondary"):
                    if confirm:
                        try:
                            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": del_opts[sel_del_user]})
                            st.success("User deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Cannot delete (referenced by other records?): {e}")
                    else:
                        st.warning("Check the confirmation box first.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYSTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analysts:
    col_alist, col_aform = st.columns([3, 2])

    with col_alist:
        st.subheader("Analyst Profiles")
        analysts = execute_query(
            """
            SELECT al.analyst_id, u.full_name, u.username, u.email,
                   al.specialization
            FROM analysts al
            JOIN users u ON al.user_id = u.user_id
            ORDER BY u.full_name
            """
        )
        if analysts:
            df_an = pd.DataFrame([dict(r) for r in analysts])
            st.dataframe(df_an, use_container_width=True, hide_index=True)
        else:
            st.info("No analyst profiles yet.")

    with col_aform:
        st.subheader("Promote User to Analyst")
        # Only users not already analysts
        eligible = execute_query(
            """
            SELECT u.user_id, u.full_name, u.username
            FROM users u
            WHERE u.user_id NOT IN (SELECT user_id FROM analysts)
            ORDER BY u.full_name
            """
        )
        if not eligible:
            st.info("All existing users are already analysts, or no users exist.")
        else:
            with st.form("create_analyst_form", clear_on_submit=True):
                el_opts = {f"{u['full_name']} ({u['username']})": u["user_id"] for u in eligible}
                sel_user = st.selectbox("Select User to promote", list(el_opts.keys()))
                spec     = st.text_input("Specialization", placeholder="Malware Analysis, Network Forensics…")
                an_sub   = st.form_submit_button("🔍 Create Analyst Profile", use_container_width=True)

            if an_sub:
                try:
                    execute_write(
                        "INSERT INTO analysts (user_id, specialization) VALUES (:uid, :spec)",
                        {"uid": el_opts[sel_user], "spec": spec or None},
                    )
                    # Update role to Analyst
                    execute_write(
                        "UPDATE users SET role='Analyst' WHERE user_id=:uid",
                        {"uid": el_opts[sel_user]},
                    )
                    st.success(f"✅ Analyst profile created for {sel_user.split('(')[0].strip()}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ATTACK TYPES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_attacks:
    col_atlist, col_atform = st.columns([3, 2])

    with col_atlist:
        st.subheader("Attack Types")
        attacks = execute_query("SELECT * FROM attack_types ORDER BY category, attack_name")
        if attacks:
            df_at = pd.DataFrame([dict(r) for r in attacks])
            st.dataframe(df_at, use_container_width=True, hide_index=True)
        else:
            st.info("No attack types.")

    with col_atform:
        st.subheader("Add Attack Type")
        with st.form("add_attack_form", clear_on_submit=True):
            at_name = st.text_input("Attack Name *", placeholder="Supply Chain Attack")
            at_cat  = st.text_input("Category", placeholder="Third-Party Risk")
            at_desc = st.text_area("Description", height=100)
            at_sub  = st.form_submit_button("Add Attack Type", use_container_width=True)

        if at_sub:
            if not at_name.strip():
                st.error("Name required.")
            else:
                try:
                    execute_write(
                        "INSERT INTO attack_types (attack_name, category, description) VALUES (:n, :c, :d)",
                        {"n": at_name.strip(), "c": at_cat or None, "d": at_desc or None},
                    )
                    st.success(f"✅ '{at_name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SYSTEM INFO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_system:
    st.subheader("Database System Information")

    try:
        engine = get_engine()
        with engine.connect() as conn:
            db_version = conn.execute(text("SELECT VERSION()")).scalar_one()
            db_name    = conn.execute(text("SELECT DATABASE()")).scalar_one()

        st.markdown(f"**MySQL Version:** `{db_version}`")
        st.markdown(f"**Connected Database:** `{db_name}`")
        st.divider()

        st.subheader("Table Row Counts")
        tables = [
            "users", "analysts", "attack_types", "incident_status",
            "assets", "vulnerabilities", "incidents",
            "incident_assets", "incident_vulnerabilities",
            "evidence", "mitigation_actions",
            "incident_status_history", "incident_comments", "reports",
        ]
        counts = []
        with engine.connect() as conn:
            for t in tables:
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
                    counts.append({"Table": t, "Row Count": cnt})
                except Exception:
                    counts.append({"Table": t, "Row Count": "Error"})

        df_counts = pd.DataFrame(counts)
        st.dataframe(df_counts, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Foreign Key Relationships")
        with engine.connect() as conn:
            fk_rows = conn.execute(text("""
                SELECT
                    TABLE_NAME AS `From Table`,
                    COLUMN_NAME AS `Column`,
                    REFERENCED_TABLE_NAME AS `References Table`,
                    REFERENCED_COLUMN_NAME AS `Referenced Column`
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE REFERENCED_TABLE_NAME IS NOT NULL
                  AND TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME
            """)).mappings().all()

        if fk_rows:
            df_fk = pd.DataFrame([dict(r) for r in fk_rows])
            st.dataframe(df_fk, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Cannot load system info: {e}")
