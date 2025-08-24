from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    profile = relationship("Profile", back_populates="owner", uselist=False)
    chats = relationship("ChatHistory", back_populates="owner")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    expertise = Column(String, nullable=True)
    time = Column(Integer, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="profile")


class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    content = Column(Text)

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="chats")
