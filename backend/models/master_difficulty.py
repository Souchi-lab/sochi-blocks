# ✅ backend/models/master_difficulty.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class MasterDifficulty(Base):
    __tablename__ = "master_difficulty"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
