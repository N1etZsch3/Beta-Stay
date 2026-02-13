def test_agent_creation():
    from app.agent.betastay_agent import create_betastay_agent
    agent = create_betastay_agent()
    assert agent is not None


def test_agent_has_tools():
    from app.agent.betastay_agent import create_betastay_agent
    agent = create_betastay_agent()
    # create_react_agent returns a CompiledGraph, verify it can be invoked
    assert hasattr(agent, "invoke")
