import pytest
from datetime import date


def test_basic_pricing():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    result = engine.calculate(
        base_price=500.0,
        owner_preference={
            "min_price": 300.0,
            "max_price": 800.0,
            "expected_return_rate": 0.15,
            "vacancy_tolerance": 0.2,
        },
        property_info={
            "room_type": "整套",
            "area": 80.0,
            "facilities": {"wifi": True, "ac": True},
        },
        target_date=date(2026, 5, 1),
    )
    assert "conservative_price" in result
    assert "suggested_price" in result
    assert "aggressive_price" in result
    assert "calculation_details" in result
    assert result["conservative_price"] <= result["suggested_price"] <= result["aggressive_price"]
    assert result["conservative_price"] >= 300.0  # 不低于最低价
    assert result["aggressive_price"] <= 800.0  # 不高于最高价


def test_weekend_adjustment():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    # 2026-05-09 是周六（非节假日）
    weekend_result = engine.calculate(
        base_price=500.0,
        owner_preference={"min_price": 200.0, "max_price": 1000.0},
        property_info={"room_type": "整套", "area": 80.0},
        target_date=date(2026, 5, 9),
    )
    # 2026-05-11 是周一（非节假日）
    weekday_result = engine.calculate(
        base_price=500.0,
        owner_preference={"min_price": 200.0, "max_price": 1000.0},
        property_info={"room_type": "整套", "area": 80.0},
        target_date=date(2026, 5, 11),
    )
    assert weekend_result["suggested_price"] > weekday_result["suggested_price"]


def test_price_boundary_enforcement():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    result = engine.calculate(
        base_price=100.0,
        owner_preference={"min_price": 300.0, "max_price": 400.0},
        property_info={"room_type": "单间", "area": 20.0},
        target_date=date(2026, 5, 1),
    )
    # 即使基准价很低，也不低于最低价
    assert result["conservative_price"] >= 300.0
    assert result["aggressive_price"] <= 400.0
