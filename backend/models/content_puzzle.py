from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base

class ContentPuzzle(Base):
    __tablename__ = "content_puzzle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_puzzle_id = Column(UUID(as_uuid=True), ForeignKey("master_base_puzzle.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(16), unique=True, nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text)
    difficulty_id = Column(UUID(as_uuid=True), ForeignKey("master_difficulty.id"), nullable=False)
    puzzle_type_id = Column(UUID(as_uuid=True), ForeignKey("master_puzzle_type.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("master_user.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
