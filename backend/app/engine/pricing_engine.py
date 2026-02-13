from datetime import date
from app.engine.config import WEIGHTS, TIME_FACTORS, PRICE_TIERS, HOLIDAYS_2026


class PricingEngine:
    """定价规则引擎 - MVP简化版，支持房东偏好+时间因素+基础属性"""

    def __init__(self):
        self.weights = WEIGHTS.copy()
        self._holiday_dates: set[str] = set()
        for dates in HOLIDAYS_2026.values():
            self._holiday_dates.update(dates)

    def calculate(
        self,
        base_price: float,
        owner_preference: dict,
        property_info: dict,
        target_date: date,
        historical_data: dict | None = None,
        market_data: dict | None = None,
        external_events: list[dict] | None = None,
    ) -> dict:
        min_price = owner_preference.get("min_price", 0)
        max_price = owner_preference.get("max_price", float("inf"))

        details = {}

        # 1. 房东偏好调整
        pref_adj = self._calc_owner_preference(base_price, owner_preference)
        details["owner_preference"] = {"adjustment": pref_adj, "weight": self.weights["owner_preference"]}

        # 2. 历史表现调整（MVP阶段：无历史数据则为0）
        hist_adj = self._calc_historical(historical_data) if historical_data else 0.0
        details["historical_performance"] = {"adjustment": hist_adj, "weight": self.weights["historical_performance"]}

        # 3. 时间因素调整
        time_adj = self._calc_time_factor(target_date)
        details["time_factor"] = {"adjustment": time_adj, "weight": self.weights["time_factor"]}

        # 4. 市场因素调整（MVP阶段：预留接口，默认0）
        market_adj = self._calc_market(market_data) if market_data else 0.0
        details["market_factor"] = {"adjustment": market_adj, "weight": self.weights["market_factor"]}

        # 5. 基础属性调整
        base_adj = self._calc_property_base(property_info)
        details["property_base"] = {"adjustment": base_adj, "weight": self.weights["property_base"]}

        # 6. 外部事件调整（MVP阶段：预留接口，默认0）
        ext_adj = self._calc_external(external_events) if external_events else 0.0
        details["external_event"] = {"adjustment": ext_adj, "weight": self.weights["external_event"]}

        # 综合调整系数
        composite = (
            pref_adj * self.weights["owner_preference"]
            + hist_adj * self.weights["historical_performance"]
            + time_adj * self.weights["time_factor"]
            + market_adj * self.weights["market_factor"]
            + base_adj * self.weights["property_base"]
            + ext_adj * self.weights["external_event"]
        )

        suggested = base_price * (1 + composite)
        conservative = suggested * (1 + PRICE_TIERS["conservative_offset"])
        aggressive = suggested * (1 + PRICE_TIERS["aggressive_offset"])

        # 边界约束
        conservative = max(min_price, min(max_price, conservative))
        suggested = max(min_price, min(max_price, suggested))
        aggressive = max(min_price, min(max_price, aggressive))

        # 保持三档排序
        conservative = min(conservative, suggested)
        aggressive = max(aggressive, suggested)

        return {
            "conservative_price": round(conservative, 2),
            "suggested_price": round(suggested, 2),
            "aggressive_price": round(aggressive, 2),
            "base_price": base_price,
            "composite_adjustment": round(composite, 4),
            "calculation_details": details,
        }

    def _calc_owner_preference(self, base_price: float, pref: dict) -> float:
        """根据房东偏好计算调整系数"""
        adj = 0.0
        expected_rate = pref.get("expected_return_rate", 0)
        if expected_rate > 0:
            adj += expected_rate * 0.5  # 期望收益率部分转化为价格上浮

        vacancy_tol = pref.get("vacancy_tolerance", 0.5)
        # 空置容忍度低 → 价格趋向保守（下调）
        # 空置容忍度高 → 价格可以激进（上调）
        adj += (vacancy_tol - 0.5) * 0.2

        return adj

    def _calc_historical(self, data: dict) -> float:
        """根据历史表现计算调整系数（MVP预留）"""
        return 0.0

    def _calc_time_factor(self, target_date: date) -> float:
        """根据日期计算时间因素调整系数"""
        date_str = target_date.isoformat()

        # 节假日
        if date_str in self._holiday_dates:
            return TIME_FACTORS["holiday_multiplier"] - 1.0

        # 周末 (5=Saturday, 6=Sunday)
        if target_date.weekday() >= 5:
            return TIME_FACTORS["weekend_multiplier"] - 1.0

        # 工作日
        return TIME_FACTORS["weekday_multiplier"] - 1.0

    def _calc_market(self, data: dict) -> float:
        """市场因素调整（MVP预留）"""
        return 0.0

    def _calc_property_base(self, info: dict) -> float:
        """根据房源基础属性计算调整系数"""
        adj = 0.0
        # 整套 vs 单间
        if info.get("room_type") == "整套":
            adj += 0.05
        # 面积因素
        area = info.get("area", 50)
        if area > 100:
            adj += 0.03
        elif area < 30:
            adj -= 0.03
        return adj

    def _calc_external(self, events: list[dict]) -> float:
        """外部事件调整（MVP预留）"""
        return 0.0
