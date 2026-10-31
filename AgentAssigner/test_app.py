from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import models
from agent import DebugAgent
from app import create_app


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
    monkeypatch.setattr(models.settings, "reports_dir", str(tmp_path))


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
        assert fake.calls[0]["model"] == "test-model"
        assert fake.calls[0]["tool_choice"]["name"] == "submit_analysis"


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
