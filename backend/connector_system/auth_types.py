# -*- coding: utf-8 -*-
"""R-840: مصفوفة أنواع المصادقة — كل نوع توكن كائن واحد بسياسات موحدة.

كل نوع له: مخاطرة (safe/caution/deprecated)، تحذير صريح للأنواع الخطرة،
حقول معالج الإعداد في الواجهة، سياسة تخزين وتدوير، وسلوك فشل.
القاعدة: لا نظامان منفصلان — OAuth وAPI Key وغيرهما كلها كائن اعتماد واحد.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AuthType:
    id: str
    family: str                     # oauth|token|key|cert|signature|dynamic|special
    label: str
    risk: str                       # safe|caution|deprecated
    warning: Optional[str] = None
    wizard_fields: tuple = ()      # حقول معالج الإعداد (اسم، نوع)
    storage: str = "vault_encrypted"
    rotation: str = "manual"
    refresh_supported: bool = False
    failure_behavior: str = ""

    def public(self) -> Dict[str, object]:
        return {
            "id": self.id, "family": self.family, "label": self.label,
            "risk": self.risk, "warning": self.warning,
            "wizard_fields": [list(f) for f in self.wizard_fields],
            "storage": self.storage, "rotation": self.rotation,
            "refresh_supported": self.refresh_supported,
            "failure_behavior": self.failure_behavior,
        }


_W = {
    "implicit": "مهجور ومعرض لتسريب التوكن في المتصفح — لا يُستخدم افتراضيًا.",
    "ropc": "مهجور — كلمة المرور تمر عبر العميل. للأنظمة القديمة فقط.",
    "query_token": "خطر تسريب في السجلات والروابط — استخدمه كحل أخير فقط.",
    "cookies": "جلسات هشة وقابلة للاختطاف — خيار أخير مع تحذير.",
    "basic": "بيانات اعتماد دائمة بلا انتهاء — استخدمها فقط عبر HTTPS.",
}

AUTH_TYPES: Dict[str, AuthType] = {a.id: a for a in [
    # --- عائلة OAuth
    AuthType("oauth2_auth_code_pkce", "oauth", "Authorization Code + PKCE", "safe",
             wizard_fields=(("redirect_uri", "url"), ("client_id", "text"),
                            ("client_secret", "secret")),
             rotation="refresh_token", refresh_supported=True,
             failure_behavior="401 → محاولة تجديد واحدة → إعادة أو حالة expired"),
    AuthType("oauth2_auth_code", "oauth", "Authorization Code (بدون PKCE)", "caution",
             warning="للمزودين القدامى فقط — PKCE هو المسار المفضل.",
             wizard_fields=(("redirect_uri", "url"), ("client_id", "text"),
                            ("client_secret", "secret")),
             rotation="refresh_token", refresh_supported=True,
             failure_behavior="401 → تجديد واحد أو expired"),
    AuthType("client_credentials", "oauth", "Client Credentials (خدمة-خدمة)", "safe",
             wizard_fields=(("client_id", "text"), ("client_secret", "secret")),
             rotation="automatic", refresh_supported=True,
             failure_behavior="401 → توكن جديد أو error"),
    AuthType("device_code", "oauth", "Device Authorization Grant", "safe",
             wizard_fields=(("client_id", "text"),),
             failure_behavior="انتهاء صلاحية الرمز → إعادة بدء التدفق"),
    AuthType("implicit", "oauth", "Implicit (مهجور)", "deprecated",
             warning=_W["implicit"], wizard_fields=(("client_id", "text"),),
             failure_behavior="توكن منتهي → إعادة تفويض يدوي"),
    AuthType("ropc", "oauth", "Resource Owner Password (مهجور)", "deprecated",
             warning=_W["ropc"],
             wizard_fields=(("username", "text"), ("password", "secret")),
             failure_behavior="401 → إعادة إدخال"),
    AuthType("oauth1a", "oauth", "OAuth 1.0a (توكن + سر)", "caution",
             wizard_fields=(("consumer_key", "text"), ("consumer_secret", "secret"),
                            ("token", "text"), ("token_secret", "secret")),
             failure_behavior="401 → إعادة تفويض"),
    AuthType("refresh_token", "oauth", "Refresh Token (تجديد صامت)", "safe",
             rotation="automatic", refresh_supported=True,
             failure_behavior="فشل التجديد → expired + إشعار"),
    AuthType("obo", "oauth", "On-Behalf-Of / Delegated", "safe",
             wizard_fields=(("client_id", "text"), ("client_secret", "secret")),
             rotation="automatic", refresh_supported=True,
             failure_behavior="401 → تجديد بالنيابة أو expired"),
    AuthType("app_installation", "oauth", "App Installation Token (JWT → مؤقت)", "safe",
             wizard_fields=(("app_id", "text"), ("private_key", "secret")),
             rotation="automatic", refresh_supported=True,
             failure_behavior="انتهاء installation token → JWT جديد"),
    # --- التوكنات الشخصية والثابتة
    AuthType("pat", "token", "Personal Access Token", "safe",
             wizard_fields=(("token", "secret"),),
             failure_behavior="401 → منتهٍ/مبطل — إعادة إعداد"),
    AuthType("bot_token", "token", "Bot Token", "safe",
             wizard_fields=(("token", "secret"),),
             failure_behavior="401 → إعادة توليد من المزود"),
    AuthType("ssh_key", "token", "Deploy Key / SSH Key", "caution",
             warning="مفتاح خاص — تأكد أنه للقراءة فقط إن أمكن.",
             wizard_fields=(("private_key", "secret"),),
             failure_behavior="رفض المفتاح → إعادة رفع"),
    AuthType("app_password", "token", "App Password", "caution",
             warning="بديل حين لا يدعم المزود OAuth — أقل أمانًا.",
             wizard_fields=(("username", "text"), ("app_password", "secret")),
             failure_behavior="401 → إعادة إعداد"),
    AuthType("connection_string", "token", "Connection String", "caution",
             warning="يحوي كل البيانات في سطر واحد — لا يسجل أبدًا.",
             wizard_fields=(("connection_string", "secret"),),
             failure_behavior="فشل اتصال → إعادة إدخال"),
    # --- المفاتيح
    AuthType("api_key", "key", "API Key", "safe",
             wizard_fields=(("api_key", "secret"), ("in", "select:header|query")),
             failure_behavior="401/403 → مفتاح غير صالح"),
    AuthType("api_key_secret", "key", "API Key + Secret", "safe",
             wizard_fields=(("api_key", "text"), ("api_secret", "secret")),
             failure_behavior="توقيع خاطئ → إعادة إدخال"),
    AuthType("service_account", "key", "Service Account Key (JSON)", "safe",
             wizard_fields=(("service_account_json", "file"),),
             rotation="manual", failure_behavior="توكن غير صالح → إعادة رفع"),
    AuthType("presigned_url", "key", "Presigned / Signed URL", "caution",
             warning="تنتهي صلاحيتها ويصعب تدويرها — مؤقتة بطبيعتها.",
             wizard_fields=(("url", "url"),), failure_behavior="403 → إعادة توليد"),
    AuthType("webhook_url", "key", "Webhook URL بسر مضمّن", "caution",
             warning="السر في الرابط نفسه — لا يُسجل ولا يُعرض.",
             wizard_fields=(("webhook_url", "url"),),
             failure_behavior="4xx → رابط مُبطل"),
    # --- الشهادات والمصادقة الثنائية
    AuthType("mtls", "cert", "mTLS (Client Certificate)", "safe",
             wizard_fields=(("certificate", "textarea"), ("private_key", "secret")),
             failure_behavior="فشل المصافحة → شهادة غير مطابقة (تُعرض بوضوح)"),
    AuthType("x509", "cert", "X.509 Certificate", "safe",
             wizard_fields=(("certificate", "textarea"),),
             failure_behavior="انتهاء الشهادة → إعادة إصدار"),
    AuthType("basic", "cert", "Basic Auth", "caution", warning=_W["basic"],
             wizard_fields=(("username", "text"), ("password", "secret")),
             failure_behavior="401 → بيانات غير صحيحة"),
    AuthType("jwt_signed", "cert", "JWT موقّع (JWS)", "safe",
             wizard_fields=(("private_key", "secret"), ("secret", "secret")),
             rotation="automatic", refresh_supported=True,
             failure_behavior="توقيع مرفوض → مفتاح خاطئ"),
    AuthType("jwt_bearer_grant", "cert", "JWT Bearer Grant (RFC 7523)", "safe",
             wizard_fields=(("private_key", "secret"),),
             rotation="automatic", refresh_supported=True,
             failure_behavior="assertion مرفوض → إعادة توليد"),
    AuthType("saml", "cert", "SAML Assertion", "caution",
             wizard_fields=(("idp_metadata", "textarea"),),
             failure_behavior="assertion منتهي → تجديد IdP"),
    AuthType("kerberos", "cert", "Kerberos", "caution",
             warning="بيئات داخلية فقط — يتطلب KDC موثوقًا.",
             wizard_fields=(("principal", "text"), ("keytab", "secret")),
             failure_behavior="TGT منتهي → kinit"),
    # --- التوقيع والتحقق
    AuthType("hmac", "signature", "HMAC Signature", "safe",
             wizard_fields=(("shared_secret", "secret"),),
             failure_behavior="توقيع خاطئ → سر غير صالح"),
    AuthType("signed_request", "signature", "Shared Secret + Timestamp + Nonce", "safe",
             wizard_fields=(("shared_secret", "secret"),),
             failure_behavior="نافذة زمنية منتهية → رفض"),
    # --- المؤقتة والديناميكية
    AuthType("sts", "dynamic", "STS / Session Token مؤقت", "safe",
             rotation="automatic", refresh_supported=True,
             failure_behavior="انتهاء الصلاحية يعيد الحالة expired ويطلب التجديد"),
    AuthType("one_time", "dynamic", "One-Time Token", "caution",
             warning="استخدام واحد — لا يعاد استخدامه.",
             wizard_fields=(("token", "secret"),),
             failure_behavior="مستهلك → إعادة توليد"),
    # --- أنماط خاصة
    AuthType("cookies_session", "special", "Cookies / Session", "deprecated",
             warning=_W["cookies"], wizard_fields=(("cookie_value", "secret"),),
             failure_behavior="جلسة منتهية → إعادة دخول"),
    AuthType("header_injection", "special", "Header Injection (توكن مخصص)", "safe",
             wizard_fields=(("header_name", "text"), ("header_value", "secret")),
             failure_behavior="401 → قيمة غير صالحة"),
    AuthType("query_token", "special", "Query Parameter Token", "deprecated",
             warning=_W["query_token"],
             wizard_fields=(("param_name", "text"), ("token", "secret")),
             failure_behavior="401 → إعادة إدخال"),
]}


def auth_type(auth_type_id: str) -> AuthType:
    try:
        return AUTH_TYPES[auth_type_id]
    except KeyError:
        raise ValueError(f"نوع مصادقة غير معروف: {auth_type_id}")


def matrix() -> List[Dict[str, object]]:
    """المصفوفة الكاملة للواجهة والتوثيق."""
    return [a.public() for a in AUTH_TYPES.values()]
