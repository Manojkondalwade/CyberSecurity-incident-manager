#!/usr/bin/env python3
"""
setup.py
One-shot setup: creates the MySQL database, application user,
imports the schema, and prints the bcrypt hash for the demo password.

Usage (from the project root, with MySQL root credentials):
    python setup.py
"""
import subprocess
import sys
import os
import getpass

DEMO_PASSWORD = "demo123"
DB_NAME = "cyber_incident_db"
APP_USER = "cyber_app"
APP_PASS = "CyberApp@2024!"
ROOT_HOST = "localhost"

BANNER = """
╔══════════════════════════════════════════════╗
║   CyberSec Incident Manager — Setup Script  ║
╚══════════════════════════════════════════════╝
"""


def mysql_exec(sql: str, root_user: str, root_pass: str) -> bool:
    cmd = [
        "mysql",
        f"-u{root_user}",
        f"-p{root_pass}",
        "-h", ROOT_HOST,
        "--execute", sql,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ MySQL error: {result.stderr.strip()}")
        return False
    return True


def mysql_exec_file(filepath: str, db: str, root_user: str, root_pass: str) -> bool:
    cmd = [
        "mysql",
        f"-u{root_user}",
        f"-p{root_pass}",
        "-h", ROOT_HOST,
        db,
    ]
    with open(filepath, "r") as f:
        result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ MySQL error: {result.stderr.strip()}")
        return False
    return True


def generate_hash(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def write_secrets(hash_val: str):
    secrets_dir = os.path.join(os.path.dirname(__file__), ".streamlit")
    os.makedirs(secrets_dir, exist_ok=True)
    secrets_path = os.path.join(secrets_dir, "secrets.toml")

    content = f"""[mysql]
host     = "localhost"
port     = 3306
username = "{APP_USER}"
password = "{APP_PASS}"
database = "{DB_NAME}"

[demo]
username      = "demo"
password_hash = "{hash_val}"
"""
    with open(secrets_path, "w") as f:
        f.write(content)
    print(f"  ✓ Written: {secrets_path}")


def main():
    print(BANNER)

    # ── Read root credentials ──────────────────────────────────────
    print("Enter MySQL root credentials to set up the database:\n")
    root_user = input("  MySQL root username [root]: ").strip() or "root"
    root_pass = getpass.getpass("  MySQL root password: ")

    # ── Create database ────────────────────────────────────────────
    print(f"\n[1/5] Creating database '{DB_NAME}' …")
    ok = mysql_exec(
        f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        root_user, root_pass,
    )
    if ok:
        print(f"  ✓ Database '{DB_NAME}' ready.")

    # ── Create application user ────────────────────────────────────
    print(f"\n[2/5] Creating MySQL user '{APP_USER}' …")
    mysql_exec(
        f"DROP USER IF EXISTS '{APP_USER}'@'localhost';",
        root_user, root_pass,
    )
    ok = mysql_exec(
        f"CREATE USER '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASS}';",
        root_user, root_pass,
    )
    if ok:
        mysql_exec(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {DB_NAME}.* "
            f"TO '{APP_USER}'@'localhost'; FLUSH PRIVILEGES;",
            root_user, root_pass,
        )
        print(f"  ✓ User '{APP_USER}' created with DML privileges.")

    # ── Import schema ──────────────────────────────────────────────
    print("\n[3/5] Importing schema …")
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    ok = mysql_exec_file(schema_path, DB_NAME, root_user, root_pass)
    if ok:
        print("  ✓ Schema imported (14 tables + reference data).")

    # ── Generate bcrypt hash ───────────────────────────────────────
    print(f"\n[4/5] Generating bcrypt hash for demo password '{DEMO_PASSWORD}' …")
    try:
        hash_val = generate_hash(DEMO_PASSWORD)
        print(f"  ✓ Hash generated.")
    except ImportError:
        print("  ✗ bcrypt not installed. Run: pip install bcrypt")
        hash_val = ""

    # ── Write secrets.toml ─────────────────────────────────────────
    print("\n[5/5] Writing .streamlit/secrets.toml …")
    if hash_val:
        write_secrets(hash_val)

    # ── Done ───────────────────────────────────────────────────────
    print("""
╔══════════════════════════════════════════════╗
║              Setup Complete!                ║
╠══════════════════════════════════════════════╣
║  Demo login:  demo / demo123                ║
║  Run app:     streamlit run app.py          ║
╚══════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
