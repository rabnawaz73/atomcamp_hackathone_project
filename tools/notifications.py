import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from healthguardian.config import get_settings

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER = (
    "⚠️ **Medical Disclaimer:** I am an AI assistant, not a licensed medical professional. "
    "This information is for educational purposes only. For serious symptoms, emergencies, "
    "or persistent health concerns, please consult a qualified healthcare provider immediately."
)


def send_telegram_message(chat_id: str, body: str, log_action: str = None, user_id: int = None) -> dict:
    """Send a Telegram message via the Bot API. Returns status dict."""
    settings = get_settings()

    if not settings.telegram_bot_token:
        logger.info("Telegram not configured — simulating message to %s", chat_id)
        return {"success": True, "simulated": True, "to": chat_id, "body_preview": body[:200]}

    try:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": body,
        }
        if log_action and user_id:
            if log_action == "daily_plan":
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [
                            {"text": "🏃 Exercise (+20)", "callback_data": f"log:{user_id}:exercise"},
                            {"text": "🍳 Breakfast (+15)", "callback_data": f"log:{user_id}:breakfast"}
                        ],
                        [
                            {"text": "🥗 Lunch (+15)", "callback_data": f"log:{user_id}:lunch"},
                            {"text": "🍽️ Dinner (+15)", "callback_data": f"log:{user_id}:dinner"}
                        ],
                        [
                            {"text": "🍎 Snacks (+15)", "callback_data": f"log:{user_id}:snacks"},
                            {"text": "💧 Hydration (+10)", "callback_data": f"log:{user_id}:hydration"}
                        ],
                        [
                            {"text": "😴 Sleep (+10)", "callback_data": f"log:{user_id}:sleep"},
                            {"text": "🧘 Relax (+10)", "callback_data": f"log:{user_id}:relaxation"}
                        ]
                    ]
                }
            else:
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "✅ Log Activity & Earn Points", "callback_data": f"log:{user_id}:{log_action}"}]
                    ]
                }
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            return {"success": False, "error": f"{response.status_code} - {response.text}"}
            
        return {"success": True, "simulated": False, "to": chat_id}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def send_email_message(to_email: str, subject: str, body: str, log_action: str = None, user_id: int = None) -> dict:
    """Send an Email message via SMTP. Returns status dict."""
    settings = get_settings()

    if not all([settings.smtp_server, settings.smtp_username, settings.smtp_password]):
        logger.info("SMTP not configured — simulating email to %s", to_email)
        return {"success": True, "simulated": True, "to": to_email, "body_preview": body[:200]}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_username
        msg["To"] = to_email

        msg.attach(MIMEText(body, "plain"))
        
        if log_action and user_id:
            from healthguardian.utils.ngrok import get_public_url
            public_url = get_public_url()
            btn_style = "display: inline-block; margin-bottom: 5px; margin-right: 5px; padding: 8px 12px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; font-family: sans-serif; font-size: 14px; font-weight: bold;"
            
            if log_action == "daily_plan":
                html_body = f"<p>{body.replace(chr(10), '<br>')}</p><br><b>✅ Log Activities to Earn Points:</b><br><br>"
                
                buttons = [
                    ("🏃 Exercise (+20)", "exercise"),
                    ("🍳 Breakfast (+15)", "breakfast"),
                    ("🥗 Lunch (+15)", "lunch"),
                    ("🍽️ Dinner (+15)", "dinner"),
                    ("🍎 Snacks (+15)", "snacks"),
                    ("💧 Hydration (+10)", "hydration"),
                    ("😴 Sleep (+10)", "sleep"),
                    ("🧘 Relax (+10)", "relaxation")
                ]
                
                for text, action in buttons:
                    html_body += f"<a href='{public_url}/?log_action={action}&user_id={user_id}' style='{btn_style}'>{text}</a>"
                
                msg.attach(MIMEText(html_body, "html"))
            else:
                magic_link = f"{public_url}/?log_action={log_action}&user_id={user_id}"
                html_body = f"<p>{body.replace(chr(10), '<br>')}</p><br><a href='{magic_link}' style='{btn_style}'>✅ Log Activity & Earn Points</a>"
                msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

        return {"success": True, "simulated": False, "to": to_email}
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return {"success": False, "error": str(exc)}


def format_daily_plan_message(plan: dict) -> str:
    """Format a daily wellness plan as a notification-friendly message."""
    lines = ["🌿 *Your HealthGuardian Daily Plan*", ""]

    sections = [
        ("wake_up", "⏰ Wake Up"),
        ("exercise", "🏃 Exercise"),
        ("breakfast", "🍳 Breakfast"),
        ("lunch", "🥗 Lunch"),
        ("dinner", "🍽️ Dinner"),
        ("snacks", "🍎 Snacks"),
        ("hydration", "💧 Hydration"),
        ("relaxation", "🧘 Relaxation"),
        ("sleep", "😴 Sleep"),
    ]

    for key, label in sections:
        value = plan.get(key)
        if value:
            if isinstance(value, dict):
                time_val = value.get("time", "")
                time_str = ", ".join(time_val) if isinstance(time_val, list) else str(time_val)
                detail = (
                    value.get("activity") 
                    or value.get("meal") 
                    or value.get("notes")
                    or value.get("details")
                    or value.get("description")
                    or ""
                )
                if not detail:
                    detail = ", ".join(str(v) for k, v in value.items() if k not in ("time", "reminders", "target_litres", "indoor", "duration_minutes"))
                lines.append(f"{label}: {time_str} — {detail}")
            else:
                lines.append(f"{label}: {value}")

    lines.extend(["", "Stay healthy! 💪 — HealthGuardian AI"])
    return "\n".join(lines)


def format_reminder_message(task: str, time_str: str) -> str:
    return f"⏰ *HealthGuardian Reminder* ({time_str})\n\n{task}\n\nYou've got this! 💪"
