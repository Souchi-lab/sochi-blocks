# ✅ backend/models/master_puzzle_type.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class MasterPuzzleType(Base):
    __tablename__ = "master_puzzle_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
