import os
from sqlalchemy import create_engine, Column, Integer, BigInteger, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# זהו קובץ הניהול של מסד הנתונים. 
# הוא יודע לדבר עם כל מסד נתונים שתביא לו בקישור.

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True) # מזהה הטלגרם
    has_used_free = Column(Boolean, default=False) # האם קיבל 10 שורות חינם
    is_premium = Column(Boolean, default=False)    # האם שילם מנוי

# מקבל את הקישור למסד הנתונים מהגדרות השרת
DATABASE_URL = os.getenv('DATABASE_URL')

# אם אין קישור (בדיקה מקומית), הוא יוצר קובץ קטן במחשב
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./local_test.db"
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def get_user_status(user_id):
    """בודק מה המצב של המשתמש: האם השתמש בחינם והאם הוא פרימיום"""
    session = SessionLocal()
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        session.add(user)
        session.commit()
    
    result = {
        "has_used_free": user.has_used_free,
        "is_premium": user.is_premium
    }
    session.close()
    return result

def mark_free_used(user_id):
    """מסמן שהמשתמש ניצל את ה-10 שורות חינם שלו"""
    session = SessionLocal()
    user = session.query(User).filter(User.user_id == user_id).first()
    if user:
        user.has_used_free = True
        session.commit()
    session.close()
