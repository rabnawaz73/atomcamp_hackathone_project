import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from healthguardian.agents.crew import run_plan_generation_workflow
from healthguardian.database import get_db_session
from healthguardian.database.models import User
from healthguardian.database.repository import (
    get_latest_plan,
    log_activity,
    save_daily_plan,
    user_profile_dict,
)
from healthguardian.tools.notifications import format_daily_plan_message, format_reminder_message, send_telegram_message, send_email_message

def dispatch_notification(user, subject: str, message: str, log_action: str = None) -> dict:
    pref = getattr(user, "notification_preference", "email")
    if pref == "telegram" and getattr(user, "telegram_chat_id", None):
        return send_telegram_message(user.telegram_chat_id, message, log_action, user.id)
    elif pref == "both":
        res_email = send_email_message(user.email, subject, message, log_action, user.id)
        res_tg = {}
        if getattr(user, "telegram_chat_id", None):
            res_tg = send_telegram_message(user.telegram_chat_id, message, log_action, user.id)
        return {"success": res_email.get("success") or res_tg.get("success")}
    else:
        return send_email_message(user.email, subject, message, log_action, user.id)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


from datetime import datetime
from dateutil import parser
from apscheduler.triggers.date import DateTrigger

def _send_task_reminder(user_id: int, task_key: str, message: str):
    from healthguardian.database.repository import get_user_by_id
    user = get_user_by_id(user_id)
    if user:
        dispatch_notification(user, f"HealthGuardian Reminder: {task_key.replace('_', ' ').title()}", message, log_action=task_key)

def schedule_daily_tasks_for_user(user_id: int, plan_data: dict):
    global _scheduler
    if not _scheduler:
        return

    for job in _scheduler.get_jobs():
        if job.id.startswith(f"task_{user_id}_"):
            _scheduler.remove_job(job.id)

    now = datetime.now()
    
    for key in ["wake_up", "exercise", "breakfast", "lunch", "dinner", "relaxation", "sleep"]:
        task_info = plan_data.get(key)
        if isinstance(task_info, dict):
            time_val = task_info.get("time")
            time_str = ", ".join(time_val) if isinstance(time_val, list) else str(time_val)
            if time_str:
                try:
                    parsed_time = parser.parse(time_str).time()
                    run_date = datetime.combine(now.date(), parsed_time)
                    
                    if run_date > now:
                        detail = task_info.get("activity") or task_info.get("meal") or task_info.get("notes") or ""
                        msg = f"⏰ Time for {key.replace('_', ' ').title()}:\n{detail}"
                        _scheduler.add_job(
                            _send_task_reminder,
                            DateTrigger(run_date=run_date),
                            args=[user_id, key, msg],
                            id=f"task_{user_id}_{key}"
                        )
                except Exception as exc:
                    logger.warning("Could not parse time '%s' for task '%s': %s", time_str, key, exc)

def _send_morning_plans():
    """Generate and send daily plans to all users at scheduled time."""
    logger.info("Running scheduled morning plan generation")
    with get_db_session() as session:
        users = session.query(User).all()

    for user in users:
        try:
            profile = user_profile_dict(user)
            plan, city_report = run_plan_generation_workflow(profile, user.city_override)
            save_daily_plan(user.id, plan, city_report)
            schedule_daily_tasks_for_user(user.id, plan)

            message = format_daily_plan_message(plan)
            result = dispatch_notification(user, "Your HealthGuardian Daily Plan", message)

            status = "sent" if result.get("success") else "failed"
            log_activity(
                user.id,
                "notification",
                f"Morning plan {status} via {getattr(user, 'notification_preference', 'email')}",
            )
        except Exception as exc:
            logger.error("Failed morning plan for user %s: %s", user.id, exc)


def _send_hydration_reminders():
    """Send hydration reminders to users with plans."""
    with get_db_session() as session:
        users = session.query(User).all()

    for user in users:
        plan = get_latest_plan(user.id)
        if not plan:
            continue
        hydration = plan.plan_data.get("hydration", {})
        reminders = hydration.get("reminders", [])
        if reminders:
            msg = format_reminder_message(
                f"Time for a water break! Target: {hydration.get('target_litres', 2.5)}L today.",
                reminders[0] if reminders else "now",
            )
            dispatch_notification(user, "HealthGuardian Hydration Reminder", msg)


def start_scheduler():
    """Start background scheduler for daily plans and reminders."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from healthguardian.services.telegram_bot import start_telegram_bot
    start_telegram_bot()

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_send_morning_plans, CronTrigger(hour=6, minute=0), id="morning_plans")
    _scheduler.add_job(_send_hydration_reminders, CronTrigger(hour=10, minute=0), id="hydration_am")
    _scheduler.add_job(_send_hydration_reminders, CronTrigger(hour=14, minute=0), id="hydration_pm")
    _scheduler.start()
    logger.info("HealthGuardian scheduler started")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
