# -*- coding: utf-8 -*-
"""R-848: كتالوج أنماط الأسرار — المصدر الوحيد للتنقية والفحص.

لكل قاعدة: معرّف ثابت، وخطورة، ووصف دلالي، ونمط. ``scan=False`` يعني أن القاعدة
للتنقية فقط (مثل ``Bearer`` العام و``key=value``)، لأنها في المستودع تكثر في
الأمثلة والوثائق. أما التنقية فتطبق كل القواعد: الإفراط في الإخفاء أهون من التسرب.

لا اعتماد خارج المكتبة القياسية: تحمّله ``tools/gate_secrets.py`` بالمسار مباشرة.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

MASK = "***"


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str          # critical | high | medium
    description: str
    pattern: "re.Pattern[str]"
    scan: bool = True      # يدخل بوابة المستودع
    group: int = 0         # المجموعة التي تحمل القيمة السرية
    min_entropy: float = 0.0
    scan_min_len: int = 0  # في الفحص فقط: أقصر من الطول الحقيقي للصيغة = مثال/اختبار
    require_mixed: bool = False  # في الفحص فقط: يلزم حرف ورقم معًا (يستبعد المعرّفات)
    placeholders: bool = True    # هل يُستثنى «النائب» في الفحص


def _r(p: str, flags: int = 0) -> "re.Pattern[str]":
    return re.compile(p, flags)


RULES: Tuple[Rule, ...] = (
    Rule("pem_private_key", "critical", "رأس مفتاح خاص PEM (RSA/EC/OPENSSH/PKCS8)",
         _r(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----(?:[\s\S]*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----)?")),
    Rule("github_token", "critical", "رمز GitHub كلاسيكي/OAuth/تطبيق (ghp_/gho_/ghu_/ghs_/ghr_)",
         _r(r"\bgh[pousr]_[A-Za-z0-9]{8,}"), scan_min_len=40),
    Rule("github_fine_grained", "critical", "رمز GitHub دقيق الصلاحيات (github_pat_)",
         _r(r"\bgithub_pat_[A-Za-z0-9_]{8,}"), scan_min_len=50),
    Rule("render_api_key", "critical", "مفتاح Render API (rnd_)",
         _r(r"\brnd_[A-Za-z0-9]{8,}"), scan_min_len=24),
    Rule("supabase_pat", "critical", "رمز إدارة Supabase (sbp_)",
         _r(r"\bsbp_[A-Za-z0-9]{8,}"), scan_min_len=40),
    Rule("supabase_secret_key", "critical", "مفتاح Supabase السري الجديد (sb_secret_)",
         _r(r"\bsb_secret_[A-Za-z0-9_-]{8,}"), scan_min_len=26),
    Rule("jwt", "high", "JWT (منها مفتاح Supabase service_role)",
         _r(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    Rule("aws_access_key_id", "critical", "معرّف مفتاح AWS (AKIA/ASIA)",
         _r(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    Rule("stripe_secret_key", "critical", "مفتاح Stripe سري أو مقيّد (sk_/rk_ live/test)",
         _r(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}"), placeholders=False),
    Rule("google_api_key", "high", "مفتاح Google API (AIza)",
         _r(r"\bAIza[A-Za-z0-9_-]{35}\b")),
    Rule("openai_style_key", "high", "مفتاح بنمط sk- (OpenAI/Anthropic وأمثالهما)",
         _r(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{8,}"), scan_min_len=24),
    Rule("slack_token", "high", "رمز Slack (xox?-)",
         _r(r"\bxox[abprs]-[A-Za-z0-9-]{8,}"), scan_min_len=20),
    Rule("telegram_bot_token", "high", "رمز بوت Telegram (رقم:مفتاح)",
         _r(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}")),
    Rule("generic_assignment", "medium",
         "قيمة طويلة عالية العشوائية مسندة إلى اسم سري (password/secret/token/api_key…)",
         _r(r"(?i)\b[\w.-]*(?:password|passwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|token)[\w.-]*"
            r"[\"']?\s*[:=]\s*[\"']([A-Za-z0-9+/_=.-]{20,})[\"']"),
         group=1, min_entropy=3.5, require_mixed=True),
    Rule("bearer", "high", "ترويسة Bearer (تنقية فقط)",
         _r(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}"), scan=False),
)

RULE_IDS = tuple(r.id for r in RULES)
SCAN_RULES = tuple(r for r in RULES if r.scan)

# key=value بلا اقتباس (سجلات): يُخفى الجزء بعد الفاصل. تنقية فقط.
_KV_RE = _r(r"(?i)\b(password|passwd|secret|api[_-]?key|token|authorization)"
            r"(\s*[=:]\s*)([^\s,;&\"']{4,})")

# كلمات العناصر النائبة: لا تُعد سرًا في الفحص (التنقية تخفيها على أي حال)
_PLACEHOLDER_WORDS = ("example", "sample", "placeholder", "dummy", "fake", "changeme",
                      "your_", "your-", "yourkey", "redacted", "xxxx", "test_", "_test", "test-", "-test",
                      "mock", "notreal", "not_real", "insert", "replace")
_TEMPLATE_MARKS = ("${", "{{", "<", "%(", "$(")


def entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in (s.count(ch) for ch in set(s)))


def is_placeholder(value: str) -> bool:
    v = value.lower()
    if any(w in v for w in _PLACEHOLDER_WORDS) or any(m in value for m in _TEMPLATE_MARKS):
        return True
    body = re.sub(r"^[a-z]+_", "", v)
    if body and max(body.count(ch) for ch in set(body)) / len(body) > 0.5:
        return True    # ghp_aaaaaaaa… أو ********
    return False


@dataclass(frozen=True)
class Hit:
    rule: str
    severity: str
    start: int
    end: int
    value: str

    def fingerprint(self, path: str = "") -> str:
        """بصمة غير عكوسة: القاعدة + المسار + القيمة. لا تُحفظ القيمة أبدًا."""
        h = hashlib.sha256(f"{self.rule}\x00{path}\x00{self.value}".encode("utf-8", "replace"))
        return h.hexdigest()[:24]


def find(text: str, rules: Optional[Iterable[Rule]] = None, *,
         skip_placeholders: bool = True) -> List[Hit]:
    """كل الكشوف في نص (للفحص). المتداخل يُحسم للقاعدة الأولى في الكتالوج."""
    hits: List[Hit] = []
    taken: List[Tuple[int, int]] = []
    for rule in (SCAN_RULES if rules is None else rules):
        for m in rule.pattern.finditer(text):
            s, e = m.span(rule.group)
            val = m.group(rule.group)
            if any(s < te and ts < e for ts, te in taken):
                continue
            if rule.min_entropy and entropy(val) < rule.min_entropy:
                continue
            if len(val) < rule.scan_min_len:
                continue
            if rule.require_mixed and not (re.search(r"[0-9]", val) and re.search(r"[A-Za-z]", val)):
                continue
            if skip_placeholders and rule.placeholders and is_placeholder(val):
                continue
            taken.append((s, e))
            hits.append(Hit(rule.id, rule.severity, s, e, val))
    return sorted(hits, key=lambda h: h.start)


def redact(text: Any, limit: Optional[int] = None) -> str:
    """تنقية: كل القواعد + key=value. لا يُستثنى «نائب» — الإفراط أهون من التسرب."""
    s = str("" if text is None else text)
    for rule in RULES:
        if rule.group:
            s = rule.pattern.sub(lambda m, g=rule.group: m.group(0).replace(m.group(g), MASK), s)
        else:
            s = rule.pattern.sub(MASK, s)
    s = _KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{MASK}", s)
    return s[:limit] if limit is not None else s


def has_secret(text: Any) -> bool:
    s = str("" if text is None else text)
    return any(r.pattern.search(s) for r in RULES)
