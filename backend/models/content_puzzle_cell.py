from sqlalchemy import Column, SmallInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, CHAR
import uuid

from .base import Base

class ContentPuzzleCell(Base):
    __tablename__ = "content_puzzle_cell"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("content_puzzle.id", ondelete="CASCADE"), nullable=False)
    x = Column(SmallInteger, nullable=False)
    y = Column(SmallInteger, nullable=False)
    z = Column(SmallInteger, nullable=False)
    value = Column(CHAR(1), ForeignKey("master_piece.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("puzzle_id", "x", "y", "z", name="uq_content_puzzle_cell"),
    )
