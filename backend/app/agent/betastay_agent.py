from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi
from app.core.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.property_tool import property_create_tool, property_query_tool, show_property_form_tool
from app.tools.pricing_tool import pricing_calculate_tool
from app.tools.feedback_tool import feedback_record_tool
from app.tools.excel_tool import excel_parse_tool


def get_tools():
    return [
        property_create_tool,
        property_query_tool,
        show_property_form_tool,
        pricing_calculate_tool,
        feedback_record_tool,
        excel_parse_tool,
    ]


def create_betastay_agent(checkpointer=None):
    """创建BetaStay Agent实例"""
    model = ChatTongyi(
        model=settings.DASHSCOPE_MODEL,
        streaming=True,
        model_kwargs={"enable_thinking": True, "incremental_output": True},
        api_key=settings.DASHSCOPE_API_KEY,
    )

    agent = create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent
