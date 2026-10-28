"""R-750 (ROADMAP_V5 §١.٢ — بأمر المالك D-042): جرد القدرات الصادق الآلي.

يجيب عن سؤال المالك «ماذا يستطيع النظام فعلًا الآن؟» من الحالة الحية لا من
قائمة ادعاءات: كل قدرة مرتكزة على أداة في سجل الأدوات الفعلي (أو على علم
تشغيل لنقاط ليست أدوات)، ومستواها يُحسب من أربعة مدخلات حية فقط:
أسماء الأدوات المسجلة + الأعلام + حالة مفتاح التوقيع + القرص السحابي.

مبادئ:
- لا ادعاء: أداة مرتكز غير مسجلة = missing مهما كان العلم.
- لا أثر = لا تنفيذ (R-635): بلا مفتاح توقيع نشط كل قدرة تتطلب أثرًا موقّعًا
  محجوبة (blocked) لا متاحة.
- لا «مثبت حيًا» من داخل العملية: الإثبات الحي دليل خارجي (طلب حقيقي عبر
  المنشور) يُوثق في forensics/ — النظام لا يشهد لنفسه.
- لا سر في المخرجات (المادة ٩): أسماء وأعلام ومستويات فقط.
"""

from typing import Any, Dict, Iterable, List, Optional

LEVELS = ("missing", "deferred", "implemented_disabled", "blocked", "enabled")

# id, name, anchor_tool (أداة السجل المرتكز — None لنقاط ليست أدوات),
# flag (علم التشغيل — None = لا علم), requires_signing, roadmap, note
CATALOG: List[Dict[str, Any]] = [
    {"id": "ledger_signing", "name": "توقيع السجل السيادي",
     "anchor_tool": None, "flag": None, "requires_signing": True,
     "roadmap": "V5 ١.٣", "note": "مفتاح التوقيع بيد المالك (المادة ٧)"},
    {"id": "tool_invocation", "name": "استدعاء الأدوات بأثر موقّع",
     "anchor_tool": "health.snapshot", "flag": None, "requires_signing": True,
     "roadmap": "R-729", "note": "/tools/invoke — لا أثر = لا تنفيذ"},
    {"id": "brain", "name": "العقل (نموذج لغوي حي)",
     "anchor_tool": "brain.status", "flag": "brain", "requires_signing": False,
     "roadmap": "V5 ١.٦", "note": "OLLAMA_ENABLED + OLLAMA_MODEL بيد المالك"},
    # R-789c: كان «البحث والقراءة» قدرة واحدة يكفيها العلم ⇒ أُعلنت «مفعّلة» حيًا بلا مزود
    # بحث، فكرر العقل الادعاء للمالك. الآن: القراءة بعلم الأدوات، والبحث بعلم مشتق يشترط مزودًا فعليًا.
    {"id": "web_tools", "name": "البحث في الويب",
     "anchor_tool": "web.search", "flag": "web_search", "requires_signing": True,
     "roadmap": "R-736", "note": "WEB_TOOLS_ENABLED + مزود بحث فعلي (searxng بعنوان خارجي أو tavily بمفتاحه)"},
    {"id": "web_fetch", "name": "قراءة صفحات الويب ومستودعات GitHub",
     "anchor_tool": "web.fetch", "flag": "web_tools", "requires_signing": True,
     "roadmap": "R-736 / R-789", "note": "WEB_TOOLS_ENABLED — حارس SSRF"},
    {"id": "research", "name": "خط البحث الثابت",
     "anchor_tool": "research.run", "flag": "web_search", "requires_signing": True,
     "roadmap": "R-737", "note": "خط ثابت — ليس حلقة وكيل عامة (§٢)"},
    {"id": "media", "name": "توليد الصور ذاتي الاستضافة",
     "anchor_tool": "media.image", "flag": "media", "requires_signing": True,
     "roadmap": "R-747", "note": "MEDIA_ENABLED + MEDIA_BASE_URL"},
    {"id": "vision", "name": "الرؤية", "anchor_tool": None, "flag": "vision",
     "requires_signing": False, "roadmap": "R-741",
     "note": "VISION_ENABLED + VISION_MODEL"},
    {"id": "stt", "name": "تحويل الكلام إلى نص", "anchor_tool": None,
     "flag": "stt", "requires_signing": False, "roadmap": "R-740",
     "note": "STT_ENABLED"},
    {"id": "tts", "name": "تحويل النص إلى كلام", "anchor_tool": None,
     "flag": "tts", "requires_signing": False, "roadmap": "R-742",
     "note": "TTS_ENABLED + TTS_MODEL"},
    {"id": "mcp", "name": "موصلات MCP البعيدة", "anchor_tool": None,
     "flag": "mcp", "requires_signing": True, "roadmap": "R-738 / V5 §٤.١",
     "note": "MCP_ENABLED + MCP_SERVERS بيد المالك"},
    {"id": "persistent_memory", "name": "ذاكرة دائمة عبر النشر",
     "anchor_tool": "disk.status", "flag": "cloud_disk",
     "requires_signing": False, "roadmap": "V5 ١.٤",
     "note": "سرّا Supabase (الرابط + مفتاح الخدمة) بيد المالك — الاستمرارية عبر نشر فعلي لم تُثبت"},
    {"id": "code_execution", "name": "تنفيذ الكود", "anchor_tool": None,
     "flag": None, "requires_signing": True, "roadmap": "V4 ٣.٣",
     "note": "مؤجل بقرار المالك (D-041)", "deferred": True},
    # فجوات V5 — مرتكزة على أدوات لم تُبنَ بعد: تسجيلها وحده يغير المستوى
    {"id": "secrets_vault", "name": "خزينة أسرار الموصلات",
     "anchor_tool": "vault.status", "flag": "vault", "requires_signing": True,
     "roadmap": "V5 ١.٥",
     "note": "مبنية (R-752: AES-256-GCM + حصر نطاقي + تدقيق إلزامي) — التمكين "
             "يتطلب المفتاح الرئيسي SOVEREIGN_VAULT_MASTER_KEY بيد المالك، "
             "والتدقيق يتطلب مفتاح توقيع (١.٣)"},
    {"id": "agent_loop", "name": "حلقة الوكيل العامة (هدف→خطة→تنفيذ→تحقق)",
     "anchor_tool": "agent.run", "flag": "brain", "requires_signing": True,
     "roadmap": "V5 §٢",
     "note": "مبنية (R-753: خطوة→أداة مسجلة→تحقق، ميزانيات، إلغاء، أثر agent_run) "
             "— التخطيط الحي يتطلب العقل (١.٦) والأثر يتطلب مفتاح توقيع (١.٣)"},
    {"id": "durable_tasks", "name": "مهام طويلة قابلة للاستئناف",
     "anchor_tool": "tasks.resume", "flag": "brain", "requires_signing": True,
     "roadmap": "V5 §٣",
     "note": "مبنية (R-754: نقاط تفتيش، استئناف بعد قتل فعلي، منع تكرار الفعل "
             "الخارجي، تقدم من القرص) — تتطلب العقل (١.٦) والتوقيع (١.٣)، "
             "والدوام عبر النشر يتطلب ١.٤"},
    {"id": "connectors", "name": "عقد الموصل المعزول (مصادقة/منحة/سحب/عزل)",
     "anchor_tool": "connectors.status", "flag": "vault", "requires_signing": True,
     "roadmap": "V5 ٤.١",
     "note": "مبني (R-756) وأول موصل: إشعار webhook — يتطلب سره في الخزينة "
             "(المفتاح الرئيسي بيد المالك) وعنوانه SOVEREIGN_WEBHOOK_URL والتوقيع (١.٣)"},
    {"id": "skill_acquisition", "name": "اكتساب المهارات",
     "anchor_tool": "skills.install", "flag": None, "requires_signing": True,
     "roadmap": "V5 §٤",
     "note": "مبني (R-757: حزمة→تقييم مرجعي→اعتماد المالك بأثر→أداة تدوم عبر إعادة "
             "التشغيل→تراجع) — الدوام عبر النشر ١.٤، والتقييم بمرجع مستقل يتطلب العقل"},
    {"id": "agent_fleet", "name": "إدارة أسطول وكلاء",
     "anchor_tool": "fleet.spawn", "flag": "brain", "requires_signing": True,
     "roadmap": "V5 §٥",
     "note": "مبني (R-758: عامل=حلقة R-753 بأثر fleet_event، منسق بسقف تزامن وعزل "
             "وإعادة جدولة، قياس 1000 فعلي في forensics/R-758_SCALE_REPORT.json) — "
             "العمال الحيون يتطلبون العقل (١.٦) والتوقيع (١.٣)، وقياس آلة Fly يتطلب ١.٧"},
]

# R-790/R-791 (V6 §٦.٩): العقل المدير — إنشاء الوكلاء ذاتيًا، الخبرة، الأهداف، الاستقلال
CATALOG.extend([
    {"id": "agent_manager", "name": "إنشاء الوكلاء ذاتيًا وإدارتهم (المدير)",
     "anchor_tool": "agent.manage", "flag": "brain", "requires_signing": True,
     "roadmap": "V6 ٦.٩.٢",
     "note": "R-790: العقل يقرر كم وكيلًا ودور كل منهم وهدفه، ينشئهم عبر الأسطول وينظمهم "
             "ويجمع نتائجهم — العقل واحد فيصطف الطلب عليه (لا تزامن حقيقي أكبر من العقل)"},
    {"id": "experience", "name": "اكتساب الخبرة والمعرفة",
     "anchor_tool": "experience.stats", "flag": None, "requires_signing": False,
     "roadmap": "V6 ٦.٩.١ / ٦.٩.٥",
     "note": "R-790: كل تشغيل يُسجل وقائعه (أدوات/حالة/خطأ) إلحاقيًا ويُسترجع للتخطيط التالي؛ "
             "حقائق بمصادرها — استرجاع بتشابه الكلمات لا بتضمين دلالي"},
    {"id": "goals", "name": "أهداف وخطط دائمة",
     "anchor_tool": "goals.work", "flag": "brain", "requires_signing": True,
     "roadmap": "V6 ٦.٩.٣",
     "note": "R-791: أهداف من المالك أو يقترحها العقل من ملاحظاته؛ خطة وقرار كل خطوة من العقل"},
    {"id": "autonomy", "name": "العمل الذاتي بلا طلب (حلقة الاستقلال)",
     "anchor_tool": "autonomy.tick", "flag": "autonomy", "requires_signing": True,
     "roadmap": "V6 ٦.٩.٤",
     "note": "R-791: SOVEREIGN_AUTONOMY=1 — لا أفعال موصلات خارجية ولا قرارات المالك ذاتيًا، "
             "وتنفيذ الكود محجوب (D-041)"},
])

# R-796: محرك التطوير الذاتي — من اقتراح نصي إلى تعديل كود باختبار RED→GREEN
CATALOG.append(
    {"id": "self_development", "name": "التطوير الذاتي للكود (مسودة → RED→GREEN → ترقية)",
     "anchor_tool": "selfdev.tick", "flag": "brain", "requires_signing": True,
     "roadmap": "V6 ٦.١٠ (R-796)",
     "note": "R-796: العقل يصوغ تعديلًا واختبارًا من مهام حقيقية (اقتراحات/المالك/أهداف متعذرة)؛ "
             "الإنتاج لا يكتب ملفًا — CI يطبّق على فرع work/selfdev-* ويثبت RED ثم GREEN؛ "
             "الترقية إلى main قرار المالك"})

LIVE_PROOF_NOTE = ("لا مستوى «مثبت حيًا» من داخل العملية — الإثبات الحي دليل "
                   "خارجي عبر المنشور يُوثق في forensics/")


def _level(cap: Dict[str, Any], names: set, flags: Dict[str, bool],
           signing_ok: bool) -> str:
    if cap.get("deferred"):
        return "deferred"
    if cap["id"] == "ledger_signing":
        return "enabled" if signing_ok else "blocked"
    anchor: Optional[str] = cap.get("anchor_tool")
    if anchor is not None and anchor not in names:
        return "missing"
    flag = cap.get("flag")
    if flag is not None and not flags.get(flag, False):
        return "implemented_disabled"
    if cap.get("requires_signing") and not signing_ok:
        return "blocked"
    if cap["id"] == "mcp" and not any(n.startswith("mcp.") for n in names):
        return "blocked"  # مفعّل بلا خادم مزامن في السجل — لا أداة فعلية
    return "enabled"


def build_inventory(tool_names: Iterable[str], flags: Dict[str, bool],
                    signing_ok: bool, cloud_disk_enabled: bool) -> Dict[str, Any]:
    """الجرد من المدخلات الحية — دالة نقية (قابلة للاختبار بمطابقة عكسية)."""
    names = set(tool_names or ())
    all_flags = dict(flags or {})
    all_flags["cloud_disk"] = bool(cloud_disk_enabled)
    caps = []
    for cap in CATALOG:
        level = _level(cap, names, all_flags, bool(signing_ok))
        caps.append({
            "id": cap["id"], "name": cap["name"], "level": level,
            "anchor_tool": cap.get("anchor_tool"), "flag": cap.get("flag"),
            "requires_signing": bool(cap.get("requires_signing")),
            "roadmap": cap["roadmap"], "note": cap["note"],
        })
    summary = {lv: sum(1 for c in caps if c["level"] == lv) for lv in LEVELS}
    return {"capabilities": caps, "summary": summary,
            "levels": list(LEVELS), "live_proof": LIVE_PROOF_NOTE,
            "inputs": {"registered_tools": len(names),
                       "signing_ok": bool(signing_ok),
                       "cloud_disk_enabled": bool(cloud_disk_enabled)}}
