"""HealthGuardian AI — Streamlit entry point."""

import streamlit as st

from healthguardian.database import ensure_db
from healthguardian.database.repository import get_user_by_id
from healthguardian.services.scheduler import start_scheduler
from healthguardian.ui.pages import init_session_state, render_dashboard, render_login_page, render_signup_page
from healthguardian.ui.styles import CUSTOM_CSS


@st.cache_resource
def setup_ngrok():
    from healthguardian.utils.ngrok import get_public_url
    return get_public_url(8501)

def main():
    st.set_page_config(
        page_title="HealthGuardian AI",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    ensure_db()
    start_scheduler()
    init_session_state()
    setup_ngrok()

    if "log_action" in st.query_params and "user_id" in st.query_params:
        action = st.query_params["log_action"]
        uid = int(st.query_params["user_id"])
        
        from healthguardian.database.repository import add_health_points, log_activity
        pts = 10
        if action == "exercise": pts = 20
        elif action in ["breakfast", "lunch", "dinner", "snacks"]: pts = 15
            
        add_health_points(uid, pts)
        log_activity(uid, "email_log", f"Logged {action} via Email (+{pts} pts)")
        
        st.toast(f"✅ Successfully logged {action}! You earned {pts} points.")
        st.query_params.clear()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🌿 HealthGuardian")
        st.caption("Your AI-powered wellness companion")

        if st.session_state.authenticated:
            user = get_user_by_id(st.session_state.user_id)
            if user:
                st.markdown(f"**{user.full_name}**")
                st.caption(f"📧 {user.email}")
                points = user.health_points or 0
                st.progress(min(points % 100 / 100, 1.0), text=f"🏆 {points} health points")

            st.divider()
            nav = st.radio(
                "Navigation",
                ["Dashboard", "Profile"],
                label_visibility="collapsed",
            )

            if st.button("Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            nav = None
            page_choice = st.radio(
                "Get Started",
                ["Sign In", "Sign Up"],
                label_visibility="collapsed",
            )
            st.session_state.page = "login" if page_choice == "Sign In" else "signup"

    st.markdown(
        '<div class="main-header"><h1>🌿 HealthGuardian AI</h1>'
        "<p>Multi-agent personal health assistant — personalised plans, medical guidance, Email & Telegram reminders</p></div>",
        unsafe_allow_html=True,
    )

    if st.session_state.authenticated:
        user = get_user_by_id(st.session_state.user_id)
        if not user:
            st.session_state.authenticated = False
            st.rerun()
            return

        if nav == "Profile":
            _render_profile(user)
        else:
            render_dashboard(user)
    else:
        if st.session_state.page == "signup":
            render_signup_page()
        else:
            render_login_page()


def _render_profile(user):
    from healthguardian.database import get_db_session
    from healthguardian.database.models import User

    st.markdown("### 👤 Your Profile")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            height = st.number_input("Height (cm)", value=user.height_cm or 170, min_value=100, max_value=250)
            weight = st.number_input("Weight (kg)", value=user.weight_kg or 70, min_value=30, max_value=300)
            city = st.text_input("City Override", value=user.city_override or "", placeholder="e.g. Berlin")
        with col2:
            allergies = st.text_area("Allergies", value=user.allergies or "")
            chronic = st.text_area("Chronic Conditions", value=user.chronic_conditions or "")
            medications = st.text_area("Medications", value=user.medications or "")

        emergency = st.text_input("Emergency Contact", value=user.emergency_contact or "")

        if st.form_submit_button("Save Profile", type="primary"):
            with get_db_session() as session:
                db_user = session.query(User).filter(User.id == user.id).first()
                if db_user:
                    db_user.height_cm = int(height)
                    db_user.weight_kg = int(weight)
                    db_user.city_override = city or None
                    db_user.allergies = allergies
                    db_user.chronic_conditions = chronic
                    db_user.medications = medications
                    db_user.emergency_contact = emergency
            st.toast("Profile updated!")
            st.rerun()

    st.info(
        f"**Account:** {user.full_name} · DOB: {user.date_of_birth} · "
        f"Email: {user.email} · Telegram: {user.telegram_chat_id or 'None'}"
    )


if __name__ == "__main__":
    main()
