from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.pricing import PricingRecord
from app.models.property import Property
from app.models.transaction import Transaction
from app.models.feedback import Feedback
from app.engine.pricing_engine import PricingEngine


async def calculate_and_save(
    db: AsyncSession,
    property_id: int,
    target_date: date,
    base_price: float | None = None,
) -> PricingRecord | None:
    # Fetch property
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        return None

    # Use min_price as base if not provided
    effective_base = base_price or prop.min_price or 300.0

    # Fetch factor data
    historical_data = await _fetch_historical_data(db, property_id)
    market_data = await _fetch_market_data(db, property_id, prop.room_type, prop.area)
    external_events = await _fetch_external_events(db, property_id, target_date)

    engine = PricingEngine()
    pricing = engine.calculate(
        base_price=effective_base,
        owner_preference={
            "min_price": prop.min_price or 0,
            "max_price": prop.max_price or float("inf"),
            "expected_return_rate": prop.expected_return_rate or 0,
            "vacancy_tolerance": prop.vacancy_tolerance or 0.5,
        },
        property_info={
            "room_type": prop.room_type,
            "area": prop.area,
            "facilities": prop.facilities or {},
        },
        target_date=target_date,
        historical_data=historical_data,
        market_data=market_data,
        external_events=external_events,
    )

    record = PricingRecord(
        property_id=property_id,
        target_date=target_date,
        conservative_price=pricing["conservative_price"],
        suggested_price=pricing["suggested_price"],
        aggressive_price=pricing["aggressive_price"],
        calculation_details=pricing["calculation_details"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_by_property(db: AsyncSession, property_id: int) -> list[PricingRecord]:
    result = await db.execute(
        select(PricingRecord)
        .where(PricingRecord.property_id == property_id)
        .order_by(PricingRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_historical_data(
    db: AsyncSession, property_id: int
) -> dict | None:
    """Fetch 180-day transaction + feedback data for the historical performance factor."""
    cutoff = datetime.utcnow() - timedelta(days=180)

    # Transactions in last 180 days
    tx_result = await db.execute(
        select(Transaction.actual_price, Transaction.check_in_date)
        .where(Transaction.property_id == property_id)
        .where(Transaction.created_at >= cutoff)
        .order_by(Transaction.check_in_date)
    )
    transactions = [
        {"actual_price": row.actual_price, "check_in_date": row.check_in_date}
        for row in tx_result.all()
    ]

    # Feedback in last 180 days, joined with PricingRecord for suggested_price
    fb_result = await db.execute(
        select(
            Feedback.feedback_type,
            Feedback.actual_price,
            PricingRecord.suggested_price,
        )
        .join(PricingRecord, Feedback.pricing_record_id == PricingRecord.id)
        .where(PricingRecord.property_id == property_id)
        .where(Feedback.created_at >= cutoff)
    )
    feedbacks = [
        {
            "feedback_type": row.feedback_type,
            "actual_price": row.actual_price,
            "suggested_price": row.suggested_price,
        }
        for row in fb_result.all()
    ]

    if not transactions and not feedbacks:
        return None

    return {"transactions": transactions, "feedbacks": feedbacks}


async def _fetch_market_data(
    db: AsyncSession, property_id: int, room_type: str, area: float
) -> dict | None:
    """Fetch 90-day comparable property pricing for the market factor."""
    cutoff = datetime.utcnow() - timedelta(days=90)
    area_low = area * 0.7
    area_high = area * 1.3

    # Similar properties: same room_type, area ±30%, exclude self
    similar_stats = await db.execute(
        select(
            func.avg(PricingRecord.suggested_price).label("avg_price"),
            func.min(PricingRecord.suggested_price).label("min_price"),
            func.max(PricingRecord.suggested_price).label("max_price"),
        )
        .join(Property, PricingRecord.property_id == Property.id)
        .where(Property.room_type == room_type)
        .where(Property.area >= area_low)
        .where(Property.area <= area_high)
        .where(Property.id != property_id)
        .where(PricingRecord.created_at >= cutoff)
    )
    sim_row = similar_stats.one()

    # Own average in last 90 days
    own_stats = await db.execute(
        select(func.avg(PricingRecord.suggested_price).label("avg_price"))
        .where(PricingRecord.property_id == property_id)
        .where(PricingRecord.created_at >= cutoff)
    )
    own_avg = own_stats.scalar()

    if sim_row.avg_price is None or own_avg is None:
        return None

    return {
        "similar_avg": float(sim_row.avg_price),
        "similar_min": float(sim_row.min_price),
        "similar_max": float(sim_row.max_price),
        "own_avg": float(own_avg),
    }


async def _fetch_external_events(
    db: AsyncSession, property_id: int, target_date: date
) -> list[dict] | None:
    """Fetch external event signals: holiday proximity + booking urgency."""
    from app.engine.config import HOLIDAYS_2026

    events: list[dict] = []

    # Holiday proximity check (within 3 days of any holiday date)
    all_holiday_dates: list[tuple[str, date]] = []
    for name, dates in HOLIDAYS_2026.items():
        for d in dates:
            all_holiday_dates.append(
                (name, date.fromisoformat(d))
            )

    for name, hdate in all_holiday_dates:
        delta = abs((target_date - hdate).days)
        if delta == 0:
            events.append({"type": "holiday", "name": name, "distance_days": 0})
            break
        elif delta <= 3:
            events.append({"type": "holiday_adjacent", "name": name, "distance_days": delta})

    # Booking urgency: average advance_days for this property vs days until target
    cutoff = datetime.utcnow() - timedelta(days=180)
    adv_result = await db.execute(
        select(func.avg(Transaction.advance_days))
        .where(Transaction.property_id == property_id)
        .where(Transaction.advance_days.is_not(None))
        .where(Transaction.created_at >= cutoff)
    )
    avg_advance = adv_result.scalar()

    if avg_advance is not None:
        days_until = (target_date - date.today()).days
        events.append({
            "type": "booking_urgency",
            "avg_advance_days": float(avg_advance),
            "days_until_target": max(days_until, 0),
        })

    return events if events else None
