# -*- coding: utf-8 -*-
"""R-847: تشفير متدفق للأرشيف — AES-256-GCM بقطع، ذاكرة ثابتة.

``AESGCM`` يحتاج الرسالة كاملة في الذاكرة، والأرشيف قد يبلغ مئات الميغابايت
على آلة ذاكرتها محدودة. لذا يُقسم النص إلى قطع (افتراضيًا 1 MiB)، ولكل قطعة
وسم مستقل:

    الرأس: MAGIC(5) | salt(16) | nonce_prefix(7) | chunk_size(4)  = 32 بايت
    القطعة: len(4, big-endian) | ciphertext+tag
    nonce = nonce_prefix(7) | counter(4) | last(1)
    AAD   = الرأس كاملًا

العداد يمنع إعادة الترتيب والتكرار، وعلم ``last`` يمنع البتر (أرشيف ينتهي بلا
قطعة أخيرة يُرفض)، والـAAD يربط القطع برأسها. والمفتاح يُشتق من
``SOVEREIGN_BACKUP_KEY`` بـscrypt وملح عشوائي لكل أرشيف. أما البصمة المحفوظة
مع النسخة فهي HMAC للمفتاح، ولا تكشفه.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import struct
from typing import BinaryIO, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"SVBK\x01"
HEADER_LEN = 32
CHUNK = 1 << 20
MIN_KEY_LEN = 32
_MAX_CHUNK = 16 << 20


class CryptoError(Exception):
    """فشل فك التشفير — ``reason`` من مفردات ثابتة."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def check_key(key: Optional[str]) -> None:
    if key is not None and len(key) < MIN_KEY_LEN:
        raise CryptoError("weak_key")


def fingerprint(key: str) -> str:
    """بصمة المفتاح (HMAC) — تحدد أي مفتاح شفّر النسخة بلا كشفه."""
    return hmac.new(key.encode("utf-8"), b"svbk-fingerprint-v1", hashlib.sha256).hexdigest()[:16]


def _derive(key: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1).derive(key.encode("utf-8"))


def is_encrypted(head: bytes) -> bool:
    return head[:len(MAGIC)] == MAGIC


def _nonce(prefix: bytes, counter: int, last: bool) -> bytes:
    return prefix + struct.pack(">I", counter) + (b"\x01" if last else b"\x00")


class EncryptingWriter:
    """كائن ملف للكتابة فقط: يشفر ما يُكتب فيه قطعًا إلى ``out``."""

    def __init__(self, out: BinaryIO, key: str, chunk: int = CHUNK):
        check_key(key)
        salt, self._prefix = os.urandom(16), os.urandom(7)
        self._header = MAGIC + salt + self._prefix + struct.pack(">I", chunk)
        self._aead = AESGCM(_derive(key, salt))
        self._out, self._chunk, self._buf, self._n = out, chunk, bytearray(), 0
        self._closed = False
        out.write(self._header)

    def _emit(self, data: bytes, last: bool) -> None:
        if self._n >= 0xFFFFFFFF:
            raise CryptoError("too_many_chunks")
        ct = self._aead.encrypt(_nonce(self._prefix, self._n, last), data, self._header)
        self._out.write(struct.pack(">I", len(ct)) + ct)
        self._n += 1

    def write(self, data) -> int:
        if self._closed:
            raise ValueError("الكاتب مغلق")
        self._buf += data
        # نُبقي قطعة كاملة على الأقل في الذاكرة حتى نعرف أيها الأخيرة
        while len(self._buf) > self._chunk:
            piece = bytes(self._buf[:self._chunk])
            del self._buf[:self._chunk]
            self._emit(piece, False)
        return len(data)

    def flush(self) -> None:
        self._out.flush()

    def close(self) -> None:
        if not self._closed:
            self._emit(bytes(self._buf), True)
            self._buf.clear()
            self._closed = True


class DecryptingReader:
    """كائن ملف للقراءة فقط: يفك القطع بالترتيب ويرفض البتر والعبث."""

    def __init__(self, src: BinaryIO, key: str):
        self._src = src
        header = src.read(HEADER_LEN)
        if len(header) != HEADER_LEN or not is_encrypted(header):
            raise CryptoError("not_encrypted")
        salt, self._prefix = header[5:21], header[21:28]
        (self._chunk,) = struct.unpack(">I", header[28:32])
        if not 0 < self._chunk <= _MAX_CHUNK:
            raise CryptoError("bad_header")
        self._header = header
        self._aead = AESGCM(_derive(key, salt))
        self._buf, self._n, self._done = b"", 0, False

    def _next(self) -> None:
        raw = self._src.read(4)
        if len(raw) < 4:
            raise CryptoError("truncated")
        (ln,) = struct.unpack(">I", raw)
        if ln > self._chunk + 16:
            raise CryptoError("bad_chunk")
        ct = self._src.read(ln)
        if len(ct) != ln:
            raise CryptoError("truncated")
        for last in (False, True):
            try:
                pt = self._aead.decrypt(_nonce(self._prefix, self._n, last), ct, self._header)
            except InvalidTag:  # TOLERATED: نجرب علمي «الأخيرة» ثم نحسم بالرفض أدناه
                continue
            self._n += 1
            self._buf += pt
            if last:
                self._done = True
                if self._src.read(1):
                    raise CryptoError("trailing_data")
            return
        raise CryptoError("auth_failed")

    def read(self, n: int = -1) -> bytes:
        while not self._done and (n < 0 or len(self._buf) < n):
            self._next()
        if n < 0:
            out, self._buf = self._buf, b""
        else:
            out, self._buf = self._buf[:n], self._buf[n:]
        return out
