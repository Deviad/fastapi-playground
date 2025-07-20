from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from flask_playground_poc.db import Base as SqlBase


class UserInfo(SqlBase):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)

    # Relationship back to User
    user = relationship("User", back_populates="user_info")
