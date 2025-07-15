# ✅ backend/models/master_piece.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base

class MasterPiece(Base):
    __tablename__ = "master_piece"

    id = Column(String(1), primary_key=True)  # 例: 'A', 'B', 'C' など
    name = Column(String(32), nullable=False)
    shape_json = Column(JSONB, nullable=False)
