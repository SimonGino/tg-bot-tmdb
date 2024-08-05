from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class WatchlistItem(Base):
    __tablename__ = 'watchlist'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    item_id = Column(Integer, nullable=False)
    item_type = Column(String, nullable=False)  # 'movie' or 'tv'
    title = Column(String, nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


def add_to_watchlist(user_id: int, item_id: int, item_type: str, title: str) -> None:
    """
    Add an item to the user's watchlist.

    :param user_id: Telegram user ID
    :param item_id: TMDB movie or TV show ID
    :param item_type: 'movie' or 'tv'
    :param title: Title of the movie or TV show
    """
    session = Session()
    watchlist_item = WatchlistItem(user_id=user_id, item_id=item_id, item_type=item_type, title=title)
    session.add(watchlist_item)
    session.commit()
    session.close()


def get_watchlist(user_id: int) -> list:
    """
    Get the watchlist for a specific user.

    :param user_id: Telegram user ID
    :return: List of watchlist items
    """
    session = Session()
    watchlist = session.query(WatchlistItem).filter_by(user_id=user_id).all()
    session.close()
    return watchlist


def remove_from_watchlist(user_id: int, item_id: int) -> bool:
    """
    Remove an item from the user's watchlist.

    :param user_id: Telegram user ID
    :param item_id: TMDB movie or TV show ID
    :return: True if item was removed, False if not found
    """
    session = Session()
    item = session.query(WatchlistItem).filter_by(user_id=user_id, item_id=item_id).first()
    if item:
        session.delete(item)
        session.commit()
        session.close()
        return True
    session.close()
    return False