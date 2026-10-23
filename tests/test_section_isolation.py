"""R-735 (البند ١.٣ — إغلاق، بأمر المالك «تابع»): أقسام منفصلة فعلًا ومعزولة.

معيار الإغلاق حرفيًا: «كل قسم يستهلك نقاطه الخاصة ويُختبر بمعزل؛ لا قسم يعرض
بيانات قسم آخر».

ما كشفه القياس الفعلي في متصفح (لا الافتراض):
- شريط أقسام R-727 كان أسفل التطبيق كامل الارتفاع (y=1413 في نافذة 1500)،
  أي غير مرئي عمليًا.
- الموجّه نقل `chat-input` من «مركز القيادة» إلى أسفل الصفحة، ففصله عن المحادثة.
- لوحة الحالة الحية position:fixed تطفو فوق كل الأقسام (بيانات قسم الأدوات في كل مكان).

الإصلاح: الأقسام تبويبات في الشريط الرئيسي المرئي، ولكل قسم لوحته، وخريطة
`sections` في LIVE_BINDINGS.json تعلن نقاط كل قسم ووحداته — ويُطابقها هذا الحارس.
"""

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
MANIFEST = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(encoding="utf-8"))
MAIN_JS = (FRONTEND / "js/main.js").read_text(encoding="utf-8")
SECTIONS = MANIFEST.get("sections", {})
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Ancestry(HTMLParser):
    """يسجل لكل معرّف سلسلة معرّفات أسلافه — لمعرفة اللوحة التي يقع فيها كل عنصر."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.ancestors = {}

    def handle_starttag(self, tag, attrs):
        el_id = dict(attrs).get("id")
        if el_id:
            self.ancestors[el_id] = [i for _, i in self.stack if i]
        if tag not in VOID:
            self.stack.append((tag, el_id))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                return


_P = _Ancestry()
_P.feed(INDEX)
ANC = _P.ancestors


def _pane_of(el_id):
    for a in reversed(ANC.get(el_id, [])):
        if a.startswith("tab-") and a != "tab-content":
            return a
    return None


def test_manifest_declares_sections_with_panes():
    for name in ("chat", "memory", "tools", "evolution"):
        assert name in SECTIONS, f"القسم «{name}» غير معلن في خريطة الأقسام"
        assert {"pane", "endpoints", "modules"} <= set(SECTIONS[name])


@pytest.mark.parametrize("name", ["memory", "tools", "evolution"])
def test_section_is_a_visible_main_tab(name):
    assert f'data-tab="{name}"' in INDEX, f"لا زر للقسم «{name}» في الشريط الرئيسي المرئي"
    pane = SECTIONS[name]["pane"]
    assert f"document.getElementById('{pane}')" in MAIN_JS, f"{pane} غير مسجل في tabContents"


@pytest.mark.parametrize("name", ["chat", "memory", "tools", "evolution"])
def test_section_root_lives_inside_its_pane(name):
    root = f"sovereign-section-{name}"
    assert root in ANC, f"{root} مفقود"
    assert _pane_of(root) == SECTIONS[name]["pane"], (
        f"{root} في {_pane_of(root)} لا في لوحته {SECTIONS[name]['pane']}"
    )


def test_no_hidden_secondary_nav_and_no_dom_relocation():
    assert 'id="sovereign-section-nav"' not in INDEX, "شريط أقسام ثانٍ مخفي أسفل الصفحة"
    assert "section-router.js" not in INDEX
    for js in (FRONTEND / "js").rglob("*.js"):
        src = js.read_text(encoding="utf-8", errors="ignore")
        assert not re.search(r"getElementById\([\"']chat-input[\"']\)[\s\S]{0,200}appendChild", src), (
            f"{js.name} ينقل حقل المحادثة من مكانه"
        )


def test_live_status_panel_does_not_float_over_sections():
    js = (FRONTEND / "js/modules/live-system-status.js").read_text(encoding="utf-8")
    assert "position:fixed" not in js.replace(" ", ""), "اللوحة تطفو فوق كل الأقسام"
    assert _pane_of("live-system-status") == SECTIONS["tools"]["pane"], "اللوحة ليست في قسم الأدوات"


def _fetched_endpoints(module):
    src = (FRONTEND / module).read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"fetch\(\s*[\"'](/[^\"'?]*)", src))


def test_each_section_module_consumes_only_its_own_endpoints():
    assert SECTIONS, "خريطة الأقسام فارغة — النجاح هنا سيكون فارغًا لا حقيقيًا"
    for name, sec in SECTIONS.items():
        own = {e.split(" ", 1)[1] for e in sec["endpoints"]}
        for mod in sec["modules"]:
            extra = _fetched_endpoints(mod) - own
            assert not extra, f"وحدة {mod} في قسم «{name}» تستهلك نقاط قسم آخر: {extra}"


def test_no_endpoint_shared_between_sections():
    assert SECTIONS, "خريطة الأقسام فارغة — النجاح هنا سيكون فارغًا لا حقيقيًا"
    seen = {}
    for name, sec in SECTIONS.items():
        for ep in sec["endpoints"]:
            assert ep not in seen, f"{ep} معروضة في «{seen.get(ep)}» و«{name}» معًا"
            seen[ep] = name


def test_every_bound_element_in_a_pane_uses_that_sections_endpoints():
    pane_to_section = {s["pane"]: n for n, s in SECTIONS.items()}
    for b in MANIFEST["bound"]:
        pane = _pane_of(b["element"])
        if b.get("created_by_writer") and pane is None:
            continue
        if pane is None:
            continue  # الرأس/التذييل: إطار عام مشترك لا قسم
        name = pane_to_section.get(pane)
        assert name, f"لوحة {pane} بلا قسم معلن"
        assert b["endpoint"] in SECTIONS[name]["endpoints"], (
            f"{b['element']} في قسم «{name}» يعرض {b['endpoint']} — بيانات قسم آخر"
        )


def _client():
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)


@pytest.mark.parametrize("name", ["monitor", "memory", "tools"])
def test_section_endpoints_work_in_isolation(name):
    """كل قسم يُختبر بمعزل: نقاط GET الخاصة به وحدها تعمل وتعيد JSON."""
    with _client() as c:
        for ep in SECTIONS[name]["endpoints"]:
            method, path = ep.split(" ", 1)
            if method != "GET":
                continue
            r = c.get(path)
            assert r.status_code == 200, f"قسم «{name}»: {ep} → {r.status_code}"
            assert isinstance(r.json(), dict)
