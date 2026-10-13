"""Pydantic schemas (LLM outputs, spec section 6) and SQLAlchemy tables."""
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, field_validator
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

EMBED_DIM = 2048  # nemotron-3-embed-1b

DocType = Literal["rejection_letter", "policy", "discharge_summary", "bill", "other"]


def mask_policy_no(value: str) -> str:
    return "****" + value.replace("*", "")[-4:]


# ---------- LLM output schemas ----------


class DocClass(BaseModel):
    doc_type: DocType


class Rejection(BaseModel):
    insurer: str
    claim_no: str
    policy_no_masked: str  # keep last 4 only; masked in code, never trusted to the LLM
    policy_start_date: date | None  # added to spec schema: dates.py needs it, letters usually state it
    rejection_date: date
    reason_text: str  # verbatim
    cited_clauses: list[str]  # e.g. ["4.1", "Exclusion 3"]
    reason_type: Literal["pre_existing", "waiting_period", "non_disclosure", "not_medically_necessary", "other"]

    @field_validator("policy_no_masked")
    @classmethod
    def _mask(cls, v: str) -> str:
        return mask_policy_no(v)

    @field_validator("cited_clauses")
    @classmethod
    def _strip_prefix(cls, v: list[str]) -> list[str]:
        return [re.sub(r"(?i)^(clause|section)\s*", "", c).strip() for c in v]


class MedicalFacts(BaseModel):
    diagnosis: str
    admission_date: date
    discharge_date: date
    history_mentioned: list[str]  # verbatim phrases, e.g. "k/c/o HTN 2 yrs"
    procedures: list[str]


ClauseTag = Literal["definition", "exclusion", "waiting_period", "sub_limit", "procedure", "other"]


class Clause(BaseModel):
    clause_no: str
    text: str
    tag: ClauseTag


class ClauseTags(BaseModel):
    tags: dict[str, ClauseTag]  # clause_no -> tag


class Verdict(BaseModel):
    outcome: Literal["contestable", "likely_valid", "unclear"]
    confidence: Literal["low", "medium", "high"]
    reasons: list[str]  # each must cite a clause id or a fact
    clause_ids: list[int]
    source_ids: list[int]
    missing_documents: list[str]


# ---------- Database ----------


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)


class ClauseRow(Base):
    __tablename__ = "clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    clause_no: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    tag: Mapped[str] = mapped_column(String(32))
    # ponytail: no ANN index (pgvector caps HNSW at 2000 dims); exact scan is fine for one policy per case
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))


class LLMCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    tier: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(engine, expire_on_commit=False)


def init_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
