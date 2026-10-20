from orchestrator.agents import all_agents
from orchestrator.a2a.server import (
    AGENT_ALIASES,
    available_agent_ids,
    build_agent_card,
    create_app,
)


def test_a2a_gateway_registers_core_product_gtm_and_mentor_agents():
    ids = set(available_agent_ids())
    assert {"product", "architect", "coder", "security_auditor", "mentor", "gtm"} <= ids
    assert len(ids) == len(AGENT_ALIASES)


def test_a2a_card_exposes_registered_agents_as_skills():
    card = build_agent_card()
    skill_ids = {skill.id for skill in card.skills}
    assert "product" in skill_ids
    assert "mentor" in skill_ids
    assert "gtm" not in skill_ids  # Alias of business_strategy, not a duplicate skill.
    assert "business_strategy" in skill_ids
    assert any(
        interface.protocol_binding == "JSONRPC"
        and interface.protocol_version == "1.0"
        for interface in card.supported_interfaces
    )


def test_a2a_server_defaults_to_loopback_and_registers_card_route():
    app = create_app(host="127.0.0.1", port=8090)
    paths = {route.path for route in app.routes}
    assert "/.well-known/agent-card.json" in paths
    assert "/a2a/jsonrpc" in paths


def test_a2a_gateway_refuses_remote_bind_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("ASCM_A2A_ALLOW_REMOTE", raising=False)
    try:
        create_app(host="0.0.0.0", port=8090)
    except ValueError as exc:
        assert "loopback" in str(exc)
    else:
        raise AssertionError("Remote binding should require explicit opt-in")



def test_every_advertised_specialist_resolves_to_an_implemented_agent():
    # The founder mentor lives outside all_agents.py; every other target must
    # resolve to a real class or compatibility alias in the central agent module.
    for agent_id, class_name in AGENT_ALIASES.items():
        if agent_id == "mentor":
            assert class_name == "ASCMProactiveMentor"
        else:
            assert getattr(all_agents, class_name, None) is not None, (
                f"A2A advertises {agent_id!r} but {class_name!r} is not implemented"
            )


def test_a2a_roster_includes_the_implemented_specialists_without_placeholder_ids():
    ids = set(available_agent_ids())
    assert {
        "discovery", "product", "design", "architect", "planner", "database",
        "coder", "security_auditor", "business_strategy", "gtm", "revenue_roi",
        "architecture_review", "code_review", "mentor",
    } <= ids
    assert not ({"checker", "compliance", "qa", "sre", "apm", "oncall", "sales",
                 "marketing", "advertising", "seo"} & ids)
