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


# --------------- Historical factor tests ---------------

class TestCalcHistorical:
    def _engine(self):
        from app.engine.pricing_engine import PricingEngine
        return PricingEngine()

    def test_empty_data(self):
        engine = self._engine()
        assert engine._calc_historical({"transactions": [], "feedbacks": []}) == 0.0

    def test_transactions_only_upward_trend(self):
        engine = self._engine()
        # Older half avg=100, recent half avg=120 → trend = +0.2
        data = {
            "transactions": [
                {"actual_price": 100, "check_in_date": date(2026, 1, 1)},
                {"actual_price": 100, "check_in_date": date(2026, 1, 15)},
                {"actual_price": 120, "check_in_date": date(2026, 2, 1)},
                {"actual_price": 120, "check_in_date": date(2026, 2, 15)},
            ],
            "feedbacks": [],
        }
        result = engine._calc_historical(data)
        assert result > 0  # upward trend
        assert result == pytest.approx(0.2, abs=0.01)  # (0.2 + 0) / 1 signal only tx

    def test_feedbacks_only_all_accepted(self):
        engine = self._engine()
        data = {
            "transactions": [],
            "feedbacks": [
                {"feedback_type": "采纳", "actual_price": 500, "suggested_price": 500},
                {"feedback_type": "采纳", "actual_price": 500, "suggested_price": 500},
            ],
        }
        result = engine._calc_historical(data)
        assert result > 0  # acceptance → upward

    def test_feedbacks_only_all_rejected(self):
        engine = self._engine()
        data = {
            "transactions": [],
            "feedbacks": [
                {"feedback_type": "拒绝", "actual_price": None, "suggested_price": 500},
                {"feedback_type": "拒绝", "actual_price": None, "suggested_price": 500},
            ],
        }
        result = engine._calc_historical(data)
        assert result < 0  # rejection → downward

    def test_both_sources_averaged(self):
        engine = self._engine()
        data = {
            "transactions": [
                {"actual_price": 100, "check_in_date": date(2026, 1, 1)},
                {"actual_price": 120, "check_in_date": date(2026, 2, 1)},
            ],
            "feedbacks": [
                {"feedback_type": "采纳", "actual_price": 500, "suggested_price": 500},
            ],
        }
        result = engine._calc_historical(data)
        # Both signals present → averaged
        assert result > 0

    def test_transaction_trend_clamped(self):
        engine = self._engine()
        # Extreme trend: older=100, recent=200 → raw trend=1.0, clamped to 0.3
        data = {
            "transactions": [
                {"actual_price": 100, "check_in_date": date(2026, 1, 1)},
                {"actual_price": 200, "check_in_date": date(2026, 2, 1)},
            ],
            "feedbacks": [],
        }
        result = engine._calc_historical(data)
        assert result <= 0.3


# --------------- Market factor tests ---------------

class TestCalcMarket:
    def _engine(self):
        from app.engine.pricing_engine import PricingEngine
        return PricingEngine()

    def test_no_data(self):
        engine = self._engine()
        assert engine._calc_market({"similar_avg": 0, "own_avg": 0}) == 0.0

    def test_underpriced(self):
        engine = self._engine()
        # similar_avg=500, own_avg=400 → deviation=0.2, adj=0.1
        result = engine._calc_market({
            "similar_avg": 500, "similar_min": 300, "similar_max": 700, "own_avg": 400,
        })
        assert result == pytest.approx(0.1, abs=0.01)

    def test_overpriced(self):
        engine = self._engine()
        # similar_avg=400, own_avg=500 → deviation=-0.25, adj=-0.125
        result = engine._calc_market({
            "similar_avg": 400, "similar_min": 300, "similar_max": 500, "own_avg": 500,
        })
        assert result < 0

    def test_clamped_high(self):
        engine = self._engine()
        # Extreme: similar_avg=1000, own_avg=100 → deviation=0.9, adj=0.45 → clamped 0.2
        result = engine._calc_market({
            "similar_avg": 1000, "similar_min": 800, "similar_max": 1200, "own_avg": 100,
        })
        assert result == pytest.approx(0.2, abs=0.001)

    def test_clamped_low(self):
        engine = self._engine()
        # Extreme: similar_avg=100, own_avg=1000 → deviation=-9.0, adj=-4.5 → clamped -0.2
        result = engine._calc_market({
            "similar_avg": 100, "similar_min": 80, "similar_max": 120, "own_avg": 1000,
        })
        assert result == pytest.approx(-0.2, abs=0.001)

    def test_equal_prices(self):
        engine = self._engine()
        result = engine._calc_market({
            "similar_avg": 500, "similar_min": 400, "similar_max": 600, "own_avg": 500,
        })
        assert result == pytest.approx(0.0, abs=0.001)


# --------------- External event factor tests ---------------

class TestCalcExternal:
    def _engine(self):
        from app.engine.pricing_engine import PricingEngine
        return PricingEngine()

    def test_empty_events(self):
        engine = self._engine()
        assert engine._calc_external([]) == 0.0

    def test_holiday_direct(self):
        engine = self._engine()
        result = engine._calc_external([
            {"type": "holiday", "name": "春节", "distance_days": 0},
        ])
        assert result == pytest.approx(0.10, abs=0.001)

    def test_holiday_adjacent_day1(self):
        engine = self._engine()
        result = engine._calc_external([
            {"type": "holiday_adjacent", "name": "春节", "distance_days": 1},
        ])
        assert result == pytest.approx(0.06, abs=0.001)

    def test_holiday_adjacent_day3(self):
        engine = self._engine()
        result = engine._calc_external([
            {"type": "holiday_adjacent", "name": "春节", "distance_days": 3},
        ])
        assert result == pytest.approx(0.02, abs=0.001)

    def test_high_urgency(self):
        engine = self._engine()
        # avg_advance=30, days_until=10 → 10 < 30*0.5=15 → +0.05
        result = engine._calc_external([
            {"type": "booking_urgency", "avg_advance_days": 30, "days_until_target": 10},
        ])
        assert result == pytest.approx(0.05, abs=0.001)

    def test_low_urgency(self):
        engine = self._engine()
        # avg_advance=14, days_until=60 → 60 > 14*2=28 → -0.03
        result = engine._calc_external([
            {"type": "booking_urgency", "avg_advance_days": 14, "days_until_target": 60},
        ])
        assert result == pytest.approx(-0.03, abs=0.001)

    def test_combined_clamped(self):
        engine = self._engine()
        # holiday(+0.10) + high urgency(+0.05) = 0.15 → at clamp boundary
        result = engine._calc_external([
            {"type": "holiday", "name": "国庆", "distance_days": 0},
            {"type": "booking_urgency", "avg_advance_days": 30, "days_until_target": 5},
        ])
        assert result == pytest.approx(0.15, abs=0.001)
