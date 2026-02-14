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
        """根据历史交易和反馈计算调整系数"""
        transactions = data.get("transactions", [])
        feedbacks = data.get("feedbacks", [])

        # Transaction trend signal: compare recent half vs older half avg price
        tx_signal = 0.0
        if len(transactions) >= 2:
            mid = len(transactions) // 2
            older_avg = sum(t["actual_price"] for t in transactions[:mid]) / mid
            recent_avg = sum(t["actual_price"] for t in transactions[mid:]) / (len(transactions) - mid)
            if older_avg > 0:
                tx_signal = (recent_avg - older_avg) / older_avg
                tx_signal = max(-0.3, min(0.3, tx_signal))

        # Feedback signal
        fb_signal = 0.0
        if feedbacks:
            accepted = sum(1 for f in feedbacks if f["feedback_type"] == "采纳")
            rejected = sum(1 for f in feedbacks if f["feedback_type"] == "拒绝")
            adjusted = [f for f in feedbacks if f["feedback_type"] == "调整"]
            total = len(feedbacks)

            accept_rate = accepted / total
            reject_rate = rejected / total

            # Acceptance → slight upward; rejection → downward
            fb_signal += accept_rate * 0.1
            fb_signal -= reject_rate * 0.15

            # Adjustments: if actual_price > suggested → user wanted higher
            for f in adjusted:
                if f.get("actual_price") and f.get("suggested_price"):
                    if f["actual_price"] > f["suggested_price"]:
                        fb_signal += 0.05 / total
                    else:
                        fb_signal -= 0.05 / total

        signals = []
        if transactions:
            signals.append(tx_signal)
        if feedbacks:
            signals.append(fb_signal)
        return sum(signals) / len(signals) if signals else 0.0

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
        """根据同类房源市场数据计算调整系数"""
        similar_avg = data.get("similar_avg", 0)
        own_avg = data.get("own_avg", 0)

        if similar_avg <= 0 or own_avg <= 0:
            return 0.0

        # Positive deviation means similar properties price higher → we're underpriced
        deviation = (similar_avg - own_avg) / similar_avg
        # Apply 0.5 damping factor
        adjustment = deviation * 0.5
        return max(-0.2, min(0.2, adjustment))

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
        """根据外部事件（节假日邻近、预订紧迫度）计算调整系数"""
        adj = 0.0

        for event in events:
            etype = event.get("type")

            if etype == "holiday":
                # Direct holiday hit
                adj += 0.10
            elif etype == "holiday_adjacent":
                # Spillover effect, decays with distance (1-3 days)
                distance = event.get("distance_days", 3)
                adj += 0.06 * (1.0 - (distance - 1) / 3.0)
            elif etype == "booking_urgency":
                avg_advance = event.get("avg_advance_days", 14)
                days_until = event.get("days_until_target", 30)
                if avg_advance > 0 and days_until < avg_advance * 0.5:
                    # High urgency: target date is much sooner than typical booking lead time
                    adj += 0.05
                elif days_until > avg_advance * 2:
                    # Low urgency: very far out
                    adj -= 0.03

        return max(-0.15, min(0.15, adj))
