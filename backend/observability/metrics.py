# -*- coding: utf-8 -*-
"""R-846: سجل مقاييس داخل العملية بصيغة Prometheus النصية (بلا اعتماد خارجي).

- ثلاثة أنواع: Counter وGauge وHistogram بدلاء ثابتة.
- **سقف السلاسل**: لكل مقياس ``MAX_SERIES`` سلسلة. ما زاد يُجمع في سلسلة
  واحدة قيم وسومها ``__overflow__`` ويُعدّ في ``obs_series_overflow_total``،
  فلا ينفجر الاستهلاك من مسح أو قيم غير متوقعة.
- **الجامعون**: دوال تُستدعى عند القراءة (عمق الطابور، تسليمات الإشعارات...).
  الجامع المعطوب يُعدّ في ``obs_collector_errors_total`` ولا يكسر القراءة.
- لا قيمة وسم تحمل سرًا: قيم الوسوم تُنقّى وتُقص إلى 120 حرفًا.
"""
from __future__ import annotations

import logging
import math
import re
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .redact import redact

_log = logging.getLogger("observability.metrics")

MAX_SERIES = 200
OVERFLOW = "__overflow__"
DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
_NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# جامع: يعيد [(اسم، نوع، وصف، وسوم، قيمة)]
Sample = Tuple[str, str, str, Dict[str, str], float]


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def _fmt(v: float) -> str:
    if math.isinf(v):
        return "+Inf" if v > 0 else "-Inf"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(float(v))


def _labels_str(names: Sequence[str], values: Sequence[str], extra: str = "") -> str:
    parts = [f'{n}="{_esc(v)}"' for n, v in zip(names, values)]
    if extra:
        parts.append(extra)
    return "{" + ",".join(parts) + "}" if parts else ""


class _Metric:
    kind = ""

    def __init__(self, registry: "Registry", name: str, help_: str,
                 labelnames: Sequence[str] = ()):
        if not _NAME_RE.match(name):
            raise ValueError(f"اسم مقياس غير صالح: {name}")
        for ln in labelnames:
            if not _LABEL_RE.match(ln) or ln == "le":
                raise ValueError(f"اسم وسم غير صالح: {ln}")
        self.registry, self.name, self.help = registry, name, help_
        self.labelnames = tuple(labelnames)
        self._series: Dict[Tuple[str, ...], Any] = {}
        self._lock = threading.Lock()

    def _key(self, labels: Optional[Dict[str, Any]]) -> Tuple[str, ...]:
        labels = labels or {}
        if set(labels) != set(self.labelnames):
            raise ValueError(f"{self.name}: الوسوم المتوقعة {self.labelnames} لا {tuple(labels)}")
        key = tuple(redact(labels[n])[:120] for n in self.labelnames)
        if key not in self._series and len(self._series) >= MAX_SERIES:
            self.registry._overflow(self.name)
            return tuple(OVERFLOW for _ in self.labelnames)
        return key

    def series_count(self) -> int:
        with self._lock:
            return len(self._series)


class Counter(_Metric):
    kind = "counter"

    def inc(self, labels: Optional[Dict[str, Any]] = None, value: float = 1.0) -> None:
        if value < 0:
            raise ValueError("العداد لا ينقص")
        with self._lock:
            k = self._key(labels)
            self._series[k] = self._series.get(k, 0.0) + value

    def value(self, labels: Optional[Dict[str, Any]] = None) -> float:
        with self._lock:
            return self._series.get(tuple(str((labels or {})[n]) for n in self.labelnames), 0.0)

    def render(self) -> List[str]:
        with self._lock:
            return [f"{self.name}{_labels_str(self.labelnames, k)} {_fmt(v)}"
                    for k, v in sorted(self._series.items())]


class Gauge(Counter):
    kind = "gauge"

    def set(self, labels: Optional[Dict[str, Any]] = None, value: float = 0.0) -> None:
        with self._lock:
            self._series[self._key(labels)] = float(value)

    def inc(self, labels: Optional[Dict[str, Any]] = None, value: float = 1.0) -> None:
        with self._lock:
            k = self._key(labels)
            self._series[k] = self._series.get(k, 0.0) + value


class Histogram(_Metric):
    kind = "histogram"

    def __init__(self, registry, name, help_, labelnames=(), buckets=DEFAULT_BUCKETS):
        super().__init__(registry, name, help_, labelnames)
        b = sorted(float(x) for x in buckets)
        if not b or b != sorted(set(b)):
            raise ValueError("دلاء غير صالحة")
        self.buckets = tuple(b)

    def observe(self, labels: Optional[Dict[str, Any]] = None, value: float = 0.0) -> None:
        with self._lock:
            k = self._key(labels)
            s = self._series.get(k)
            if s is None:
                s = self._series[k] = {"counts": [0] * len(self.buckets), "sum": 0.0, "count": 0}
            for i, ub in enumerate(self.buckets):
                if value <= ub:
                    s["counts"][i] += 1
            s["sum"] += value
            s["count"] += 1

    def render(self) -> List[str]:
        out = []
        with self._lock:
            for k, s in sorted(self._series.items()):
                for ub, c in zip(self.buckets, s["counts"]):
                    le = 'le="' + _fmt(ub) + '"'
                    out.append(f"{self.name}_bucket{_labels_str(self.labelnames, k, le)} {c}")
                inf = 'le="+Inf"'
                out.append(f"{self.name}_bucket{_labels_str(self.labelnames, k, inf)} {s['count']}")
                out.append(f"{self.name}_sum{_labels_str(self.labelnames, k)} {_fmt(s['sum'])}")
                out.append(f"{self.name}_count{_labels_str(self.labelnames, k)} {s['count']}")
        return out


class Registry:
    def __init__(self):
        self._metrics: Dict[str, _Metric] = {}
        self._collectors: List[Tuple[str, Callable[[], Iterable[Sample]]]] = []
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.overflow = self.counter("obs_series_overflow_total",
                                     "سلاسل رُفضت لتجاوز سقف السلاسل", ["metric"])
        self.collector_errors = self.counter("obs_collector_errors_total",
                                             "جامعو مقاييس فشلوا عند القراءة", ["collector"])

    def _get_or_make(self, cls, name, help_, labelnames, **kw):
        with self._lock:
            m = self._metrics.get(name)
            if m is not None:
                if type(m) is not cls or m.labelnames != tuple(labelnames):
                    raise ValueError(f"المقياس {name} مسجل بنوع أو وسوم أخرى")
                return m
            m = cls(self, name, help_, labelnames, **kw)
            self._metrics[name] = m
            return m

    def counter(self, name, help_, labelnames=()) -> Counter:
        return self._get_or_make(Counter, name, help_, labelnames)

    def gauge(self, name, help_, labelnames=()) -> Gauge:
        return self._get_or_make(Gauge, name, help_, labelnames)

    def histogram(self, name, help_, labelnames=(), buckets=DEFAULT_BUCKETS) -> Histogram:
        return self._get_or_make(Histogram, name, help_, labelnames, buckets=buckets)

    def _overflow(self, metric: str) -> None:
        # بلا قفل المقياس الأصلي (مأخوذ) — عداد مستقل
        c = self.overflow
        with c._lock:
            k = (metric[:120],)
            c._series[k] = c._series.get(k, 0.0) + 1

    def register_collector(self, name: str, fn: Callable[[], Iterable[Sample]]) -> None:
        with self._lock:
            self._collectors = [(n, f) for n, f in self._collectors if n != name]
            self._collectors.append((name, fn))

    def _collect(self) -> List[Sample]:
        out: List[Sample] = []
        with self._lock:
            cols = list(self._collectors)
        for name, fn in cols:
            try:
                out.extend(list(fn()))
            except Exception as exc:  # TOLERATED: جامع معطوب يُعدّ ولا يكسر القراءة
                self.collector_errors.inc({"collector": name})
                _log.warning("R-846: الجامع %s فشل: %s", name, type(exc).__name__)
        return out

    def render(self) -> str:
        samples = self._collect()
        lines: List[str] = [
            "# HELP process_uptime_seconds زمن تشغيل العملية",
            "# TYPE process_uptime_seconds gauge",
            f"process_uptime_seconds {_fmt(round(time.time() - self.started_at, 3))}",
            "# HELP process_threads خيوط العملية الحية",
            "# TYPE process_threads gauge",
            f"process_threads {threading.active_count()}",
        ]
        with self._lock:
            metrics = sorted(self._metrics.values(), key=lambda m: m.name)
        for m in metrics:
            body = m.render()
            if not body:
                continue
            lines += [f"# HELP {m.name} {m.help}", f"# TYPE {m.name} {m.kind}", *body]
        by_name: Dict[str, List[Sample]] = {}
        for s in samples:
            if _NAME_RE.match(s[0]) and s[0] not in self._metrics:
                by_name.setdefault(s[0], []).append(s)
        for name in sorted(by_name):
            first = by_name[name][0]
            lines += [f"# HELP {name} {first[2]}", f"# TYPE {name} {first[1]}"]
            for _, _, _, labels, v in by_name[name]:
                names = sorted(labels)
                lines.append(f"{name}{_labels_str(names, [redact(labels[n])[:120] for n in names])} {_fmt(float(v))}")
        return "\n".join(lines) + "\n"

    def snapshot(self) -> Dict[str, Any]:
        """عرض JSON مختصر — العدادات والمقاييس والجامعون (بلا دلاء)."""
        out: Dict[str, Any] = {}
        with self._lock:
            metrics = list(self._metrics.values())
        for m in metrics:
            with m._lock:
                if isinstance(m, Histogram):
                    out[m.name] = [{"labels": dict(zip(m.labelnames, k)), "count": s["count"],
                                    "sum": round(s["sum"], 6)} for k, s in m._series.items()]
                else:
                    out[m.name] = [{"labels": dict(zip(m.labelnames, k)), "value": v}
                                   for k, v in m._series.items()]
        for name, kind, _h, labels, v in self._collect():
            out.setdefault(name, []).append({"labels": labels, "value": v})
        return out


REGISTRY = Registry()


def registry() -> Registry:
    """السجل الحالي — استعمله بدل استيراد REGISTRY مباشرة (reset_for_tests يستبدله)."""
    return REGISTRY


def reset_for_tests() -> Registry:
    global REGISTRY
    REGISTRY = Registry()
    return REGISTRY
