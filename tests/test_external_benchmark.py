"""R-746 (البند ٤.٤ — المقارنة بالعالم الخارجي): معايير دورية تُقارن بمرجعية
خارجية عامة وتوثّق الفجوات.

المراجع (عامة، منشورة، كل منها برابط وتاريخ استرجاع):
- زمن الرد: Nielsen «Response Times: The 3 Important Limits» (0.1/1/10 ث)
  + Google RAIL (معالجة الإدخال ≤ 50ms لرد مرئي ≤ 100ms).
- جودة الرد: عينة مثبتة من GSM8K test (MIT، مراجعة 3101c7d، sha256 للملف).
- تغطية الأدوات: الأدوات المدمجة المعلنة في OpenAI «Using tools» وClaude
  «Tool reference» — الحالة تُحسب وقت التشغيل من السجل الفعلي لا من ادعاء.

1. كل مرجع برابط https وتاريخ؛ العينة مثبتة بمراجعة وبصمة.
2. تصنيف الزمن حسب حدود Nielsen، وفجوة RAIL معلنة بالأرقام.
3. التغطية: available / built_disabled / deferred / missing من السجل والأعلام.
4. الجودة بلا عقل = unmeasured معلن بسبب — لا رقم مختلق.
5. الجودة بعقل: مطابقة الجواب العددي (يقبل الفواصل) ودقة على n.
6. الفجوات القابلة للقياس تغذي اقتراحات ٤.٥ (benchmark_gap:*).
7. مهمة مجدولة external_benchmark ← benchmark.run.
8. حلقة حقيقية: السجل → /benchmark/report بتغطية من السجل الفعلي، بلا سر.
"""

import importlib
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def eb():
    import external_benchmark
    importlib.reload(external_benchmark)
    return external_benchmark


def test_references_are_public_cited_and_pinned(eb):
    for key, ref in eb.REFERENCES.items():
        assert ref["url"].startswith("https://"), key
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", ref["retrieved"]), key
    g = eb.GSM8K_SAMPLE
    assert g["revision"].startswith("3101c7d")
    assert len(g["sha256"]) == 64 and g["license"] == "MIT"
    assert len(g["items"]) >= 5
    assert all(isinstance(i["answer"], int) for i in g["items"])
    for c in eb.CAPABILITY_CATALOG:
        assert c["refs"] and all(r in eb.REFERENCES for r in c["refs"]), c["id"]


def test_latency_classified_by_nielsen_and_rail_gap(eb):
    assert eb.classify_latency(40)["band"] == "instant"
    assert eb.classify_latency(400)["band"] == "flow"
    assert eb.classify_latency(4000)["band"] == "attention"
    assert eb.classify_latency(12000)["band"] == "beyond_attention"
    r = eb.latency_metric("health_snapshot", 80.0, budget_ms=eb.RAIL_HANDLER_BUDGET_MS)
    assert r["gap_ms"] == pytest.approx(30.0) and r["within_budget"] is False
    r = eb.latency_metric("health_snapshot", 20.0, budget_ms=eb.RAIL_HANDLER_BUDGET_MS)
    assert r["gap_ms"] == 0 and r["within_budget"] is True


def test_coverage_status_from_registry_and_flags(eb):
    cov = eb.capability_coverage(
        tool_names={"web.search", "web.fetch", "health.snapshot"},
        flags={"web_tools": False, "media": False})
    st = {c["id"]: c["status"] for c in cov["items"]}
    assert st["function_calling"] == "available"
    assert st["web_search"] == "built_disabled"
    assert st["code_execution"] == "deferred"
    assert st["file_search"] == "missing"
    c = next(c for c in cov["items"] if c["id"] == "code_execution")
    assert "D-041" in c["note"]
    assert cov["total"] == len(eb.CAPABILITY_CATALOG)
    assert cov["available"] + cov["built_disabled"] + cov["deferred"] + cov["missing"] == cov["total"]
    cov2 = eb.capability_coverage({"web.search", "web.fetch", "mcp.x.y"},
                                  {"web_tools": True, "media": False})
    st2 = {c["id"]: c["status"] for c in cov2["items"]}
    assert st2["web_search"] == "available" and st2["remote_mcp"] == "available"


def test_quality_without_mind_is_unmeasured_not_invented(eb):
    q = eb.quality_probe(None, n=3)
    assert q["status"] == "unmeasured" and q["reason"]
    assert "accuracy" not in q


def test_quality_with_mind_scores_numeric_answers(eb):
    items = eb.GSM8K_SAMPLE["items"]
    answers = {i["question"]: i["answer"] for i in items}

    def fake_mind(system, question):
        a = answers[question]
        if a == items[0]["answer"]:
            return "work...\nAnswer: wrong"
        return f"reasoning\nAnswer: {a:,}"

    q = eb.quality_probe(fake_mind, n=3, timer=iter([0.0, 0.5] * 10).__next__)
    assert q["status"] == "measured" and q["n"] == 3
    assert q["correct"] == 2 and q["accuracy"] == pytest.approx(2 / 3)
    assert q["latency"]["median_ms"] == pytest.approx(500.0)
    assert eb.extract_number("Answer: 70,000") == 70000


def test_measurable_gaps_feed_improvement_proposals(eb):
    import improvement_proposals
    book = improvement_proposals.ProposalBook()
    report = {"gaps": [{"metric": "health_snapshot_latency", "observed": 80.0,
                        "reference": "RAIL ≤ 50ms", "gap": "30.0ms"}]}
    book.ingest(eb.gaps_as_defects(report), now=1.0)
    p = book.list()[0]
    assert p["defect_id"] == "benchmark_gap:health_snapshot_latency"
    assert p["status"] == "proposed" and "RAIL" in p["evidence"]


def test_scheduled_task_registered():
    import scheduler
    t = next(t for t in scheduler.build_from_env().tasks if t.name == "external_benchmark")
    assert t.tool == "benchmark.run"


def test_real_loop_report_from_real_registry():
    from fastapi.testclient import TestClient
    import app as app_module
    import tool_registry
    with TestClient(app_module.app) as client:
        out = tool_registry.get_registry().invoke("benchmark.run", caller="test_r746")
        assert out["ok"] is True, out
        r = client.get("/benchmark/report").json()["report"]
        st = {c["id"]: c["status"] for c in r["coverage"]["items"]}
        assert st["web_search"] in ("built_disabled", "available")
        assert st["code_execution"] == "deferred"
        assert r["latency"]["health_snapshot"]["observed_ms"] >= 0
        assert r["quality"]["status"] == "unmeasured"  # العقل معطل في الاختبارات
        assert "references" in r and r["references"]["nielsen_response_times"]["url"]
        text = str(r)
        for w in ("Bearer ", "api_key", "private_key"):
            assert w not in text
