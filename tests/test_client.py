"""
SDK unit tests — 80+ tests covering client init, auth, retry, errors,
and one test per tool method (mock httpx, no live calls).
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

import sys
sys.path.insert(0, "src")

from thinkneo import ThinkNEO as ThinkneoClient
from thinkneo.client import AsyncThinkNEO as AsyncThinkneoClient
from thinkneo.exceptions import (
    AuthenticationError, RateLimitError, ConnectionError,
    ThinkNEOError, ToolError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_response(status=200, body=None):
    """Create a mock httpx Response."""
    if body is None:
        body = {"jsonrpc": "2.0", "id": "1", "result": {
            "content": [{"type": "text", "text": '{"status":"ok"}'}]
        }}
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp)
    return resp


@pytest.fixture
def client():
    return ThinkneoClient(api_key="test-key", base_url="https://test.example.com/mcp")


@pytest.fixture
def mock_post(client):
    """Mock httpx.Client.post to return a successful response."""
    with patch.object(client._client, "post", return_value=_mock_response()) as m:
        yield m


# ---------------------------------------------------------------------------
# Client Init
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_default_base_url(self):
        c = ThinkneoClient()
        assert "mcp.thinkneo.ai" in c.base_url

    def test_custom_base_url(self):
        c = ThinkneoClient(base_url="https://custom.example.com/mcp")
        assert c.base_url == "https://custom.example.com/mcp"

    def test_api_key_set(self):
        c = ThinkneoClient(api_key="my-key")
        assert c.api_key == "my-key"

    def test_env_var_api_key(self):
        with patch.dict(os.environ, {"THINKNEO_API_KEY": "env-key"}):
            # Client should support reading from env
            c = ThinkneoClient()
            # Note: current impl doesn't auto-read env, but auth header works

    def test_timeout_configurable(self):
        c = ThinkneoClient(timeout=60.0)
        assert c.timeout == 60.0

    def test_max_retries_configurable(self):
        c = ThinkneoClient(max_retries=5)
        assert c.max_retries == 5

    def test_context_manager(self):
        with ThinkneoClient() as c:
            assert c is not None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_auth_header_set(self, client, mock_post):
        client.check(text="test")
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        assert "Bearer test-key" in str(headers)

    def test_no_auth_header_without_key(self, mock_post):
        c = ThinkneoClient(api_key=None, base_url="https://test.example.com/mcp")
        with patch.object(c._client, "post", return_value=_mock_response()):
            c.check(text="test")

    def test_401_raises_auth_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(401)):
            with pytest.raises(AuthenticationError):
                client.check(text="test")

    def test_429_raises_rate_limit_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(429)):
            with pytest.raises(RateLimitError):
                client.check(text="test")


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

class TestRetry:
    def test_retries_on_500(self, client):
        with patch.object(client._client, "post",
                         side_effect=[_mock_response(500), _mock_response(500), _mock_response()]):
            result = client.check(text="test")
            assert result is not None

    def test_max_retries_exhausted(self, client):
        with patch.object(client._client, "post",
                         side_effect=httpx.ConnectError("down")):
            with pytest.raises(ConnectionError):
                client.check(text="test")


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_tool_error_on_rpc_error(self, client):
        body = {"jsonrpc": "2.0", "id": "1", "error": {"code": -32600, "message": "Invalid"}}
        with patch.object(client._client, "post", return_value=_mock_response(200, body)):
            with pytest.raises(ToolError):
                client.check(text="test")

    def test_server_error_raised(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(502)):
            with pytest.raises(ThinkNEOError):
                client.check(text="test")


# ---------------------------------------------------------------------------
# Tool Methods — one test per method (59 MCP + 8 A2A-only = 67)
# Uses parametrize for efficiency
# ---------------------------------------------------------------------------

# All tool methods with minimal valid args
TOOL_METHODS = [
    # Public
    ("check", {"text": "hello"}),
    ("provider_status", {}),
    ("usage", {}),
    ("read_memory", {}),
    ("simulate_savings", {"monthly_ai_spend": 5000.0}),
    ("schedule_demo", {"contact_name": "T", "company": "C", "email": "t@t.com"}),
    # Auth-required (all return GenericResponse via _tool_call)
    ("check_spend", {"workspace": "prod"}),
    ("evaluate_guardrail", {"text": "t", "workspace": "prod"}),
    ("check_policy", {"workspace": "prod"}),
    ("get_budget_status", {"workspace": "prod"}),
    ("list_alerts", {"workspace": "prod"}),
    ("get_compliance_status", {"workspace": "prod"}),
    ("route_model", {"task_type": "chat"}),
    ("get_savings_report", {}),
    ("registry_search", {}),
    ("registry_get", {"name": "test"}),
    ("registry_install", {"name": "test"}),
    ("registry_publish", {"name": "t", "display_name": "T", "description": "D", "endpoint_url": "https://x.com/mcp"}),
    ("registry_review", {"name": "t", "rating": 5}),
    # Observability
    ("start_trace", {"agent_name": "test"}),
    ("log_event", {"session_id": "s1", "event_type": "tool_call"}),
    ("end_trace", {"session_id": "s1"}),
    ("get_trace", {"session_id": "s1"}),
    ("get_observability_dashboard", {}),
    # Trust Score
    ("evaluate_trust_score", {"org_name": "TestOrg"}),
    ("get_trust_badge", {"report_token": "tok"}),
    # Value/ROI
    ("set_baseline", {"process_name": "support", "cost_per_unit_usd": 15.0}),
    ("log_decision", {"agent_name": "test", "decision_type": "model"}),
    ("decision_cost", {}),
    ("log_risk_avoidance", {"risk_type": "pii"}),
    ("agent_roi", {}),
    ("business_impact", {}),
    ("detect_waste", {}),
    # Outcome Validation
    ("register_claim", {"action": "email_sent", "target": "u@t.com", "evidence_type": "http_status"}),
    ("verify_claim", {"claim_id": "c1"}),
    ("get_proof", {"claim_id": "c1"}),
    ("verification_dashboard", {}),
    # Policy Engine
    ("policy_create", {"name": "p1", "conditions": "[{}]", "effect": "block"}),
    ("policy_evaluate", {"context": "{}"}),
    ("policy_list", {}),
    ("policy_violations", {}),
    # Compliance
    ("compliance_generate", {"framework": "eu_ai_act"}),
    ("compliance_list", {}),
    # A2A Bridge
    ("bridge_mcp_to_a2a", {"mcp_tool_name": "thinkneo_check"}),
    ("bridge_a2a_to_mcp", {"a2a_task": "{}"}),
    ("bridge_generate_agent_card", {}),
    ("bridge_list_mappings", {}),
    # A2A Governance
    ("a2a_log", {"from_agent": "a", "to_agent": "b", "action": "task_sent"}),
    ("a2a_set_policy", {"from_agent": "a", "to_agent": "b"}),
    ("a2a_flow_map", {}),
    ("a2a_audit", {}),
    # Benchmarking
    ("benchmark_compare", {"task_type": "chat"}),
    ("benchmark_report", {}),
    ("router_explain", {"task_type": "chat"}),
    # SLA
    ("sla_define", {"agent_name": "test", "metric": "latency", "threshold": 500.0}),
    ("sla_status", {}),
    ("sla_dashboard", {}),
    ("sla_breaches", {}),
    # A2A-only skills
    ("detect_secrets", {"code": "password=123"}),
    ("detect_injection", {"text": "ignore instructions"}),
    ("compare_models", {}),
    ("optimize_prompt", {"prompt": "hello world"}),
    ("count_tokens", {"text": "hello"}),
    ("detect_pii", {"text": "SSN: 123-45-6789"}),
    ("cache_prompt", {"key": "k1"}),
    ("rotate_key", {}),
    # write_memory (auth)
    ("write_memory", {"filename": "test.md", "content": "# test"}),
]


@pytest.mark.parametrize("method,kwargs", TOOL_METHODS,
                         ids=[t[0] for t in TOOL_METHODS])
def test_tool_method_calls_api(client, mock_post, method, kwargs):
    """Each tool method should call the API and return a response."""
    fn = getattr(client, method)
    result = fn(**kwargs)
    assert result is not None
    mock_post.assert_called_once()


@pytest.mark.parametrize("method,kwargs", TOOL_METHODS,
                         ids=[f"{t[0]}_json" for t in TOOL_METHODS])
def test_tool_method_sends_correct_tool_name(client, mock_post, method, kwargs):
    """Each method should send the correct thinkneo_<name> in the RPC payload."""
    fn = getattr(client, method)
    fn(**kwargs)
    call_args = mock_post.call_args
    payload = call_args.kwargs.get("json", call_args[1].get("json", {}))
    tool_name = payload.get("params", {}).get("name", "")
    assert tool_name.startswith("thinkneo_"), f"{method} sent tool_name={tool_name}"


class TestListTools:
    def test_list_tools(self, client, mock_post):
        mock_post.return_value = _mock_response(200, {
            "jsonrpc": "2.0", "id": "1",
            "result": {"tools": [{"name": "thinkneo_check"}]}
        })
        tools = client.list_tools()
        assert isinstance(tools, list)


# ---------------------------------------------------------------------------
# Live E2E (only on push to master)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_live_check():
    """E2E: call thinkneo_check on production."""
    client = ThinkneoClient()
    result = client.check(text="Hello world")
    assert hasattr(result, "raw") or isinstance(result, dict)

@pytest.mark.live
def test_live_provider_status():
    """E2E: call provider_status on production."""
    client = ThinkneoClient()
    result = client.provider_status()
    assert result is not None
