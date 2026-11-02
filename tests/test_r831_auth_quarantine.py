# -*- coding: utf-8 -*-
"""R-831: عزل فشل مصادقة GCM في المخزن الصلب — رفض موثق مرة واحدة لكل سجل.

الخلفية: سجلات episodic مشفرة بمفتاح سيادة قديم (تغيّر المفتاح عبر بيئة
سابقة) تُرفض بفشل مصادقة GCM في كل دورة قراءة — كان فيضان السجلات يعيد
نفس الخطأ عشرات المرات لكل سجل في كل دورة تشغيل (المجدد يقرأ الذاكرة كل
300ث). R-831 يحفظ سلوك fail-closed كما هو (السجل المرفوض لا يعود كبيانات
أبدًا) ويوثق الرفض مرة واحدة لكل سجل ثم يتخطاه بصمت.

هذه الاختبارات تثبت:
1. الرفض الأول يُسجَّل كخطأ GCM صريح (سلوك R-682 محفوظ).
2. المحاولات التالية لنفس السجل لا تكرر الخطأ (عزل) ولا تعيده كبيانات.
3. سجلات مختلفة يوثق كل منها مرة (لا تعميم عزل خاطئ).
4. مسح الحجر عند reset() يعيد التوثيق (السلوك الأصلي عند التهيئة).
"""
import base64
import hashlib
import json
import logging
from unittest.mock import MagicMock

import pytest


def _mock_core():
    core = MagicMock()
    core._last_hash = "a" * 64
    core.get_statistics.return_value = {"index": {"total_events": 3}}
    return core


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """مخزن صلب حقيقي معزول تحت tmp_path (نمط المشروع في test_return_none_lowrisk).

    threads.start_managed يُستبدل بخيط وهمي — لا خيوط خلفية في الاختبار.
    """
    import backend.memory.store as store_mod
    from backend.memory.store import SolidMemoryStore

    store_dir = tmp_path / "store"
    store_dir.mkdir(parents=True, exist_ok=True)
    file_map = {"index": store_dir / "index.json"}
    for kind in store_mod.MemoryKind:
        file_map[kind.value] = store_dir / f"{kind.value}.json"
    monkeypatch.setattr(store_mod, "FILE_MAP", file_map)
    monkeypatch.setattr(store_mod, "get_core", _mock_core)
    encoder = MagicMock()
    encoder.fingerprint = lambda p: hashlib.sha256(
        json.dumps(p, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:32]
    monkeypatch.setattr(store_mod, "get_encoder", lambda: encoder)
    monkeypatch.setattr(store_mod, "get_store", lambda: None)

    real_start_managed = store_mod.threads.start_managed

    def _no_threads(target, **kwargs):
        # لا خيوط خلفية داخل الاختبار — الإيقاف فوري
        class _Stopped:
            def stop(self):
                pass

            def join(self, *a, **k):
                pass

        return _Stopped()

    monkeypatch.setattr(store_mod.threads, "start_managed", _no_threads)
    try:
        yield SolidMemoryStore()
    finally:
        monkeypatch.setattr(store_mod.threads, "start_managed", real_start_managed)


def _tamper_first_episodic(store):
    """إفساد حمولة أول سجل episodic (محاكاة سجل بمفتاح قديم/تالف)."""
    items = list(store._data["episodic"].values())
    assert items, "لا يوجد سجل episodic لاختباره"
    item = items[0]
    env = json.loads(item.encrypted_payload)
    ct = bytearray(base64.b64decode(env["d"]))
    ct[0] ^= 0xFF  # إفساد بايت — فشل وسم GCM مضمون
    env["d"] = base64.b64encode(bytes(ct)).decode()
    item.encrypted_payload = json.dumps(env)
    return item.id


class TestR831AuthQuarantine:
    """عزل فشل المصادقة — رفض واحد موثق لكل سجل، لا فيضان."""

    def test_first_rejection_logged_once_then_silent(
        self, isolated_store, caplog
    ):
        """الرفض يوثق مرة واحدة لكل سجل — المحاولات التالية بلا تكرار."""
        store = isolated_store
        store.save("episodic", {"title": "حدث اختبار", "description": "وصف"}, importance=0.9, store_in_core=False)
        item_id = _tamper_first_episodic(store)
        encrypted = store._data["episodic"][item_id].encrypted_payload

        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            # المحاولة الأولى — يجب أن تُوثق كفشل مصادقة صريح
            p1 = store._decrypt_payload(encrypted, "episodic", item_id=item_id)
            # المحاولتان التاليتان لنفس السجل — عزل: بلا توثيق جديد
            p2 = store._decrypt_payload(encrypted, "episodic", item_id=item_id)
            p3 = store._decrypt_payload(encrypted, "episodic", item_id=item_id)

        # السلوك الأمني محفوظ: الثلاثة مرفوضة ولا تعود كبيانات
        for p in (p1, p2, p3):
            assert p.get("_error"), "السجل المرفوض يجب ألا يعود كبيانات أبدًا"
        # الرفض الأول موثق صراحة كفشل GCM (سلوك R-682)
        errors = [r for r in caplog.records
                  if "GCM authentication FAILED" in r.getMessage()]
        assert errors, "الرفض الأول يجب أن يوثق كفشل مصادقة GCM صريح"
        assert len(errors) == 1, (
            f"الرفض يوثق مرة واحدة لكل سجل (وُجد {len(errors)}) — "
            "المحاولات المعزولة لا تكرر الخطأ"
        )

    def test_distinct_records_logged_separately(
        self, isolated_store, caplog
    ):
        """سجلان تالفان — كل واحد يوثق رفضه مرة (لا تعميم العزل)."""
        store = isolated_store
        store.save("episodic", {"title": "أول"}, importance=0.9, store_in_core=False)
        store.save("episodic", {"title": "ثانٍ"}, importance=0.9, store_in_core=False)
        first = _tamper_first_episodic(store)
        # إفساد سجل ثانٍ مختلف
        items = [i for i in store._data["episodic"].values() if i.id != first]
        item2 = items[0]
        env = json.loads(item2.encrypted_payload)
        ct = bytearray(base64.b64decode(env["d"]))
        ct[0] ^= 0xFF
        env["d"] = base64.b64encode(bytes(ct)).decode()
        item2.encrypted_payload = json.dumps(env)

        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            for _ in range(3):
                store._decrypt_payload(
                    store._data["episodic"][first].encrypted_payload,
                    "episodic", item_id=first,
                )
            for _ in range(3):
                store._decrypt_payload(
                    item2.encrypted_payload, "episodic", item_id=item2.id,
                )

        errors = [r for r in caplog.records
                  if "GCM authentication FAILED" in r.getMessage()]
        assert len(errors) == 2, (
            f"سجلان تالفان = توثيقان (وُجد {len(errors)}) — "
            "كل سجل يوثق رفضه مرة واحدة"
        )

    def test_reset_clears_quarantine_and_relogs(
        self, isolated_store, caplog
    ):
        """reset() يمسح الحجر — السجل التالف يوثق رفضه من جديد."""
        store = isolated_store
        store.save("episodic", {"title": "حدث"}, importance=0.9, store_in_core=False)
        item_id = _tamper_first_episodic(store)
        store._save_kind("episodic")  # ثبات التشويه على القرص (نمط الإنتاج)

        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            store._decrypt_payload(
                store._data["episodic"][item_id].encrypted_payload,
                "episodic", item_id=item_id,
            )
        first_count = len([r for r in caplog.records
                           if "GCM authentication FAILED" in r.getMessage()])
        assert first_count == 1

        caplog.clear()
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            store.reset(preserve_data=True)
        # بعد التهيئة: إعادة المحاولة توثق الرفض مرة أخرى (السجل ما زال تالفًا)
        with caplog.at_level(logging.ERROR, logger="backend.memory.store"):
            store._decrypt_payload(
                store._data["episodic"][item_id].encrypted_payload,
                "episodic", item_id=item_id,
            )
        errors = [r for r in caplog.records
                  if "GCM authentication FAILED" in r.getMessage()]
        assert errors, "بعد reset يجب أن يوثق الرفض من جديد (مسح الحجر)"

    def test_quarantined_record_never_returns_as_data(self, isolated_store):
        """البوابة الأمنية: السجل المعزول مرفوض في كل مسارات القراءة."""
        store = isolated_store
        store.save("episodic", {"title": "حدث"}, importance=0.9, store_in_core=False)
        item_id = _tamper_first_episodic(store)

        # عبر query (بوابة البصمة فاشلة-مغلقة)
        results = store.query("episodic", search_text="حدث", limit=10)
        matched = [r for r in results
                   if isinstance(r, dict)
                   and r.get("_metadata", {}).get("id") == item_id]
        assert not matched, "السجل التالف لا يعود من query أبدًا"

        # عبر get مباشرة (مسار القراءة الفردية)
        payload = store.get("episodic", item_id)
        assert payload is None or payload.get("_error"), (
            "السجل التالف لا يعود من get كبيانات صالحة"
        )
