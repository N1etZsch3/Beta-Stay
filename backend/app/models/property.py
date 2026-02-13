from sqlalchemy import String, Float, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class Property(Base):
    __tablename__ = "property"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="房源名称")
    address: Mapped[str] = mapped_column(String(500), nullable=False, comment="地址")
    room_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="房型")
    area: Mapped[float] = mapped_column(Float, nullable=False, comment="面积(平方米)")
    facilities: Mapped[dict] = mapped_column(JSON, default=dict, comment="设施配置")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="房源描述")

    # 房东偏好
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最低可接受价")
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最高价格")
    expected_return_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="期望收益率")
    vacancy_tolerance: Mapped[float | None] = mapped_column(Float, nullable=True, comment="空置容忍度(0-1)")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
