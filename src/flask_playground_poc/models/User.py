from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from flask_playground_poc.db import Base as SqlBase


class User(SqlBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    # One-to-one relationship with UserInfo
    user_info = relationship(
        "UserInfo", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
