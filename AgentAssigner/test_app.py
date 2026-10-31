import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

import models
from agent import DebugAgent, GeminiAgent
from app import create_app
from logs import fetch_logs, parse_log_payload
from models import AcceptRequest


# Builds a fake Claude reply containing a tool_use analysis with the given confidence.
def tool_response(confidence: float):
    block = SimpleNamespace(
        type="tool_use",
        name="submit_analysis",
        input={
            "root_cause": {
                "summary": "DB connection pool exhausted",
                "explanation": "Timeouts began right after the deploy lowered pool size.",
                "confidence": confidence,
            },
            "evidence": ["ERROR timeout acquiring connection"],
            "remediation": [
                {"action": "Raise pool size to 50", "type": "corrective"},
                {"action": "Add pool saturation alert", "type": "preventive"},
            ],
            "stakeholder_summary": "Checkout slowness traced to a DB pool limit.",
            "kb_article_title": "Handling DB pool exhaustion",
        },
    )
    return SimpleNamespace(content=[block])


class FakeClient:
    # Stores the canned response or error and exposes a fake `messages.create` that records its calls.
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response, self._error = response, error
        self.messages = SimpleNamespace(create=self._create)

    # Fake Anthropic call: records the arguments, then raises the error or returns the canned response.
    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


# Creates a test client for an app that uses the Claude agent with the fake Anthropic client.
def make_client(fake):
    return TestClient(create_app(DebugAgent(client=fake, model="test-model")))


PAYLOAD = {"bug_id": "BUG-1", "description": "Checkout API timing out", "service": "checkout"}


# Autouse fixture: points reports/data to a temp folder and clears external settings so tests are isolated.
@pytest.fixture(autouse=True)
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(models.settings, "reports_dir", str(tmp_path / "reports"))
    monkeypatch.setattr(models.settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(models.settings, "log_api_url", "")
    monkeypatch.setattr(models.settings, "log_file_path", "")
    monkeypatch.setattr(models.settings, "service_api_key", "")
    monkeypatch.setattr(models.settings, "callback_url", "")
    monkeypatch.setattr(models.settings, "callback_api_key", "")
    monkeypatch.setattr(models.settings, "central_url", "")
    monkeypatch.setattr("agent.GEMINI_RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(models.settings, "gemini_fallback_models", [])


# Accepting a bug with high confidence ends in SUCCESS and produces a report.
def test_accept_then_success_and_report():
    fake = FakeClient(tool_response(0.9))
    with make_client(fake) as c:
        r = c.post("/api/investigations", json=PAYLOAD)
        assert r.status_code == 202 and r.json()["status"] == "QUEUED"

        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "SUCCESS" and s["success"] is True
        assert s["root_cause"] == "DB connection pool exhausted"

        report = c.get("/api/investigations/BUG-1/report")
        assert "Probable Root Cause" in report.text and "Raise pool size" in report.text
        assert fake.calls[-1]["model"] == "test-model"
        assert fake.calls[-1]["tool_choice"]["name"] == "submit_analysis"


# Low-confidence analysis ends in NEEDS_REVIEW, not success.
def test_low_confidence_needs_review():
    with make_client(FakeClient(tool_response(0.2))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "NEEDS_REVIEW" and s["success"] is False


# An LLM error marks the investigation FAILED and records the error in details and report.
def test_llm_failure_reports_failed():
    with make_client(FakeClient(error=RuntimeError("boom"))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "FAILED" and s["success"] is False
        assert "boom" in c.get("/api/investigations/BUG-1/details").json()["error"]
        assert "Error" in c.get("/api/investigations/BUG-1/report").text


# Unknown bug IDs return 404 and an empty bug ID is rejected with 422.
def test_unknown_bug_and_validation():
    with make_client(FakeClient(tool_response(0.9))) as c:
        assert c.get("/api/investigations/NOPE").status_code == 404
        assert c.post("/api/investigations", json={"bug_id": "", "description": "x"}).status_code == 422


# A missing Anthropic API key makes the investigation FAILED instead of crashing.
def test_missing_api_key_fails_gracefully(monkeypatch):
    monkeypatch.setattr(models.settings, "anthropic_api_key", "")
    with TestClient(create_app(DebugAgent())) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "FAILED"


GEMINI_JSON = (
    '{"root_cause": {"summary": "DB pool exhausted", "explanation": "Pool shrank after deploy", '
    '"confidence": 0.85}, "evidence": ["timeout acquiring connection"], '
    '"remediation": [{"action": "Raise pool size", "type": "corrective"}], '
    '"stakeholder_summary": "Checkout slow due to DB pool", "kb_article_title": "DB pool"}'
)


# Creates a test client for an app that uses the Gemini agent over a mocked HTTP transport.
def gemini_client(handler):
    return make_gemini(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


# Builds a test client around a GeminiAgent that uses the given HTTP client.
def make_gemini(http):
    return TestClient(create_app(GeminiAgent(http_client=http, model="gemini-test")))


# Gemini replies wrapped in ```json fences are parsed, and the API key and model URL are sent correctly.
def test_gemini_success_with_fenced_json(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    seen = {}

    def handler(request: httpx.Request):
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["url"] = str(request.url)
        text = "```json\n" + GEMINI_JSON + "\n```"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    with gemini_client(handler) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "SUCCESS" and s["root_cause"] == "DB pool exhausted"
    assert seen["key"] == "test-key" and "gemini-test:generateContent" in seen["url"]


# A Gemini 429 gives a rate-limit error, and a missing Gemini key gives a clear configuration error.
def test_gemini_rate_limit_and_missing_key(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    with gemini_client(lambda r: httpx.Response(429, json={})) as c:
        c.post("/api/investigations", json=PAYLOAD)
        d = c.get("/api/investigations/BUG-1/details").json()
        assert d["status"] == "FAILED" and "rate limit" in d["error"]

    monkeypatch.setattr(models.settings, "gemini_api_key", "")
    with gemini_client(lambda r: httpx.Response(200, json={})) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert "GEMINI_API_KEY" in c.get("/api/investigations/BUG-1/details").json()["error"]


# Non-JSON output from Gemini makes the investigation FAILED.
def test_gemini_garbage_output_fails(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    with gemini_client(lambda r: httpx.Response(200, json=body)) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert c.get("/api/investigations/BUG-1").json()["status"] == "FAILED"


# Transient 503 errors from Gemini are retried until the request succeeds.
def test_gemini_retries_transient_overload(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    attempts = {"json": 0}

    def handler(request: httpx.Request):
        if json.loads(request.content)["generationConfig"].get("responseMimeType"):
            attempts["json"] += 1
            if attempts["json"] < 3:
                return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": GEMINI_JSON}]}}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "a prompt"}]}}]})

    with gemini_client(handler) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert c.get("/api/investigations/BUG-1").json()["status"] == "SUCCESS"
    assert attempts["json"] == 3


# When the primary Gemini model stays overloaded, a fallback model answers and is recorded.
def test_gemini_falls_back_to_another_model_when_overloaded(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(models.settings, "gemini_fallback_models", ["backup-model"])

    def handler(request: httpx.Request):
        if "gemini-test:" in str(request.url):
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        text = GEMINI_JSON if json.loads(request.content)["generationConfig"].get("responseMimeType") else "a prompt"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    with gemini_client(handler) as c:
        c.post("/api/investigations", json=PAYLOAD)
        d = c.get("/api/investigations/BUG-1/details").json()
    assert d["status"] == "SUCCESS" and d["model"] == "backup-model"
    assert d["analysis"]["model_used"] == "backup-model"
    assert any("fallback model backup-model" in e["event"] for e in d["audit"])


# parse_log_payload handles JSON lists, wrapped lists, unknown objects and plain text.
def test_parse_log_payload_formats():
    assert parse_log_payload('["a", "b"]') == ["a", "b"]
    assert parse_log_payload('{"logs": [{"level": "ERROR", "message": "db down"}]}') == ["ERROR db down"]
    assert parse_log_payload('{"data": [{"foo": 1}]}') == ['{"foo": 1}']
    assert parse_log_payload("line1\n\nline2\n") == ["line1", "line2"]


# Helper that runs an async coroutine to completion from a sync test.
def run(coro):
    return asyncio.run(coro)


# Logs are fetched from the log REST API, with {service} and {bug_id} filled into the URL.
def test_fetch_logs_from_rest_api(monkeypatch):
    monkeypatch.setattr(models.settings, "log_api_url", "http://logs.test/logs?service={service}&id={bug_id}")
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=["ERROR pool exhausted"])

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = run(fetch_logs(AcceptRequest(**PAYLOAD), http))
    assert res.lines == ["ERROR pool exhausted"] and "log API" in res.source
    assert seen["url"] == "http://logs.test/logs?service=checkout&id=BUG-1"


# When the log API fails, logs come from the local file, filtered to the service.
def test_fetch_logs_falls_back_to_file(monkeypatch, tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("INFO checkout ok\nERROR checkout pool exhausted\nINFO billing ok\n")
    monkeypatch.setattr(models.settings, "log_api_url", "http://logs.test/logs")
    monkeypatch.setattr(models.settings, "log_file_path", str(log_file))
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    res = run(fetch_logs(AcceptRequest(**PAYLOAD), http))
    assert res.lines == ["INFO checkout ok", "ERROR checkout pool exhausted"]  # filtered to the service
    assert "log file" in res.source and any("log API unavailable" in n for n in res.notes)


# With no log source configured, no lines are returned and a note explains why.
def test_fetch_logs_nothing_configured():
    res = run(fetch_logs(AcceptRequest(**PAYLOAD)))
    assert res.lines == [] and res.source == "none" and res.notes


# The recommended prompt and collected logs are sent to the AI and shown in the report.
def test_prompt_and_logs_reach_the_ai_and_report(monkeypatch, tmp_path):
    log_file = tmp_path / "svc.log"
    log_file.write_text("ERROR checkout timeout acquiring DB connection\n")
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(models.settings, "log_file_path", str(log_file))
    prompts = []

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        prompts.append(body["contents"][0]["parts"][0]["text"])
        if body["generationConfig"].get("responseMimeType") == "application/json":
            text = GEMINI_JSON
        else:
            text = "Look for connection pool errors right after the deploy."
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    with gemini_client(handler) as c:
        c.post("/api/investigations", json=PAYLOAD)
        d = c.get("/api/investigations/BUG-1/details").json()
        assert d["status"] == "SUCCESS"
        assert d["investigation_prompt"] == "Look for connection pool errors right after the deploy."
        assert d["log_line_count"] == 1 and "log file" in d["log_source"]
        report = c.get("/api/investigations/BUG-1/report").text
        assert "Investigation Prompt" in report and "connection pool errors" in report
    analysis_prompt = prompts[-1]
    assert "timeout acquiring DB connection" in analysis_prompt
    assert "Look for connection pool errors" in analysis_prompt


# /ready reports whether the central service is reachable, without becoming unready when it is down.
def test_ready_reports_central_connectivity(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "k")
    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")

    async def up(http=None):
        return True, "GET http://central.test:8080/api/incidents -> HTTP 200"

    async def down(http=None):
        return False, "GET http://central.test:8080/api/incidents failed: ConnectError"

    with make_client(FakeClient(tool_response(0.9))) as c:
        monkeypatch.setattr("app.ping_central", up)
        checks = c.get("/ready").json()["checks"]
        assert checks["central_reachable"] is True and "HTTP 200" in checks["central_detail"]
        monkeypatch.setattr("app.ping_central", down)
        r = c.get("/ready")
        assert r.status_code == 200 and r.json()["checks"]["central_reachable"] is False


# If recommending a prompt fails, the default prompt is used and the investigation still succeeds.
def test_prompt_recommendation_failure_uses_default(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")

    def handler(request: httpx.Request):
        if json.loads(request.content)["generationConfig"].get("responseMimeType"):
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": GEMINI_JSON}]}}]})
        return httpx.Response(500, text="boom")

    with gemini_client(handler) as c:
        c.post("/api/investigations", json=PAYLOAD)
        d = c.get("/api/investigations/BUG-1/details").json()
        assert d["status"] == "SUCCESS" and "Checkout API timing out" in d["investigation_prompt"]
        assert any("using default prompt" in e["event"] for e in d["audit"])


# With SERVICE_API_KEY set, the API requires X-API-Key while /health stays open.
def test_api_key_protects_api_but_not_health(monkeypatch):
    monkeypatch.setattr(models.settings, "service_api_key", "s3cret")
    with make_client(FakeClient(tool_response(0.9))) as c:
        assert c.get("/health").status_code == 200
        assert c.post("/api/investigations", json=PAYLOAD).status_code == 401
        assert c.post("/api/investigations", json=PAYLOAD, headers={"X-API-Key": "wrong"}).status_code == 401
        ok = c.post("/api/investigations", json=PAYLOAD, headers={"X-API-Key": "s3cret"})
        assert ok.status_code == 202
        assert c.get("/api/investigations/BUG-1").status_code == 401
        assert c.get("/api/investigations/BUG-1", headers={"X-API-Key": "s3cret"}).status_code == 200


# /ready returns 503 without an LLM API key and 200 once a key is set.
def test_readiness_reflects_llm_key(monkeypatch):
    with make_client(FakeClient(tool_response(0.9))) as c:
        monkeypatch.setattr(models.settings, "llm_provider", "gemini")
        monkeypatch.setattr(models.settings, "gemini_api_key", "")
        r = c.get("/ready")
        assert r.status_code == 503 and r.json()["ready"] is False
        monkeypatch.setattr(models.settings, "gemini_api_key", "k")
        assert c.get("/ready").status_code == 200


# Saved investigations are reloaded after a restart, and runs that were in progress become FAILED.
def test_investigations_survive_restart_and_interrupted_ones_fail():
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert c.get("/api/investigations/BUG-1").json()["status"] == "SUCCESS"

    import store

    interrupted = models.Investigation(
        bug_id="BUG-2", request=AcceptRequest(bug_id="BUG-2", description="x"),
        status=models.InvestigationStatus.IN_PROGRESS,
    )
    store.save(interrupted)

    with make_client(FakeClient(tool_response(0.9))) as c:  # new app instance = restart
        assert c.get("/api/investigations/BUG-1").json()["status"] == "SUCCESS"
        assert "Probable Root Cause" in c.get("/api/investigations/BUG-1/report").text
        s = c.get("/api/investigations/BUG-2").json()
        assert s["status"] == "FAILED" and "restart" in s["message"]


# The callback is retried after a server error and finally delivers the summary with the API key.
def test_callback_delivers_summary_with_retry(monkeypatch):
    from callback import notify_callback

    monkeypatch.setattr("callback.RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(models.settings, "callback_url", "http://backend.test/hook")
    monkeypatch.setattr(models.settings, "callback_api_key", "cb-key")
    calls = []

    def handler(request: httpx.Request):
        calls.append((json.loads(request.content), request.headers.get("x-api-key")))
        return httpx.Response(500 if len(calls) == 1 else 200)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = models.InvestigationSummary(
        bug_id="BUG-1", status=models.InvestigationStatus.SUCCESS, message="ok", success=True
    )
    msg = run(notify_callback(summary, http))
    assert "delivered" in msg and len(calls) == 2
    assert calls[1][0]["bug_id"] == "BUG-1" and calls[1][0]["status"] == "SUCCESS" and calls[1][1] == "cb-key"


# A permanently failing callback reports failure without raising.
def test_callback_failure_is_non_fatal(monkeypatch):
    from callback import notify_callback

    monkeypatch.setattr("callback.RETRY_DELAYS", (0,))
    monkeypatch.setattr(models.settings, "callback_url", "http://backend.test/hook")
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    summary = models.InvestigationSummary(
        bug_id="BUG-1", status=models.InvestigationStatus.FAILED, message="x", success=False
    )
    assert "failed after retries" in run(notify_callback(summary, http))


# Finishing an investigation sends exactly one callback and logs it in the audit trail.
def test_finished_investigation_triggers_callback(monkeypatch):
    sent = []

    async def fake_notify(summary, http=None):
        sent.append(summary)
        return "callback delivered (HTTP 200)"

    monkeypatch.setattr("app.notify_callback", fake_notify)
    monkeypatch.setattr(models.settings, "callback_url", "http://backend.test/hook")
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        d = c.get("/api/investigations/BUG-1/details").json()
    assert len(sent) == 1 and sent[0].status.value == "SUCCESS" and sent[0].success is True
    assert any("Backend notification" in e["event"] for e in d["audit"])


# normalize_incident maps different field-name spellings and falls back to the raw document.
def test_normalize_incident_handles_common_field_names():
    from central import normalize_incident

    doc = {"id": "7", "bugDescription": "DB down", "serviceName": "orders", "priority": "high",
           "logLines": ["ERROR a", "ERROR b"]}
    assert normalize_incident(doc) == {
        "description": "DB down", "service": "orders", "severity": "high", "logs": ["ERROR a", "ERROR b"],
    }
    assert normalize_incident({"logs": "l1\nl2", "message": "m"})["logs"] == ["l1", "l2"]
    assert "unknown" in normalize_incident({"id": "1", "weird": "unknown"})["description"]


# fetch_incident returns data on 200 and None for 404 and server errors.
def test_fetch_incident_from_central(monkeypatch):
    from central import fetch_incident

    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")
    seen = []

    def handler(request: httpx.Request):
        seen.append(str(request.url))
        if request.url.path.endswith("/MISSING"):
            return httpx.Response(404)
        if request.url.path.endswith("/BROKEN"):
            return httpx.Response(500)
        return httpx.Response(200, json={"id": "BUG-9", "description": "Cart fails", "service": "cart"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    data, note = run(fetch_incident("BUG-9", http))
    assert data["description"] == "Cart fails" and seen[0] == "http://central.test:8080/api/incidents/BUG-9"
    assert run(fetch_incident("MISSING", http))[0] is None
    data, note = run(fetch_incident("BROKEN", http))
    assert data is None and "unavailable" in note


# A description is required unless the central service is configured to supply it.
def test_description_required_unless_central_configured(monkeypatch):
    with make_client(FakeClient(tool_response(0.9))) as c:
        assert c.post("/api/investigations", json={"bug_id": "BUG-1"}).status_code == 422

    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")
    seen = {}

    async def fake_fetch(bug_id, http=None):
        return {"description": "Cart fails", "service": "cart", "logs": ["ERROR cart npe"]}, "fetched"

    monkeypatch.setattr("app.fetch_incident", fake_fetch)
    fake = FakeClient(tool_response(0.9))
    with make_client(fake) as c:
        assert c.post("/api/investigations", json={"bug_id": "BUG-1"}).status_code == 202
        d = c.get("/api/investigations/BUG-1/details").json()
        assert d["status"] == "SUCCESS"
        assert d["request"]["description"] == "Cart fails" and d["request"]["service"] == "cart"
    assert "ERROR cart npe" in fake.calls[-1]["messages"][0]["content"]


# If central is down and no description was given, the investigation fails with a clear message.
def test_central_down_and_no_description_fails_clearly(monkeypatch):
    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")

    async def fake_fetch(bug_id, http=None):
        return None, "central service unavailable"

    monkeypatch.setattr("app.fetch_incident", fake_fetch)
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
        d = c.get("/api/investigations/BUG-1/details").json()
        assert d["status"] == "FAILED" and "description is missing" in d["error"]


# If central is down but a description was given, the investigation still succeeds.
def test_central_down_but_description_given_still_succeeds(monkeypatch):
    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")

    async def fake_fetch(bug_id, http=None):
        return None, "central service unavailable"

    monkeypatch.setattr("app.fetch_incident", fake_fetch)
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert c.get("/api/investigations/BUG-1").json()["status"] == "SUCCESS"


# The {bug_id} placeholder in the callback URL is replaced with the URL-encoded bug ID.
def test_callback_url_supports_bug_id_placeholder(monkeypatch):
    from callback import notify_callback

    monkeypatch.setattr(models.settings, "callback_url", "http://central.test:8080/api/incidents/{bug_id}/ai-result")
    seen = []
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (seen.append(str(r.url)), httpx.Response(200))[1]))
    summary = models.InvestigationSummary(
        bug_id="BUG 1", status=models.InvestigationStatus.SUCCESS, message="ok", success=True
    )
    run(notify_callback(summary, http))
    assert seen == ["http://central.test:8080/api/incidents/BUG%201/ai-result"]


# push_status POSTs approve/reject to central with the X-Initiated-By marker header.
def test_push_status_calls_central_with_marker_header(monkeypatch):
    from central import push_status

    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, str(request.url), request.headers.get("x-initiated-by")))
        return httpx.Response(200)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert "succeeded" in run(push_status("BUG-1", "approve", http))
    assert calls == [("POST", "http://central.test:8080/api/incidents/BUG-1/approve", "ai-agent")]

    bad = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    assert "failed" in run(push_status("BUG-1", "reject", bad))


# Helper: enables central integration with fake fetch/push functions and returns the list of pushed actions.
def central_pushes(monkeypatch):
    monkeypatch.setattr(models.settings, "central_url", "http://central.test:8080")
    pushed = []

    async def fake_fetch(bug_id, http=None):
        return {"description": "Cart fails", "service": "cart", "logs": ["ERROR cart npe"]}, "fetched"

    async def fake_push(bug_id, action, http=None):
        pushed.append((bug_id, action))
        return f"central {action} succeeded (HTTP 200)"

    monkeypatch.setattr("app.fetch_incident", fake_fetch)
    monkeypatch.setattr("app.push_status", fake_push)
    return pushed


# A successful investigation pushes "approve" to the central service.
def test_success_pushes_approve_to_central(monkeypatch):
    pushed = central_pushes(monkeypatch)
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
        d = c.get("/api/investigations/BUG-1/details").json()
    assert pushed == [("BUG-1", "approve")]
    assert d["log_source"] == "central service" and d["log_line_count"] == 1
    assert any("central approve succeeded" in e["event"] for e in d["audit"])


# A failed investigation pushes "reject" to the central service.
def test_failure_pushes_reject_to_central(monkeypatch):
    pushed = central_pushes(monkeypatch)
    with make_client(FakeClient(error=RuntimeError("boom"))) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
        assert c.get("/api/investigations/BUG-1").json()["status"] == "FAILED"
    assert pushed == [("BUG-1", "reject")]


# A low-confidence result pushes nothing to central and leaves the bug for an engineer.
def test_low_confidence_pushes_nothing(monkeypatch):
    pushed = central_pushes(monkeypatch)
    with make_client(FakeClient(tool_response(0.2))) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
        d = c.get("/api/investigations/BUG-1/details").json()
    assert pushed == [] and d["status"] == "NEEDS_REVIEW"
    assert any("No status pushed" in e["event"] for e in d["audit"])


# Pushing status to central can be turned off with central_push_status.
def test_push_can_be_disabled(monkeypatch):
    pushed = central_pushes(monkeypatch)
    monkeypatch.setattr(models.settings, "central_push_status", False)
    with make_client(FakeClient(tool_response(0.9))) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
    assert pushed == []


# Central's callback after our own approve doesn't start a new run; force=true does re-run.
def test_callback_from_central_after_success_does_not_loop(monkeypatch):
    pushed = central_pushes(monkeypatch)
    fake = FakeClient(tool_response(0.9))
    with make_client(fake) as c:
        c.post("/api/investigations", json={"bug_id": "BUG-1"})
        calls_after_first_run = len(fake.calls)
        again = c.post("/api/investigations", json={"bug_id": "BUG-1"})  # central re-calls us after approve
        assert again.status_code == 200 and again.json()["status"] == "SUCCESS"
        assert len(fake.calls) == calls_after_first_run and pushed == [("BUG-1", "approve")]

        forced = c.post("/api/investigations?force=true", json={"bug_id": "BUG-1"})
        assert forced.status_code == 202
        assert len(fake.calls) > calls_after_first_run

