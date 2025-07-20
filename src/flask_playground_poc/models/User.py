
from sqlalchemy import Column, Integer, String

from flask_playground_poc.db import Base as SqlBase


class User(SqlBase):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name =  Column(String(50))