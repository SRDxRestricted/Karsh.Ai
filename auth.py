"""
auth.py — Authentication gate for Karsh.Ai
Stores user credentials in a local JSON file (hashed passwords).
"""
import streamlit as st
import json
import hashlib
import os

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

KERALA_DISTRICTS = [
    "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha",
    "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad",
    "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod",
]


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _load_users() -> dict:
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_users(users: dict):
    with open(AUTH_FILE, "w") as f:
        json.dump(users, f, indent=2)


def require_auth():
    """
    Call at the top of every page.
    Returns True if the user is logged in.
    When not logged in, renders login/signup and calls st.stop().
    """
    if st.session_state.get("authenticated"):
        return True
    _render_auth_page()
    st.stop()
    return False


def get_username() -> str:
    return st.session_state.get("username", "Farmer")


def get_user_district() -> str:
    return st.session_state.get("user_district", "Ernakulam")


def logout():
    for key in ["authenticated", "username", "user_district"]:
        st.session_state.pop(key, None)


def _render_auth_page():
    """Render the login / signup UI."""

    st.markdown("""
    <style>
        .auth-brand {
            text-align: center;
            margin-bottom: 32px;
        }
        .auth-brand h1 {
            color: #00c853;
            font-size: 2.2rem;
            font-weight: 900;
            margin: 0;
        }
        .auth-brand p {
            color: #9e9eb8;
            font-size: 0.88rem;
            margin: 6px 0 0 0;
        }
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"] {
            flex: 1;
            justify-content: center;
            font-weight: 600;
        }
        /* Fix password toggle overlap */
        [data-testid="stForm"] button[kind="icon"] {
            position: absolute !important;
            right: 8px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            z-index: 10 !important;
        }
        [data-testid="stForm"] input[type="password"] {
            padding-right: 40px !important;
        }
        /* Hide "Press Enter to submit form" hint */
        [data-testid="stForm"] [data-testid="InputInstructions"] {
            display: none !important;
        }
        /* Form field spacing */
        [data-testid="stForm"] [data-testid="stTextInput"],
        [data-testid="stForm"] [data-testid="stSelectbox"] {
            margin-bottom: 4px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Brand
    st.markdown("""
    <div class="auth-brand">
        <h1>Karsh.Ai</h1>
        <p>AI-Powered Farming Assistant for Kerala</p>
    </div>
    """, unsafe_allow_html=True)

    # Centred form column
    _, col, _ = st.columns([1.2, 2, 1.2])

    with col:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

        # ── Login ──
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Login", use_container_width=True, type="primary"
                )
                if submitted:
                    users = _load_users()
                    if username in users and users[username]["password"] == _hash(password):
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = users[username].get("name", username)
                        st.session_state["user_district"] = users[username].get("district", "Ernakulam")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        # ── Sign Up ──
        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Choose a Username")
                new_name = st.text_input("Your Name")
                new_district = st.selectbox("Your District", KERALA_DISTRICTS, index=6)
                new_pass = st.text_input("Choose a Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")
                signed_up = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )
                if signed_up:
                    if not new_user or not new_pass:
                        st.error("Username and password are required.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    else:
                        users = _load_users()
                        if new_user in users:
                            st.error("Username already taken.")
                        else:
                            users[new_user] = {
                                "name": new_name or new_user,
                                "district": new_district,
                                "password": _hash(new_pass),
                            }
                            _save_users(users)
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = new_name or new_user
                            st.session_state["user_district"] = new_district
                            st.rerun()
