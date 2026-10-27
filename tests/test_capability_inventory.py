"""R-750 (ROADMAP_V5 §١.٢ — بأمر المالك D-042): جرد القدرات الصادق الآلي.

معيار الإغلاق: نقطة `/capabilities` تُبنى من السجل الفعلي (سجل الأدوات +
الأعلام + حالة مفتاح التوقيع + القرص السحابي) لا من قائمة ثابتة، وتُختبر
بمطابقة عكسية: قدرة معطلة أو محجوبة أو غير مبنية **لا تُعلن متاحة** أبدًا.

مستويات الدليل المعلنة (لا مستوى «مثبت حيًا» من داخل العملية — الإثبات الحي
دليل خارجي يُوثق في forensics/، ولا يدّعيه النظام عن نفسه):
- missing: لا كود في السجل (الأداة المرتكز غير مسجلة).
- deferred: مؤجل بقرار المالك.
- implemented_disabled: الكود مسجل ومختبر لكن غير مفعّل في هذا التشغيل.
- blocked: مفعّل لكن تبعيته الصلبة غائبة (لا مفتاح توقيع → لا أثر = لا تنفيذ).
- enabled: مفعّل في هذا التشغيل وتبعياته قائمة.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

ALL_TOOLS = {
    "health.snapshot", "memory.stats", "disk.status", "brain.status",
    "web.search", "web.fetch", "web.summarize", "research.run",
    "media.image", "sovereignty.score", "reasoning.plan",
}
ALL_FLAGS_ON = {"brain": True, "web_tools": True, "media": True,
                "vision": True, "stt": True, "tts": True, "mcp": True,
                "web_search": True}  # R-789c: علم البحث المشتق (مزود فعلي)
ALL_FLAGS_OFF = {k: False for k in ALL_FLAGS_ON}


def _build(**kw):
    import capability_inventory
    args = dict(tool_names=ALL_TOOLS, flags=ALL_FLAGS_ON, signing_ok=True,
                cloud_disk_enabled=True)
    args.update(kw)
    return capability_inventory.build_inventory(**args)


def _by_id(inv):
    return {c["id"]: c for c in inv["capabilities"]}


def test_module_and_levels_declared():
    import capability_inventory
    assert set(capability_inventory.LEVELS) == {
        "missing", "deferred", "implemented_disabled", "blocked", "enabled"}
    assert "live_proven" not in capability_inventory.LEVELS


def test_disabled_flags_never_announced_enabled():
    """مطابقة عكسية ١: كل الأعلام مطفأة → لا قدرة مرتكزة على علم تُعلن enabled."""
    caps = _by_id(_build(flags=ALL_FLAGS_OFF))
    for cid in ("brain", "web_tools", "media", "vision", "stt", "tts", "mcp"):
        assert caps[cid]["level"] == "implemented_disabled", (cid, caps[cid])


def test_unregistered_tool_is_missing_even_if_flag_on():
    """مطابقة عكسية ٢: العلم وحده لا يصنع قدرة — أداة غير مسجلة = missing."""
    caps = _by_id(_build(tool_names=ALL_TOOLS - {"web.search", "media.image"}))
    assert caps["web_tools"]["level"] == "missing"
    assert caps["media"]["level"] == "missing"


def test_no_signing_key_blocks_tool_invocation():
    """مطابقة عكسية ٣: بلا مفتاح توقيع نشط (R-635) كل قدرة تتطلب أثرًا
    موقّعًا محجوبة — لا تُعلن enabled حتى لو أعلامها مفعّلة."""
    caps = _by_id(_build(signing_ok=False))
    assert caps["ledger_signing"]["level"] == "blocked"
    assert caps["tool_invocation"]["level"] == "blocked"
    for cid in ("web_tools", "media", "mcp"):
        assert caps[cid]["level"] == "blocked", (cid, caps[cid])
    assert all(c["level"] != "enabled" for c in caps.values()
               if c.get("requires_signing")), caps


def test_roadmap_gaps_are_missing_until_their_tool_exists():
    """القدرات الغائبة (خزينة/حلقة وكيل/مهام دائمة/مهارات/أسطول) مرتكزة
    على أدوات السجل: لا أداة = missing بإشارة لبند الخارطة."""
    caps = _by_id(_build())
    gaps = {"secrets_vault": "١.٥", "agent_loop": "§٢", "durable_tasks": "§٣",
            "skill_acquisition": "§٤", "agent_fleet": "§٥"}
    for cid, ref in gaps.items():
        assert caps[cid]["level"] == "missing", (cid, caps[cid])
        assert ref in caps[cid]["roadmap"], (cid, caps[cid])
    # وحين تُسجل الأداة المرتكز فقط يتغير المستوى (البناء من السجل لا قائمة ثابتة)
    anchor = caps["agent_loop"]["anchor_tool"]
    caps2 = _by_id(_build(tool_names=ALL_TOOLS | {anchor}))
    assert caps2["agent_loop"]["level"] != "missing"


def test_code_execution_deferred_by_owner():
    caps = _by_id(_build())
    assert caps["code_execution"]["level"] == "deferred"
    assert "D-041" in caps["code_execution"]["note"]


def test_persistent_memory_follows_cloud_disk():
    assert _by_id(_build(cloud_disk_enabled=False))[
        "persistent_memory"]["level"] == "implemented_disabled"
    assert _by_id(_build(cloud_disk_enabled=True))[
        "persistent_memory"]["level"] == "enabled"


def test_summary_counts_and_no_live_proof_claim():
    inv = _build(flags=ALL_FLAGS_OFF, signing_ok=False, cloud_disk_enabled=False)
    total = sum(inv["summary"].values())
    assert total == len(inv["capabilities"])
    assert inv["summary"].get("enabled", 0) == 0
    assert "live_proof" in inv and "forensics" in inv["live_proof"]


def test_endpoint_built_from_live_registry():
    """النقطة الحية تُبنى من السجل الفعلي: كل أداة مرتكز معلنة مسجلة فعلًا
    في /tools/list، ولا سر في المخرجات."""
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.get("/capabilities")
        assert r.status_code == 200, r.text
        data = r.json()
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
    caps = _by_id(data)
    for c in caps.values():
        if c["level"] in ("enabled", "blocked", "implemented_disabled") \
                and c.get("anchor_tool"):
            assert c["anchor_tool"] in names, c
        if c.get("anchor_tool") and c["anchor_tool"] not in names \
                and c["level"] != "deferred":
            assert c["level"] == "missing", c
    blob = r.text.lower()
    for bad in ("api_key", "secret_key", "private_key", "password"):
        assert bad not in blob, bad



def test_web_search_not_enabled_by_flag_alone():
    """R-789c — دليل حي: /capabilities أعلن «البحث» مفعّلًا بلا مزود بحث، فكرر العقل الادعاء."""
    flags = dict(ALL_FLAGS_ON, web_search=False)
    caps = _by_id(_build(flags=flags))
    assert caps["web_tools"]["level"] == "implemented_disabled"
    assert caps["research"]["level"] == "implemented_disabled"
    assert caps["web_fetch"]["level"] == "enabled"


def test_endpoint_web_search_requires_provider(monkeypatch):
    import app as app_mod
    import config
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True, raising=False)
    monkeypatch.setattr(app_mod, "_search_configured", lambda: False)
    caps = _by_id(app_mod._capabilities_payload())
    assert caps["web_tools"]["level"] != "enabled"
    assert caps["research"]["level"] != "enabled"
