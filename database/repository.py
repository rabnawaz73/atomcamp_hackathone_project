import json
import logging
from typing import Any

from healthguardian.database import get_db_session
from healthguardian.database.models import ActivityLog, ChatMessage, DailyPlan, User
from healthguardian.utils.auth import hash_password

logger = logging.getLogger(__name__)


def create_user(
    *,
    full_name: str,
    date_of_birth: str,
    password: str,
    telegram_chat_id: str | None = None,
    notification_preference: str = "email",
    email: str | None = None,
    height_cm: int | None = None,
    weight_kg: int | None = None,
    allergies: str = "",
    chronic_conditions: str = "",
    medications: str = "",
    emergency_contact: str = "",
) -> User:
    with get_db_session() as session:
        user = User(
            email=email or None,
            password_hash=hash_password(password),
            full_name=full_name,
            date_of_birth=date_of_birth,
            telegram_chat_id=telegram_chat_id,
            notification_preference=notification_preference,
            height_cm=height_cm,
            weight_kg=weight_kg,
            allergies=allergies,
            chronic_conditions=chronic_conditions,
            medications=medications,
            emergency_contact=emergency_contact,
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        session.expunge(user)
        return user


def authenticate_user(identifier: str, password: str) -> User | None:
    with get_db_session() as session:
        query = session.query(User)
        if "@" in identifier:
            user = query.filter(User.email == identifier).first()
        else:
            user = query.filter(User.telegram_chat_id == identifier).first()

        if user is None:
            return None

        from healthguardian.utils.auth import verify_password

        if not verify_password(password, user.password_hash):
            return None

        session.expunge(user)
        return user


def get_user_by_id(user_id: int) -> User | None:
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.expunge(user)
        return user


def save_daily_plan(user_id: int, plan_data: dict, city_report: dict | None = None) -> DailyPlan:
    with get_db_session() as session:
        plan = DailyPlan(
            user_id=user_id,
            plan_data=plan_data,
            city_report=city_report,
        )
        session.add(plan)
        session.flush()
        session.refresh(plan)
        session.expunge(plan)
        return plan


def get_latest_plan(user_id: int) -> DailyPlan | None:
    with get_db_session() as session:
        plan = (
            session.query(DailyPlan)
            .filter(DailyPlan.user_id == user_id)
            .order_by(DailyPlan.created_at.desc())
            .first()
        )
        if plan:
            session.expunge(plan)
        return plan


def log_activity(user_id: int, activity_type: str, description: str) -> None:
    with get_db_session() as session:
        session.add(
            ActivityLog(user_id=user_id, activity_type=activity_type, description=description)
        )


def get_activity_feed(user_id: int, limit: int = 20) -> list[ActivityLog]:
    with get_db_session() as session:
        activities = (
            session.query(ActivityLog)
            .filter(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .all()
        )
        for activity in activities:
            session.expunge(activity)
        return activities


def save_chat_message(user_id: int, role: str, content: str) -> None:
    with get_db_session() as session:
        session.add(ChatMessage(user_id=user_id, role=role, content=content))


def get_chat_history(user_id: int, limit: int = 50) -> list[ChatMessage]:
    with get_db_session() as session:
        messages = (
            session.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        for msg in messages:
            session.expunge(msg)
        return messages


def add_health_points(user_id: int, points: int) -> int:
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.health_points = (user.health_points or 0) + points
            return user.health_points
        return 0


def user_profile_dict(user: User) -> dict[str, Any]:
    from healthguardian.utils.auth import calculate_age

    return {
        "id": user.id,
        "full_name": user.full_name,
        "age": calculate_age(user.date_of_birth),
        "date_of_birth": user.date_of_birth,
        "telegram_chat_id": user.telegram_chat_id,
        "notification_preference": user.notification_preference,
        "email": user.email,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "allergies": user.allergies,
        "chronic_conditions": user.chronic_conditions,
        "medications": user.medications,
        "emergency_contact": user.emergency_contact,
        "city_override": user.city_override,
        "health_points": user.health_points or 0,
    }
