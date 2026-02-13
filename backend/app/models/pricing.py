from sqlalchemy import Integer, Float, DateTime, JSON, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from app.core.database import Base


class PricingRecord(Base):
    __tablename__ = "pricing_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("property.id"), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, comment="目标日期")
    conservative_price: Mapped[float] = mapped_column(Float, nullable=False, comment="保守价")
    suggested_price: Mapped[float] = mapped_column(Float, nullable=False, comment="建议价")
    aggressive_price: Mapped[float] = mapped_column(Float, nullable=False, comment="激进价")
    calculation_details: Mapped[dict] = mapped_column(JSON, default=dict, comment="计算依据明细")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
