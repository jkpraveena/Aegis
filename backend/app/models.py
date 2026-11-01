from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, JSON, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class AnalysisRun(Base):
    __tablename__="analysis_runs"
    id: Mapped[str]=mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str]=mapped_column(String(128), index=True)
    query: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(24), default="completed")
    result: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

class Document(Base):
    __tablename__="documents"
    id: Mapped[str]=mapped_column(String(36), primary_key=True)
    filename: Mapped[str]=mapped_column(String(255))
    content_type: Mapped[str]=mapped_column(String(120))
    content_hash: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    text: Mapped[str]=mapped_column(Text)
    chunk_count: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class DocumentChunk(Base):
    __tablename__="document_chunks"
    id: Mapped[str]=mapped_column(String(36), primary_key=True)
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int]=mapped_column(Integer)
    text: Mapped[str]=mapped_column(Text)
    embedding: Mapped[list|None]=mapped_column(JSON, nullable=True)
    __table_args__=(UniqueConstraint("document_id","chunk_index"),)

class Dataset(Base):
    __tablename__="datasets"
    id: Mapped[str]=mapped_column(String(36), primary_key=True)
    filename: Mapped[str]=mapped_column(String(255))
    content_hash: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    columns: Mapped[list]=mapped_column(JSON)
    rows: Mapped[list]=mapped_column(JSON)
    row_count: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
