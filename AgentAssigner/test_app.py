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
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response, self._error = response, error
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def make_client(fake):
    return TestClient(create_app(DebugAgent(client=fake, model="test-model")))


PAYLOAD = {"bug_id": "BUG-1", "description": "Checkout API timing out", "service": "checkout"}


@pytest.fixture(autouse=True)
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(models.settings, "reports_dir", str(tmp_path / "reports"))
    monkeypatch.setattr(models.settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(models.settings, "log_api_url", "")
    monkeypatch.setattr(models.settings, "log_file_path", "")
    monkeypatch.setattr(models.settings, "service_api_key", "")
    monkeypatch.setattr(models.settings, "callback_url", "")
    monkeypatch.setattr(models.settings, "callback_api_key", "")


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


def test_low_confidence_needs_review():
    with make_client(FakeClient(tool_response(0.2))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "NEEDS_REVIEW" and s["success"] is False


def test_llm_failure_reports_failed():
    with make_client(FakeClient(error=RuntimeError("boom"))) as c:
        c.post("/api/investigations", json=PAYLOAD)
        s = c.get("/api/investigations/BUG-1").json()
        assert s["status"] == "FAILED" and s["success"] is False
        assert "boom" in c.get("/api/investigations/BUG-1/details").json()["error"]
        assert "Error" in c.get("/api/investigations/BUG-1/report").text


def test_unknown_bug_and_validation():
    with make_client(FakeClient(tool_response(0.9))) as c:
        assert c.get("/api/investigations/NOPE").status_code == 404
        assert c.post("/api/investigations", json={"bug_id": "", "description": "x"}).status_code == 422


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


def gemini_client(handler):
    return make_gemini(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def make_gemini(http):
    return TestClient(create_app(GeminiAgent(http_client=http, model="gemini-test")))


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


def test_gemini_garbage_output_fails(monkeypatch):
    monkeypatch.setattr(models.settings, "gemini_api_key", "test-key")
    body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    with gemini_client(lambda r: httpx.Response(200, json=body)) as c:
        c.post("/api/investigations", json=PAYLOAD)
        assert c.get("/api/investigations/BUG-1").json()["status"] == "FAILED"


def test_parse_log_payload_formats():
    assert parse_log_payload('["a", "b"]') == ["a", "b"]
    assert parse_log_payload('{"logs": [{"level": "ERROR", "message": "db down"}]}') == ["ERROR db down"]
    assert parse_log_payload('{"data": [{"foo": 1}]}') == ['{"foo": 1}']
    assert parse_log_payload("line1\n\nline2\n") == ["line1", "line2"]


def run(coro):
    return asyncio.run(coro)


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


def test_fetch_logs_falls_back_to_file(monkeypatch, tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("INFO checkout ok\nERROR checkout pool exhausted\nINFO billing ok\n")
    monkeypatch.setattr(models.settings, "log_api_url", "http://logs.test/logs")
    monkeypatch.setattr(models.settings, "log_file_path", str(log_file))
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    res = run(fetch_logs(AcceptRequest(**PAYLOAD), http))
    assert res.lines == ["INFO checkout ok", "ERROR checkout pool exhausted"]  # filtered to the service
    assert "log file" in res.source and any("log API unavailable" in n for n in res.notes)


def test_fetch_logs_nothing_configured():
    res = run(fetch_logs(AcceptRequest(**PAYLOAD)))
    assert res.lines == [] and res.source == "none" and res.notes


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


def test_readiness_reflects_llm_key(monkeypatch):
    with make_client(FakeClient(tool_response(0.9))) as c:
        monkeypatch.setattr(models.settings, "llm_provider", "gemini")
        monkeypatch.setattr(models.settings, "gemini_api_key", "")
        r = c.get("/ready")
        assert r.status_code == 503 and r.json()["ready"] is False
        monkeypatch.setattr(models.settings, "gemini_api_key", "k")
        assert c.get("/ready").status_code == 200


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


def test_callback_failure_is_non_fatal(monkeypatch):
    from callback import notify_callback

    monkeypatch.setattr("callback.RETRY_DELAYS", (0,))
    monkeypatch.setattr(models.settings, "callback_url", "http://backend.test/hook")
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    summary = models.InvestigationSummary(
        bug_id="BUG-1", status=models.InvestigationStatus.FAILED, message="x", success=False
    )
    assert "failed after retries" in run(notify_callback(summary, http))


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

