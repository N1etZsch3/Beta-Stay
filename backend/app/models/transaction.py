from sqlalchemy import Integer, Float, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("property.id"), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入住日期")
    actual_price: Mapped[float] = mapped_column(Float, nullable=False, comment="实际成交价")
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="来源平台")
    advance_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="提前预订天数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
