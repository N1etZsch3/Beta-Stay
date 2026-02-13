from sqlalchemy import Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pricing_record_id: Mapped[int] = mapped_column(Integer, ForeignKey("pricing_record.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="采纳/拒绝/调整")
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="实际采用价格")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
