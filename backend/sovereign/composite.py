# backend/sovereign/composite.py
# الدرجة المُركّبة (Composite) — البوابة 3 (R-671)
#
# المبدأ (من المالك):
# "(B) الدرجة المُركّبة — اختيارية. إذا أردت أن تُنتج رقماً واحداً،
#  اكتب الصيغة الرياضية صريحة."
#
# هذا الملف يُعرّف الصيغة الرياضية الصريحة للدرجة المُركّبة.
# كل مؤشر أولي من primitives.py يُستخدم بوزن صريح.
#
# ⚠️ تحذير من المالك:
# "الأرقام التي تنتجها نفس الدالة التي تتحقق منها ليست درجة — هي مرآة."
# هذا الملف لا يُستخدم للتحقق. هو رقم إحصائي اختياري فقط.

from typing import Dict

from backend.sovereign.primitives import Primitives


# الصيغة الرياضية الصريحة (كل مؤشر أولي بوزن):
#
# composite = (
#     w1 * (ledger_events_signed / ledger_events_total)      # نسبة الأحداث الموقّعة
#   + w2 * (anchors_verified / anchors_total)               # نسبة المراسي المُتحقّقة
#   + w3 * (keys_with_state / keys_total)                   # نسبة المفاتيح ذات الحالة الصريحة
#   + w4 * (1 if mocks_outside_tests == 0 else 0)           # لا mocks في الإنتاج
#   + w5 * (1 if files_imported > 0 else 0)                 # لا وحدات يتيمة
#   + w6 * (tests_passing_count / tests_total)              # نسبة الاختبارات الناجحة
# ) * (1 if mocks_outside_tests_count == 0 else 0) * 100    # عامل ضارب (R-680)
#
# حيث:
# w1 = 0.15 (الأحداث الموقّعة — 15%)
# w2 = 0.15 (المراسي المُتحقّقة — 15%)
# w3 = 0.10 (المفاتيح ذات الحالة — 10%)
# w4 = 0.10 (لا mocks — 10%)
# w5 = 0.10 (لا يتيمة — 10%)
# w6 = 0.40 (الاختبارات الناجحة — 40%)  ← R-680: يُحسب من تشغيل pytest، لا من الملفات
#
# عامل الضارب: إذا mocks_outside_tests_count > 0 → الدرجة = 0 (R-680)

COMPOSITE_WEIGHTS = {
    "ledger_signed_ratio": 0.15,
    "anchors_verified_ratio": 0.15,
    "keys_state_ratio": 0.10,
    "no_mocks_in_production": 0.10,
    "no_orphan_modules": 0.10,
    "tests_passing_count_ratio": 0.40,
}


class Composite:
    """الدرجة المُركّبة — صيغة رياضية صريحة من المؤشرات الأولية.

    ⚠️ هذا الرقم ليس تحققًا. هو إحصائية اختيارية.
    التحقيق الحقيقي يكون من المؤشرات الأولية (primitives.py)
    التي يمكن لأي طرف ثالث حسابها من الملفات.
    """

    def __init__(self, primitives: Primitives):
        self.primitives = primitives
        self._weights = COMPOSITE_WEIGHTS

    def compute(self) -> Dict:
        """يحسب الدرجة المُركّبة بـ الصيغة الصريحة أعلاه.

        يُعيد قاموس يحتوي:
        - composite_score: الرقم المُركّب (0-100)
        - formula: الصيغة الرياضية المستخدمة (نص)
        - components: كل مؤشر أولي و وزنه و مساهمته
        - warning: تحذير أن هذا ليس تحققًا
        """
        p = self.primitives.compute_all()

        # المكونات
        ledger_ratio = p["ledger_events_stats"]["ratio"]
        anchors_ratio = p["anchors_stats"]["ratio"]
        keys_ratio = p["keys_stats"]["ratio"]
        mocks_count = p["mocks_outside_tests_count"]
        no_mocks = 1.0 if mocks_count == 0 else 0.0
        files_imported = p["files_imported_count"]
        no_orphans = 1.0 if files_imported > 0 else 0.0

        # R-680: tests_passing_count_ratio — يُحسب من تشغيل pytest، لا من الملفات.
        # المشكلة الأصلية: tests_passing_count كان دائماً -1 (تشغيلي، لا يُحسب هنا).
        # الحل: نقبل من المستخدم/السياق قيمة pytest الخارجية، أو نستخدم 0 (غير محسوب).
        # هذا يمنع المقياس من إعطاء 100 بسهولة عندما تفشل الاختبارات.
        # تُمرر قيمة pytest عبر Composite(primitives, tests_passing=..., tests_total=...)
        # أو عبر self.set_tests_passing(...) قبل compute().
        tests_passing = getattr(self, "tests_passing", 0)
        tests_total = getattr(self, "tests_total", 0)
        if tests_total > 0 and tests_passing >= 0:
            tests_passing_ratio = tests_passing / tests_total
        else:
            tests_passing_ratio = 0.0  # غير محسوب → 0 (لا يمنح نقاطاً مجاناً)

        # R-680: عامل الضارب — إذا وُجد mock في الإنتاج → الدرجة = 0
        hard_kill_factor = (1 if mocks_count == 0 else 0)

        # الصيغة الصريحة
        composite = (
            self._weights["ledger_signed_ratio"] * ledger_ratio
            + self._weights["anchors_verified_ratio"] * anchors_ratio
            + self._weights["keys_state_ratio"] * keys_ratio
            + self._weights["no_mocks_in_production"] * no_mocks
            + self._weights["no_orphan_modules"] * no_orphans
            + self._weights["tests_passing_count_ratio"] * tests_passing_ratio
        ) * hard_kill_factor * 100

        # التفصيل
        components = {
            "ledger_signed_ratio": {
                "value": ledger_ratio,
                "weight": self._weights["ledger_signed_ratio"],
                "contribution": self._weights["ledger_signed_ratio"] * ledger_ratio * 100,
            },
            "anchors_verified_ratio": {
                "value": anchors_ratio,
                "weight": self._weights["anchors_verified_ratio"],
                "contribution": self._weights["anchors_verified_ratio"] * anchors_ratio * 100,
            },
            "keys_state_ratio": {
                "value": keys_ratio,
                "weight": self._weights["keys_state_ratio"],
                "contribution": self._weights["keys_state_ratio"] * keys_ratio * 100,
            },
            "no_mocks_in_production": {
                "value": no_mocks,
                "weight": self._weights["no_mocks_in_production"],
                "contribution": self._weights["no_mocks_in_production"] * no_mocks * 100,
            },
            "no_orphan_modules": {
                "value": no_orphans,
                "weight": self._weights["no_orphan_modules"],
                "contribution": self._weights["no_orphan_modules"] * no_orphans * 100,
            },
            "tests_passing_count_ratio": {
                "value": tests_passing_ratio,
                "weight": self._weights["tests_passing_count_ratio"],
                "contribution": self._weights["tests_passing_count_ratio"] * tests_passing_ratio * 100,
            },
            "hard_kill_factor": {
                "value": hard_kill_factor,
                "weight": "(R-680) عامل ضارب — أي mock في الإنتاج = 0",
                "contribution": None,
            },
        }

        formula = (
            f"composite = ("
            f"{self._weights['ledger_signed_ratio']} * {ledger_ratio:.4f} "
            f"+ {self._weights['anchors_verified_ratio']} * {anchors_ratio:.4f} "
            f"+ {self._weights['keys_state_ratio']} * {keys_ratio:.4f} "
            f"+ {self._weights['no_mocks_in_production']} * {no_mocks} "
            f"+ {self._weights['no_orphan_modules']} * {no_orphans} "
            f"+ {self._weights['tests_passing_count_ratio']} * {tests_passing_ratio:.4f}"
            f") * {hard_kill_factor} * 100 = {composite:.2f}"
        )

        return {
            "composite_score": round(composite, 2),
            "formula": formula,
            "components": components,
            "primitives": p,
            "warning": (
                "⚠️ هذا الرقم ليس تحققًا. هو إحصائية اختيارية. "
                "التحقق الحقيقي من المؤشرات الأولية "
                "(backend/sovereign/primitives.py) — "
                "كل واحد قابل للتحقق الخارجي من طرف ثالث. "
                "⚠️ قابل للجدل — composite قد لا يعكس كل جودة المشروع "
                "(R-680: يُدرج tests_passing_count_ratio و عامل ضارب mocks_outside_tests_count)."
            ),
            "disputed": True,
        }
