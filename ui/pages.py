import streamlit as st
from datetime import date

from healthguardian.database.repository import (
    add_health_points,
    authenticate_user,
    create_user,
    get_activity_feed,
    get_chat_history,
    get_latest_plan,
    get_user_by_id,
    log_activity,
    save_chat_message,
    save_daily_plan,
)
from healthguardian.utils.auth import validate_age_range, validate_email


def init_session_state():
    defaults = {
        "authenticated": False,
        "user_id": None,
        "page": "login",
        "generating_plan": False,
        "agent_status": "",
        "agent_progress": 0.0,
        "chat_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_login_page():
    st.markdown("### Welcome back")
    st.caption("Sign in to access your personalised wellness dashboard.")

    with st.form("login_form"):
        identifier = st.text_input(
            "Email or Telegram Chat ID",
            placeholder="you@email.com or 123456789",
        )
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            if not identifier or not password:
                st.error("Please enter your credentials.")
                return

            user = authenticate_user(identifier.strip(), password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user.id
                st.session_state.page = "dashboard"
                st.session_state.chat_messages = []
                st.toast(f"Welcome back, {user.full_name}!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    st.divider()
    if st.button("Don't have an account? Sign Up", use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()


def render_signup_page():
    st.markdown("### Create your HealthGuardian profile")
    st.caption("Tell us about yourself so our AI agents can personalise your wellness journey.")

    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *")
            date_of_birth = st.date_input(
                "Date of Birth *",
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                value=date(2000, 1, 1),
            )
            email = st.text_input("Email *")
            telegram_chat_id = st.text_input("Telegram Chat ID (optional)", help="Get this by messaging @userinfobot on Telegram")
            notification_preference = st.selectbox("Send Notifications Via", ["email", "telegram", "both"])
        with col2:
            height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
            weight = st.number_input("Weight (kg)", min_value=30, max_value=300, value=70)
            password = st.text_input("Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")

        st.markdown("**Health Information**")
        col3, col4 = st.columns(2)
        with col3:
            allergies = st.text_area("Known Allergies", placeholder="e.g. Peanuts, shellfish")
            chronic = st.text_area(
                "Chronic Conditions",
                placeholder="e.g. Diabetes, hypertension",
            )
        with col4:
            medications = st.text_area("Current Medications", placeholder="e.g. Metformin 500mg")
            emergency = st.text_input("Emergency Contact", placeholder="Name & phone number")

        consent = st.checkbox(
            "I consent to HealthGuardian storing my health data securely and using it "
            "to generate personalised wellness plans. I understand this is not a substitute "
            "for professional medical advice.",
        )

        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if not full_name:
                errors.append("Full name is required.")
            if not email or not validate_email(email):
                errors.append("Valid email required.")
            if notification_preference in ["telegram", "both"] and not telegram_chat_id:
                errors.append("Telegram Chat ID is required if selected for notifications.")
            if not validate_age_range(str(date_of_birth)):
                errors.append("Age must be between 13 and 120.")
            if not password or len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != confirm_password:
                errors.append("Passwords do not match.")
            if not consent:
                errors.append("You must consent to data processing.")

            if errors:
                for err in errors:
                    st.error(err)
                return

            try:
                user = create_user(
                    full_name=full_name,
                    date_of_birth=str(date_of_birth),
                    password=password,
                    email=email.strip(),
                    telegram_chat_id=telegram_chat_id.strip() if telegram_chat_id else None,
                    notification_preference=notification_preference,
                    height_cm=int(height),
                    weight_kg=int(weight),
                    allergies=allergies,
                    chronic_conditions=chronic,
                    medications=medications,
                    emergency_contact=emergency,
                )
                log_activity(user.id, "signup", "Account created successfully")
                st.session_state.authenticated = True
                st.session_state.user_id = user.id
                st.session_state.page = "dashboard"
                st.toast("Account created! Welcome to HealthGuardian AI.")
                st.rerun()
            except Exception as exc:
                st.error(f"Registration failed: {exc}")

    st.divider()
    if st.button("Already have an account? Sign In", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()


def _format_plan_section(key: str, data) -> str:
    icons = {
        "wake_up": "⏰",
        "exercise": "🏃",
        "breakfast": "🍳",
        "lunch": "🥗",
        "dinner": "🍽️",
        "snacks": "🍎",
        "hydration": "💧",
        "relaxation": "🧘",
        "sleep": "😴",
    }
    icon = icons.get(key, "📌")
    label = key.replace("_", " ").title()

    if isinstance(data, dict):
        time_val = data.get("time", "")
        time_str = ", ".join(time_val) if isinstance(time_val, list) else str(time_val)
        detail = (
            data.get("activity")
            or data.get("meal")
            or data.get("notes")
            or data.get("target_litres")
            or data.get("details")
            or data.get("description")
            or ""
        )
        if not detail:
            detail = ", ".join(str(v) for k, v in data.items() if k not in ("time", "reminders", "target_litres", "indoor", "duration_minutes"))
        if key == "hydration" and "reminders" in data:
            detail = f"{data.get('target_litres', 2.5)}L — reminders at {', '.join(data['reminders'])}"
        if time_str:
            return f"**{icon} {label}** ({time_str}): {detail}"
        return f"**{icon} {label}**: {detail}"
    return f"**{icon} {label}**: {data}"


def render_dashboard(user):
    from healthguardian.agents.crew import run_medical_consultation, run_plan_generation_workflow
    from healthguardian.database.repository import user_profile_dict
    from healthguardian.services.llm import stream_chat_completion
    from healthguardian.services.scheduler import dispatch_notification
    from healthguardian.tools.notifications import format_daily_plan_message

    profile = user_profile_dict(user)
    latest_plan = get_latest_plan(user.id)
    city_report = latest_plan.city_report if latest_plan else None

    if city_report:
        loc = city_report.get("location", {})
        weather = city_report.get("weather", {})
        aqi = city_report.get("air_quality", {})
        st.markdown(
            f'<div class="weather-banner">🌤️ Current in <strong>{loc.get("city", "your city")}</strong>: '
            f'{weather.get("temperature_c", "—")}°C, {weather.get("description", "—")}, '
            f'AQI {aqi.get("aqi", "—")} ({aqi.get("category", "—")})</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Generate your first wellness plan to see local conditions.")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 📋 Today's Wellness Plan")

        if latest_plan and latest_plan.plan_data:
            plan = latest_plan.plan_data
            for key in [
                "wake_up", "exercise", "breakfast", "lunch",
                "dinner", "snacks", "hydration", "relaxation", "sleep",
            ]:
                if key in plan:
                    st.markdown(_format_plan_section(key, plan[key]))

            if plan.get("health_tip"):
                st.success(f"💡 **Tip:** {plan['health_tip']}")
        else:
            st.markdown(
                "*No plan yet. Click **Generate Today's Plan** to let our AI agents "
                "create your personalised routine.*"
            )

        st.markdown("#### ✅ Log Daily Progress")
        with st.expander("Log an activity to earn points!", expanded=False):
            with st.form("log_activity_form"):
                activity_type = st.selectbox(
                    "Activity Completed",
                    ["Exercise (+20 pts)", "Breakfast (+15 pts)", "Lunch (+15 pts)", "Dinner (+15 pts)", "Snacks (+15 pts)", "Hydration (+10 pts)", "Sleep (+10 pts)", "Relaxation (+10 pts)"]
                )
                notes = st.text_input("Optional Notes")
                submitted_log = st.form_submit_button("Log Activity", type="primary")
                if submitted_log:
                    pts = 10
                    action = "hydration"
                    if "Exercise" in activity_type: pts, action = 20, "exercise"
                    elif "Breakfast" in activity_type: pts, action = 15, "breakfast"
                    elif "Lunch" in activity_type: pts, action = 15, "lunch"
                    elif "Dinner" in activity_type: pts, action = 15, "dinner"
                    elif "Snacks" in activity_type: pts, action = 15, "snacks"
                    elif "Sleep" in activity_type: pts, action = 10, "sleep"
                    elif "Relaxation" in activity_type: pts, action = 10, "relaxation"
                    
                    add_health_points(user.id, pts)
                    log_msg = f"Logged {action} via Dashboard (+{pts} pts)"
                    if notes: log_msg += f" - {notes}"
                    log_activity(user.id, "dashboard_log", log_msg)
                    st.toast(f"✅ {action.title()} logged! You earned {pts} points.")
                    st.rerun()

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🔄 Generate Today's Plan", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_status(msg: str, progress: float):
                    status_text.markdown(f"*{msg}*")
                    progress_bar.progress(min(progress, 1.0))

                with st.spinner("Agents at work..."):
                    plan, city = run_plan_generation_workflow(
                        profile,
                        profile.get("city_override"),
                        status_callback=update_status,
                    )
                    save_daily_plan(user.id, plan, city)
                    add_health_points(user.id, 10)
                    log_activity(user.id, "plan", "Generated new daily wellness plan")
                    progress_bar.progress(1.0)
                    status_text.markdown("*✅ Plan generated successfully!*")

                st.toast("Your wellness plan is ready!")
                st.rerun()

        with btn_col2:
            if st.button("📨 Send Plan", use_container_width=True):
                if not latest_plan:
                    st.warning("Generate a plan first.")
                else:
                    msg = format_daily_plan_message(latest_plan.plan_data)
                    result = dispatch_notification(user, "Your HealthGuardian Daily Plan", msg, log_action="daily_plan")
                    if result.get("success"):
                        mode = "simulated" if result.get("simulated") else "sent"
                        log_activity(user.id, "notification", f"Plan {mode} via {getattr(user, 'notification_preference', 'email')}")
                        st.toast("Plan sent!")
                    else:
                        st.error(f"Failed to send plan: {result.get('error', 'Unknown error')}")

    with col_right:
        st.markdown("#### 💬 Medical Consultant")
        st.markdown(
            '<div class="disclaimer-box">'
            "This AI provides general health information only — not medical diagnosis or treatment."
            "</div>",
            unsafe_allow_html=True,
        )

        if not st.session_state.chat_messages:
            history = get_chat_history(user.id)
            st.session_state.chat_messages = [
                {"role": msg.role, "content": msg.content} for msg in history
            ]

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a health question..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            save_chat_message(user.id, "user", prompt)

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                history_for_llm = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_messages[:-1]
                ]

                from healthguardian.services.rag import get_rag_context
                from healthguardian.agents.crew import MEDICAL_DISCLAIMER

                rag_context = get_rag_context(prompt)
                system_msg = {
                    "role": "system",
                    "content": (
                        f"You are HealthGuardian Medical Consultant. User: {profile['full_name']}, "
                        f"age {profile['age']}. Conditions: {profile.get('chronic_conditions') or 'None'}. "
                        f"Allergies: {profile.get('allergies') or 'None'}.\n\n"
                        f"Knowledge:\n{rag_context}\n\n"
                        f"Always end with: {MEDICAL_DISCLAIMER}"
                    ),
                }
                messages = [system_msg] + history_for_llm + [{"role": "user", "content": prompt}]

                try:
                    response_text = st.write_stream(stream_chat_completion(messages))
                except Exception:
                    response_text = run_medical_consultation(profile, prompt, history_for_llm)
                    st.markdown(response_text)

            st.session_state.chat_messages.append({"role": "assistant", "content": response_text})
            save_chat_message(user.id, "assistant", response_text)

    st.divider()

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    with summary_col1:
        st.markdown("#### 📊 Health Summary")
        st.metric("Weight", f"{profile.get('weight_kg') or '—'} kg")
        if profile.get("height_cm") and profile.get("weight_kg"):
            bmi = profile["weight_kg"] / ((profile["height_cm"] / 100) ** 2)
            st.metric("BMI", f"{bmi:.1f}")

    with summary_col2:
        points = profile.get("health_points", 0)
        st.markdown("#### 🏆 Health Points")
        st.metric("Total Points", points)
        progress_pct = min(points % 100, 100)
        st.markdown(
            f'<div class="health-points-bar"><div class="health-points-fill" '
            f'style="width: {progress_pct}%"></div></div>',
            unsafe_allow_html=True,
        )
        st.caption(f"{progress_pct}/100 to next milestone")

    with summary_col3:
        st.markdown("#### 📜 Activity Feed")
        activities = get_activity_feed(user.id, limit=8)
        if activities:
            for act in activities:
                ts = act.created_at.strftime("%b %d, %H:%M") if act.created_at else ""
                st.caption(f"**{act.activity_type.title()}** · {ts}")
                st.caption(act.description)
        else:
            st.caption("No activity yet.")
