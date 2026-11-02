# R-830: ربط صريح بدل star imports — كل اسم في __all__ معرّف فعليًا
# (كان «قد تكون غير معرفة» عبر النجمة بلا تحقق؛ الاستهلاك كله عبر الوحدات الفرعية)
from . import (
    field,
    identity_core,
    self_model,
    awareness,
    attention_engine,
    introspection,
)

__all__ = [
    'field',
    'identity_core',
    'self_model',
    'awareness',
    'attention_engine',
    'introspection',
]
