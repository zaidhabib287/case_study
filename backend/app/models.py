from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime

class Base(DeclarativeBase):
    pass

class Application(Base):
    __tablename__ = "applications"
    application_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name:    Mapped[str] = mapped_column(String(200), nullable=False)
    age:          Mapped[int] = mapped_column(Integer, nullable=False)
    address:      Mapped[str] = mapped_column(String(500), nullable=False)
    region_code:  Mapped[str | None] = mapped_column(String(16), nullable=True)
    employment_status: Mapped[str] = mapped_column(String(32), default="employed")
    net_monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_obligations_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    dependents_under_12: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="application", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id:           Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id", ondelete="CASCADE"), index=True)
    filename:     Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes:   Mapped[int | None] = mapped_column(Integer)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_preview: Mapped[str | None] = mapped_column(String(400))
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="documents")

class Decision(Base):
    __tablename__ = "decisions"
    id:             Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id", ondelete="CASCADE"), index=True)
    status:         Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility_label: Mapped[str] = mapped_column(String(32), nullable=False)
    probability:    Mapped[float] = mapped_column(Float, nullable=False)
    rationale:      Mapped[str] = mapped_column(Text, nullable=False)
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="decisions")
