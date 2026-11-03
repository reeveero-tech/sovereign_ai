# CONNECTOR_GUIDE.md — دليل إضافة موصل جديد (R-840)

> الهدف: إضافة موصل لمنصة جديدة في **ملف واحد** دون لمس المحرك أو الأمان.

## الخطوات

### 1. عرّف الموصل — `backend/connector_system/connectors/<platform>_connector.py`

انسخ نمط `github_connector.py`. الموصل = تعريف ثابت (عقد) + معالجات:

```python
from .. import execution
from ..contract import ConnectorDefinition, Operation

BASE = "https://api.example.com"

def _call(material, http, method, url, **kw):
    headers = {}
    headers.update(material.headers)          # مادة الاعتماد — لا سر هنا
    r = http(method, url, headers=headers, **kw)
    exc = execution.classify_http(r.status_code)  # 401/429/5xx → سلوك المحرك
    if exc is not None:
        raise exc
    return r

def widget_list(material, inputs, http):       # معالج: (مادة، مدخلات، نقل)
    r = _call(material, http, "GET", f"{BASE}/widgets")
    return {"ok": True, "widgets": [w.get("id") for w in r.json()]}

def definition(version="1.0.0"):
    return ConnectorDefinition(
        id="example", name="Example", version=version,
        description="…", category="saas", platform_class="key_only",
        auth_types=["api_key", "oauth2_auth_code_pkce"],   # من المصفوفة
        operations={
            "widget_list": Operation("widget_list", "query",
                                      frozenset({"widget:read"}),
                                      "قراءة الودجات", inputs={}),
            "widget_create": Operation("widget_create", "execute",
                                        frozenset({"widget:write"}),
                                        idempotent=True,
                                        inputs={"name": "text"}),
            "test_connection": Operation("test_connection", "query",
                                         frozenset({"widget:read"}),
                                         "اختبار الاتصال", inputs={}),
        },
        handlers={"widget_list": widget_list,
                  "widget_create": widget_create,
                  "test_connection": widget_list},
        base_url=BASE)
```

### 2. سجّله — `backend/connector_system/registry.py`

أضف `example_connector.definition()` إلى قائمة التسجيل الافتراضية في
`Registry.__init__`.

### 3. قواعد ملزمة

| القاعدة | السبب |
|---|---|
| النطاقات مفصولة قراءة/كتابة لكل عملية (`widget:read` لا `*`) | أقل صلاحية — اختبار ١٨ يرفض الكتابة بقراءة |
| `kind="execute"` لكل كتابة + `idempotent=True` حيث يسمح المزود | منع التكرار (معيار ١٦) |
| لا سر في المعالج — `material.headers` فقط | لا تسريب (معيار ١٩) |
| `classify_http` لكل رد | 401→تجديد واحد، 429/5xx→backoff وقاطع |
| `test_connection` إلزامية | المعالج يختبرها بعد كل إعداد |
| أنواع المصادقة من المصفوفة الرسمية فقط | لا نظام موازٍ |

### 4. اختبر — `backend/tests/test_connector_system.py`

أضف اختبارًا على نمط الموجودين: سجل موصل مزيف + نقل وهمي + تأكيد النطاقات.
للاختبار الحي: علّم الاختبار `@pytest.mark.operational` وخذ السر من البيئة
حصرًا (لا سر في الكود أبدًا).

### 5. وثّق (قاعدة الدفعة الذرية)

نفس الالتزام: كود + اختبارات + `PROJECT_STATE.md` + `CHANGELOG.md` +
الخارطة النشطة في نفس الالتزام.

## الموصل العام — بلا كود أصلًا

أي API بمواصفة OpenAPI يعمل دون كتابة موصل:
`generic_openapi.definition_from_spec(connector_id, spec)` يستنتج العمليات
من المسارات والأفعال (GET→query، الباقي→execute) ويستنتج نوع المصادقة من
`securitySchemes`. دورة حياته تبدأ `preview`.
