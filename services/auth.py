"""
services/auth.py
Demo-account authentication using bcrypt.
"""
import bcrypt
import streamlit as st


def verify_login(username: str, password: str) -> bool:
    """Return True if the provided credentials match the demo account."""
    demo = st.secrets.get("demo", {})
    expected_username = demo.get("username", "demo")
    password_hash = demo.get("password_hash", "")

    if not password_hash:
        return False

    try:
        return (
            username == expected_username
            and bcrypt.checkpw(password.encode(), password_hash.encode())
        )
    except Exception:
        return False


def logout():
    """Clear the authenticated session state."""
    st.session_state["authenticated"] = False


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)
