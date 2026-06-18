import re
from datetime import date

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def validate_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def calculate_age(date_of_birth: str) -> int:
    dob = date.fromisoformat(date_of_birth)
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def validate_age_range(date_of_birth: str, min_age: int = 13, max_age: int = 120) -> bool:
    try:
        age = calculate_age(date_of_birth)
        return min_age <= age <= max_age
    except ValueError:
        return False
