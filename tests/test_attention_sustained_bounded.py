"""R-778 (ROADMAP_V6 ٦.١.٢) — تخصيصات الانتباه المستدام لا تتراكم بلا حد.

الدليل (2026-10-26، محرك انتباه حي محليًا على سجل 46,511): التخصيصات المستدامة 159→321→401
في 40ث وكلها لهدف واحد، والأقدم من 30ث تزيد ~80/20ث (أولوية 6)، بينما البؤرة والموزع ثابتان.
السبب: كل دورة (0.5ث) تنشئ تخصيصًا جديدًا للهدف نفسه، و`update_sustained` يجدد `last_updated`
لكل مستدام أولويته > 5 فلا يبلغ حد الثلاثين ثانية أبدًا ⇒ نسخ مكررة خالدة.
"""
from consciousness import attention_engine as ae


class _Core:
    def append_event(self, *a, **k):
        return {}


def _engine():
    e = ae.AttentionEngine.__new__(ae.AttentionEngine)
    e.allocations = {}
    e.spotlight = {}
    e.snapshots = []
    e.sustained_attention_items = {}
    e.total_attention_resources = 100.0
    e.used_resources = 0.0
    e.core = _Core()
    e.collect_attention_items = lambda: []
    e.check_preemption = lambda items: []
    e.update_spotlight = lambda allocs: []
    return e


def _alloc(now, target, kind, prio=6):
    return ae.AttentionAllocation(
        id=f"alloc_{now}_{target}_{kind}", target=target, attention_type=kind,
        resource_level=0.01, priority=prio, reason="t", duration=3.0,
        started_at=now, last_updated=now, meta={})


def test_superseded_sustained_allocations_expire(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(ae.time, "time", lambda: clock[0])
    e = _engine()
    e.allocate_resources = lambda items: [
        _alloc(clock[0], "T", ae.ATTENTION_TYPE_SUSTAINED),
        _alloc(clock[0], "D", ae.ATTENTION_TYPE_DIVIDED),
    ]
    for _ in range(400):  # 200ث بدورات 0.5ث
        e.update_attention()
        clock[0] += 0.5
    sustained = [a for a in e.allocations.values() if a.attention_type == ae.ATTENTION_TYPE_SUSTAINED]
    divided = [a for a in e.allocations.values() if a.attention_type == ae.ATTENTION_TYPE_DIVIDED]
    # نافذة الثلاثين ثانية كما هي (~60 دورة) — لا تراكم بعدها
    assert len(divided) <= 61
    assert len(sustained) <= 61, f"{len(sustained)} تخصيصًا مستدامًا لهدف واحد بعد 200ث"


def test_unsuperseded_sustained_allocation_survives(monkeypatch):
    """الانتباه المستدام الحقيقي (لا تخصيص أحدث لهدفه) يبقى ممدَّدًا — السلوك المقصود."""
    clock = [1000.0]
    monkeypatch.setattr(ae.time, "time", lambda: clock[0])
    e = _engine()
    e.allocate_resources = lambda items: []
    a = _alloc(clock[0], "LONE", ae.ATTENTION_TYPE_SUSTAINED)
    e.allocations[a.id] = a
    for _ in range(200):
        e.update_attention()
        clock[0] += 0.5
    assert a.id in e.allocations
