from app.models.conversation import Conversation, Message
from app.models.feedback import Feedback
from app.models.pricing import PricingRecord
from app.models.property import Property


def test_property_model_fields():
    p = Property(
        name="测试民宿",
        address="杭州市西湖区",
        room_type="整套",
        area=80.0,
        facilities={"wifi": True, "ac": True},
        min_price=200.0,
        max_price=800.0,
    )
    assert p.name == "测试民宿"
    assert p.facilities["wifi"] is True
    assert p.min_price == 200.0


def test_pricing_record_model_fields():
    from datetime import date

    pr = PricingRecord(
        property_id=1,
        target_date=date(2026, 5, 1),
        conservative_price=300.0,
        suggested_price=400.0,
        aggressive_price=500.0,
        calculation_details={"weight_owner_pref": 0.35},
    )
    assert pr.suggested_price == 400.0
    assert pr.calculation_details["weight_owner_pref"] == 0.35


def test_feedback_model_fields():
    f = Feedback(
        pricing_record_id=1,
        feedback_type="adopted",
        actual_price=380.0,
        note="价格合理",
    )
    assert f.feedback_type == "adopted"


def test_conversation_and_message_fields():
    c = Conversation(title="定价咨询")
    assert c.title == "定价咨询"

    m = Message(
        conversation_id="test-uuid-placeholder",
        role="user",
        content="帮我看看明天的建议价",
    )
    assert m.role == "user"
