#!/usr/bin/env python3
"""
Tidal authentication setup.
"""
import json
import tidalapi
from pathlib import Path

def setup_tidal_session():
    """
    Set up Tidal session with OAuth authentication.
    This will prompt you to log in via your browser.
    """
    session = tidalapi.Session()

    # OAuth login
    print("Setting up Tidal authentication...")
    print("A browser window will open for you to log in.")

    login, future = session.login_oauth()

    print(f"\nPlease visit: {login.verification_uri_complete}")
    print("Or go to:", login.verification_uri)
    print(f"And enter code: {login.user_code}")
    print("\nWaiting for authorization...")

    future.result()

    if session.check_login():
        print("✓ Successfully logged in to Tidal!")

        # Save session for later use
        session_data = {
            "token_type": session.token_type,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expiry_time": session.expiry_time.isoformat() if session.expiry_time else None
        }

        with open(".tidal_session.json", "w") as f:
            json.dump(session_data, f, indent=2)

        print("Session saved to .tidal_session.json")
        return session
    else:
        print("✗ Login failed")
        return None

def load_tidal_session():
    """Load existing Tidal session or create a new one."""
    session = tidalapi.Session()

    if Path(".tidal_session.json").exists():
        print("Loading existing Tidal session...")
        try:
            with open(".tidal_session.json", "r") as f:
                session_data = json.load(f)

            session.load_oauth_session(
                session_data["token_type"],
                session_data["access_token"],
                session_data["refresh_token"]
            )

            if session.check_login():
                print("✓ Tidal session loaded successfully")
                return session
            else:
                print("Session expired, need to re-authenticate")
        except Exception as e:
            print(f"Error loading session: {e}")

    return setup_tidal_session()

if __name__ == "__main__":
    session = setup_tidal_session()
    if session:
        # Test the session
        user = session.user
        print(f"\nLogged in as: {user.first_name} (ID: {user.id})")
