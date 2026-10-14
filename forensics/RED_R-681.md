# RED_<issue>.md — Reproducibility artifacts (R-681)

**التاريخ:** 2026-10-15
**المرجع:** أمر التسليم — المرحلة 1 [1.3] + البند المفتوح 7
**القاعدة:** كل إصلاح سلوكي يحتاج توثيق RED (الحالة قبل الإصلاح) كـ reproducibility artifact.

---

## RED-1: 3 test failures due to environment drift (fastapi 0.143.1 / httpx 0.28.1)

### كيفية إعادة إنتاج الحالة قبل الإصلاح

```bash
# 1) التثبت من إصدارات البيئة
python -c "import fastapi, httpx, starlette; print(fastapi.__version__, httpx.__version__, starlette.__version__)"
# الناتج (قبل الإصلاح): 0.143.1 0.28.1 1.8.0

# 2) التشغيل
cd sovereign_ai
python -m pytest tests/ backend/tests/ -q
```

### النتيجة قبل الإصلاح (RED)

```
3 failed, 281 passed, 10 skipped
```

الفاشلان الثلاثة:

| # | الاختبار | السبب الجذري |
|---|---|---|
| 1 | `tests/test_safety_layer.py::test_app_registers_security_endpoints` | fastapi ≥0.14x wraps included routers in `_IncludedRouter` which lacks `.path` → `route.path` iteration raises `AttributeError` |
| 2 | `tests/test_safety_layer.py::test_app_registers_nexus_api_endpoints` | نفس السبب |
| 3 | `tests/test_gate1_actual_auth.py::TestActualAuthentication::test_http_codes_only_no_key_material` | httpx 0.28.1 logs under logger name `httpx2` instead of `httpx` → test silenced wrong logger → positive control fails (key leaked in logs) |

### الدليل التشخيصي

```bash
python - <<'EOF'
import fastapi.routing as r
print(r._IncludedRouter.__mro__)
# (<class 'fastapi.routing._IncludedRouter'>, <class 'starlette.routing.BaseRoute'>, <class 'object'>)
# _IncludedRouter inherits BaseRoute which has NO .path attribute.

import logging
import httpx._client as c
# httpx 0.28+ uses logger name 'httpx2' (verified by grep in httpx source)
EOF
```

### الإصلاح (GREEN)

- `tests/test_safety_layer.py`: أُضيف `_iter_app_routes()` helper يفك `_IncludedRouter` (recursive unwrap via `original_router`).
- `tests/test_gate1_actual_auth.py`: أُسكِت كلا الاسمين `httpx` و `httpx2`.
- `tests/test_gate1_header_auth.py`: فُعّل كلا الاسمين لالتقاط السجلات (positive control).

### النتيجة بعد الإصلاح (GREEN)

```bash
python -m pytest tests/ backend/tests/ -q --junitxml=/tmp/full-suite.xml
# 287 passed, 7 skipped in 145.51s (0:02:25)
```

**الفرق:** 3 failed → 0 failed. 281 passed → 287 passed.

---

## RED-2: CI pipeline did not run backend/tests/ or generate JUnit XML

### الحالة قبل الإصلاح (RED)

`.github/workflows/ci.yml` (before R-681):
```yaml
- name: Run test suite
  run: |
    python -m pytest tests/ -v
```
- Runs only `tests/` (NOT `backend/tests/`)
- Does NOT generate JUnit XML
- Does NOT embed git SHA
- Does NOT fail explicitly on failure (implicit via pytest exit code)

### الإصلاح (GREEN)

New CI workflow:
- Runs `python -m pytest tests/ backend/tests/ -v --junitxml=forensics/pytest_results.xml --junit-prefix="R-681-ci-sha-${SHA}"`
- Generates ephemeral `data/key.secret` before tests (root fix for skips)
- Uploads JUnit XML as artifact
- Embeds git SHA in JUnit XML root attributes
- Fails explicitly on any failure

---

## RED-3: Scanner silently skipped unreadable/unparsable files

### الحالة قبل الإصلاح (RED)

`backend/tests/invariants/test_no_silent_exceptions.py` (lines ~185-195):
```python
try:
    src = p.read_text(encoding="utf-8")
except Exception:
    continue  # ← SILENT — no warning
```

### الإصلاح (GREEN)

R-681 (open item 4): Added `warnings.warn()` for both unreadable and SyntaxError cases. The scan result is unchanged (0 violations) but now emits visible warnings for skipped files.

---

## RED-4: awareness.py:561 was a placeholder without explicit TODO

### الحالة قبل الإصلاح (RED)

```python
# TOLERATED: placeholder for future condition check — no action needed (R-680)
if self.current_moment:
    pass
```

No `# TODO: placeholder, tracked in issue` marker.

### الإصلاح (GREEN)

R-681 (open item 3): Added explicit TODO tag. Real implementation deferred — tracked as issue (see forensics/RETURN_NONE_AUDIT.md for related follow-up).

---

**إعادة إنتاج كل الأرقام بأمر واحد:**

```bash
cd sovereign_ai && python -m pytest tests/ backend/tests/ -q --junitxml=/tmp/final.xml
```

Expected: `287 passed, 7 skipped, 0 failed`.
