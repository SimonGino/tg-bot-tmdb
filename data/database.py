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

class Subscriber(Base):
    __tablename__ = 'subscribers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)


Base.metadata.create_all(engine)

def is_in_watchlist(user_id: int, item_id: int, item_type: str) -> bool:
    """
        Check if an item is already in the user's watchlist.

        :param user_id: Telegram user ID
        :param item_id: TMDB movie or TV show ID
        :param item_type: 'movie' or 'tv'
        :return: True if the item is in the watchlist, False otherwise
        """
    session = Session()
    item = session.query(WatchlistItem).filter_by(
        user_id=user_id,
        item_id=item_id,
        item_type=item_type
    ).first()
    session.close()
    return item is not None

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

def add_subscriber(user_id: int) -> None:
    """
    Add a user to the subscribers list if not already subscribed.

    :param user_id: Telegram user ID
    """
    session = Session()
    existing_subscriber = session.query(Subscriber).filter_by(user_id=user_id).first()
    if not existing_subscriber:
        subscriber = Subscriber(user_id=user_id)
        session.add(subscriber)
        session.commit()
    session.close()

def get_all_subscribers() -> list:
    """
    Get all subscribers' user IDs.

    :return: List of user IDs
    """
    session = Session()
    subscribers = session.query(Subscriber).all()
    session.close()
    return [subscriber.user_id for subscriber in subscribers]