def test_property_tool_schema():
    from app.tools.property_tool import property_create_tool, property_query_tool
    assert property_create_tool.name == "property_create"
    assert property_query_tool.name == "property_query"


def test_pricing_tool_schema():
    from app.tools.pricing_tool import pricing_calculate_tool
    assert pricing_calculate_tool.name == "pricing_calculate"


def test_feedback_tool_schema():
    from app.tools.feedback_tool import feedback_record_tool
    assert feedback_record_tool.name == "feedback_record"


def test_excel_tool_schema():
    from app.tools.excel_tool import excel_parse_tool
    assert excel_parse_tool.name == "excel_parse"
