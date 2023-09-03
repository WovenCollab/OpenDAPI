# pylint: disable=too-few-public-methods
"""SQLAlchemy ORM models for testing."""

from typing import List
from typing import Optional
from sqlalchemy import ForeignKey, MetaData
from sqlalchemy import String, Column, Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""

    metadata = MetaData(schema="my_schema")


class User(Base):
    """User model."""

    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]
    addresses: Mapped[List["Address"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Address(Base):
    """Address model."""

    __tablename__ = "address"
    id = Column(Integer, primary_key=True)
    legacy_name = Column(String(50))
    email_address: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="addresses")
