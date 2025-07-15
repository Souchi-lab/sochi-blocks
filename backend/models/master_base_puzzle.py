from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base

class MasterBasePuzzle(Base):
    __tablename__ = "master_base_puzzle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    puzzle_type_id = Column(UUID(as_uuid=True), ForeignKey("master_puzzle_type.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("master_user.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
