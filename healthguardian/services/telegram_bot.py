import logging
import threading
import time
import requests

from healthguardian.config import get_settings
from healthguardian.database.repository import add_health_points, log_activity

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_bot_thread = None

def _poll_updates():
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.info("Telegram token not set, bot listener disabled.")
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
    offset = None

    logger.info("Telegram long-polling started.")
    while not _stop_event.is_set():
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            resp = requests.get(url, params=params, timeout=40)
            if not resp.ok:
                time.sleep(5)
                continue

            data = resp.json()
            if not data.get("ok"):
                time.sleep(5)
                continue

            for result in data.get("result", []):
                offset = result["update_id"] + 1

                if "callback_query" in result:
                    cq = result["callback_query"]
                    cb_data = cq.get("data", "")
                    if cb_data.startswith("log:"):
                        try:
                            parts = cb_data.split(":")
                            if len(parts) >= 3:
                                user_id_str = parts[1]
                                action = parts[2]
                                user_id = int(user_id_str)

                                # Give points
                                pts = 10
                                if action == "exercise":
                                    pts = 20
                                elif action in ["breakfast", "lunch", "dinner", "snacks"]:
                                    pts = 15

                                add_health_points(user_id, pts)
                                log_activity(user_id, "telegram_log", f"Logged {action} via Telegram (+{pts} pts)")

                                # Answer query
                                requests.post(
                                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/answerCallbackQuery",
                                    json={"callback_query_id": cq["id"], "text": f"✅ Logged! +{pts} points."},
                                    timeout=10
                                )
                                
                                # Edit message to remove button
                                if "message" in cq:
                                    requests.post(
                                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/editMessageReplyMarkup",
                                        json={
                                            "chat_id": cq["message"]["chat"]["id"],
                                            "message_id": cq["message"]["message_id"],
                                            "reply_markup": {"inline_keyboard": []}
                                        },
                                        timeout=10
                                    )
                        except Exception as inner_exc:
                            logger.error("Failed to process callback query: %s", inner_exc)
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.warning("Telegram polling error: %s", e)
            time.sleep(5)

def start_telegram_bot():
    global _bot_thread
    if _bot_thread is None or not _bot_thread.is_alive():
        _stop_event.clear()
        _bot_thread = threading.Thread(target=_poll_updates, daemon=True)
        _bot_thread.start()

def stop_telegram_bot():
    if _bot_thread:
        _stop_event.set()
