from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = scoped_session(sessionmaker(bind=engine))

class WatchlistItem(Base):
    __tablename__ = 'watchlist'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    item_id = Column(Integer, nullable=False)
    item_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)

class Subscriber(Base):
    __tablename__ = 'subscribers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)

Base.metadata.create_all(engine)

@contextmanager
def session_scope():
    """提供一个事务范围的会话"""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def is_in_watchlist(user_id: int, item_id: int, item_type: str) -> bool:
    with session_scope() as session:
        return session.query(WatchlistItem).filter_by(
            user_id=user_id, item_id=item_id, item_type=item_type
        ).first() is not None

def add_to_watchlist(user_id: int, item_id: int, item_type: str, title: str) -> None:
    with session_scope() as session:
        watchlist_item = WatchlistItem(user_id=user_id, item_id=item_id, item_type=item_type, title=title)
        session.add(watchlist_item)

def get_watchlist(user_id: int) -> list:
    with session_scope() as session:
        return session.query(WatchlistItem).filter_by(user_id=user_id).all()

def remove_from_watchlist(user_id: int, item_id: int) -> bool:
    with session_scope() as session:
        item = session.query(WatchlistItem).filter_by(user_id=user_id, item_id=item_id).first()
        if item:
            session.delete(item)
            return True
        return False

def add_subscriber(user_id: int) -> None:
    with session_scope() as session:
        if not session.query(Subscriber).filter_by(user_id=user_id).first():
            subscriber = Subscriber(user_id=user_id)
            session.add(subscriber)

def get_all_subscribers() -> list:
    with session_scope() as session:
        return [subscriber.user_id for subscriber in session.query(Subscriber).all()]