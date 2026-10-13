import json
import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import Column, String, Text, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

# אחסון המשתמשים.
# אם מוגדר DATABASE_URL (למשל Postgres חינמי ב-Neon או Supabase) הנתונים נשמרים שם
# ולא נמחקים בריסטארט. בלי DATABASE_URL נוצר קובץ SQLite מקומי לבדיקות.

LEGACY_JSON_FILE = "users_db.json"

DEFAULT_USER = {
    "agreed_to_terms": False,
    "has_used_free": False,
    "is_premium": False,
    "expiry_date": None,
    "subscription_id": None,
    "free_credits": 0,
    "referred_by": None,
    "referral_awarded": False,
    "first_name": None,
    "last_name": None,
    "username": None,
}

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./local_test.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()


class UserRecord(Base):
    __tablename__ = "lotto_users"
    user_id = Column(String(32), primary_key=True)
    data = Column(Text, nullable=False, default="{}")


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base.metadata.create_all(bind=engine)


def _load(session, user_id):
    record = session.get(UserRecord, user_id)
    if record is None:
        return None, None
    try:
        return record, json.loads(record.data)
    except json.JSONDecodeError:
        return record, {}


def _import_legacy_json():
    """מעביר משתמשים מקובץ users_db.json הישן, פעם אחת, אם הטבלה ריקה."""
    if not os.path.exists(LEGACY_JSON_FILE):
        return
    with SessionLocal() as session:
        if session.execute(select(UserRecord.user_id).limit(1)).first():
            return
        try:
            with open(LEGACY_JSON_FILE, "r", encoding="utf-8") as f:
                legacy = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for user_id, user in legacy.items():
            session.add(UserRecord(user_id=str(user_id), data=json.dumps(user, ensure_ascii=False)))
        session.commit()
        logging.info("Imported %s users from %s", len(legacy), LEGACY_JSON_FILE)


_import_legacy_json()


async def get_user_data(user_id):
    user_id = str(user_id)
    with SessionLocal() as session:
        record, data = _load(session, user_id)
        if record is None:
            data = DEFAULT_USER.copy()
            session.add(UserRecord(user_id=user_id, data=json.dumps(data, ensure_ascii=False)))
            session.commit()
            return data

        missing_defaults = False
        for key, value in DEFAULT_USER.items():
            if key not in data:
                data[key] = value
                missing_defaults = True
        if missing_defaults:
            record.data = json.dumps(data, ensure_ascii=False)
            session.commit()
        return data


async def user_agreed_to_terms(user_id):
    await update_user_data(user_id, {"agreed_to_terms": True})


async def update_user_data(user_id, updates):
    user_id = str(user_id)
    with SessionLocal() as session:
        record, data = _load(session, user_id)
        if record is None:
            data = DEFAULT_USER.copy()
            record = UserRecord(user_id=user_id)
            session.add(record)
        data.update(updates)
        record.data = json.dumps(data, ensure_ascii=False)
        session.commit()


async def get_all_users():
    with SessionLocal() as session:
        users = {}
        for record in session.execute(select(UserRecord)).scalars():
            try:
                users[record.user_id] = json.loads(record.data)
            except json.JSONDecodeError:
                users[record.user_id] = {}
        return users


async def set_user_premium(user_id, sub_id=None, days=31, extend=False):
    """מפעיל VIP ל-days ימים. עם extend=True, מנוי שעדיין בתוקף מוארך מתאריך התפוגה שלו."""
    start = datetime.now()
    if extend:
        user = await get_user_data(user_id)
        try:
            current = datetime.strptime(user.get("expiry_date") or "", "%Y-%m-%d %H:%M:%S")
            if user.get("is_premium") and current > start:
                start = current
        except ValueError:
            pass
    expiry = (start + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    await update_user_data(user_id, {"is_premium": True, "expiry_date": expiry, "subscription_id": sub_id})
    return expiry


async def set_referrer(user_id, referrer_id):
    user_id = str(user_id)
    referrer_id = str(referrer_id)
    if user_id == referrer_id:
        return False

    user = await get_user_data(user_id)
    if user.get("referred_by"):
        return False

    await update_user_data(user_id, {"referred_by": referrer_id})
    return True


async def award_referral_credit(user_id):
    user_id = str(user_id)
    user = await get_user_data(user_id)
    referrer_id = user.get("referred_by")
    if not referrer_id or user.get("referral_awarded"):
        return None

    referrer = await get_user_data(referrer_id)
    credits = int(referrer.get("free_credits", 0) or 0) + 1
    await update_user_data(referrer_id, {"free_credits": credits})
    await update_user_data(user_id, {"referral_awarded": True})
    return referrer_id


async def use_free_credit(user_id):
    user_id = str(user_id)
    user = await get_user_data(user_id)
    credits = int(user.get("free_credits", 0) or 0)
    if credits <= 0:
        return False

    await update_user_data(user_id, {"free_credits": credits - 1})
    return True
