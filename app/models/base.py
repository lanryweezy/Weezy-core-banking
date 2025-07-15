import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declared_attr
from app.db import Base as DbBase # Alias to avoid naming conflict

class Base(DbBase):
    __abstract__ = True  # This tells SQLAlchemy not to create a table for this class

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + "s" # Convention: class User -> table users

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
