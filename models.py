from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Faculty(Base):
    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    submissions = Column(Integer, default=0)

    forms = relationship("FormEntry", back_populates="faculty")

class FormEntry(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    template = Column(String)
    faculty_id = Column(Integer, ForeignKey("faculties.id"))

    faculty = relationship("Faculty", back_populates="forms")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    faculty_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

