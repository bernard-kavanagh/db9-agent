"""
One-time setup: creates the db9 database and applies the schema.

Usage:
  python setup.py

Prerequisites:
  1. Run `./db9 login` (SSO) or `./db9 login --api-key YOUR_KEY`
  2. Run this script — it will create the database and apply schema.sql
  3. Copy the connection string into .env as DB9_CONNECTION_STRING
"""
import subprocess
import sys
import json
import os


def run(cmd: list[str], capture: bool = False):
    result = subprocess.run(
        cmd, capture_output=capture, text=True,
        cwd=os.path.dirname(__file__)
    )
    return result


def main():
    print("── db9 Lead Dashboard Setup ──\n")

    # 1. Check login
    result = run(["./db9", "status", "--output", "json"], capture=True)
    if result.returncode != 0:
        print("❌  Not logged in. Run: ./db9 login")
        sys.exit(1)
    print("✅  Logged in to db9")

    # 2. Create database
    db_name = "emea-leads"
    app_user = "leads_app"
    print(f"\n📦  Creating database '{db_name}'...")
    result = run(["./db9", "create", "--name", db_name, "--json"], capture=True)
    if result.returncode != 0:
        print(f"   (database may already exist, continuing...)")

    # 3. Create a persistent app user (avoids 10-min JWT expiry)
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    app_password = ''.join(secrets.choice(alphabet) for _ in range(32))
    print(f"\n👤  Creating persistent app user '{app_user}'...")
    result = run([
        "./db9", "db", "users", db_name, "create",
        "--username", app_user,
        "--password", app_password,
        "--json",
    ], capture=True)

    conn_str = None
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            conn_str = data.get("connection_string_with_password")
        except json.JSONDecodeError:
            pass

    if not conn_str:
        # Fall back to short-lived admin token
        result = run(["./db9", "db", "connect", db_name, "--json"], capture=True)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                conn_str = data.get("connection_string")
                print("⚠️  Using short-lived token — replace DB9_CONNECTION_STRING before long runs")
            except json.JSONDecodeError:
                pass

    if not conn_str:
        print("\n⚠️  Could not auto-detect connection string.")
        print(f"   Run: ./db9 db users {db_name} create --username leads_app --password YOURPASS --json")
        print("   Then add connection_string_with_password to .env as DB9_CONNECTION_STRING")
    else:
        print(f"✅  Connection string obtained")

    # 4. Apply schema
    print("\n📐  Applying schema...")
    result = run(["./db9", "db", "sql", db_name, "--file", "schema.sql"], capture=True)
    if result.returncode == 0:
        print("✅  Schema applied")
    else:
        print(f"⚠️  Schema apply returned: {result.stderr}")
        print(f"   You may need to apply schema.sql manually:")
        print(f"   ./db9 db sql {db_name} --file schema.sql")

    # 5. Write .env if it doesn't exist
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"ANTHROPIC_API_KEY=your_key_here\n")
            if conn_str:
                f.write(f"DB9_CONNECTION_STRING={conn_str}\n")
            else:
                f.write(f"DB9_CONNECTION_STRING=\n")
        print(f"\n📝  Created .env — add your ANTHROPIC_API_KEY")
    else:
        if conn_str:
            print(f"\n📝  .env exists. Set DB9_CONNECTION_STRING={conn_str}")
        print("   Make sure ANTHROPIC_API_KEY is set in .env")

    print("\n── Next steps ──────────────────────────────────────────────")
    print("1. Edit .env — set ANTHROPIC_API_KEY and DB9_CONNECTION_STRING")
    print("2. Install deps:  pip install -r requirements.txt")
    print("3. Run agent:     python -m agent.run --region 'Western Europe'")
    print("4. Run dashboard: uvicorn dashboard.main:app --reload --port 8000")
    print("   Then open:     http://localhost:8000")
    print("────────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
