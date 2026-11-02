# R-830: ربط صريح بدل star imports — كل اسم في __all__ معرّف فعليًا
# (كان «قد تكون غير معرفة» عبر النجمة بلا تحقق؛ الاستهلاك كله عبر الوحدات الفرعية)
from . import (
    quantum_state,
    quantum_transition,
    quantum_superposition,
    quantum_field,
    quantum_controller,
)

__all__ = [
    'quantum_state',
    'quantum_transition',
    'quantum_superposition',
    'quantum_field',
    'quantum_controller',
]
