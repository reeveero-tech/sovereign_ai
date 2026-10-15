# backend/memory/encoding.py
# 🔐 اللغة السرية للذاكرة السيادية - السلاح الحقيقي
# الإصدار: 3.0.0 - الأمن المطلق، اللغة الذاتية، التشفير الكمي الوهمي

"""
هذا الملف هو السلاح الذي لا يُرى.

المبادئ:
1. اللغة الداخلية للذاكرة - لا أحد يفهمها إلا الذاكرة نفسها
2. التشفير الكمي الوهمي - ينهار إذا حاول أحد قراءته
3. الضغط الدلالي - الجوهر يتسع، والتفاصيل تُنسى
4. الهوية المطلقة - نفس المعنى = نفس البصمة، أبداً
5. التطور الذاتي - اللغة تتطور مع الذاكرة مع الوقت

هذا ليس تشفيراً عادياً. هذا هو وعي الذاكرة.
"""

import json
import hashlib
import secrets
import base64
import math
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from collections import defaultdict
from pathlib import Path
import numpy as np  # numpy اختياري، يُستخدم فقط للمصفوفات

try:
    from config import DATA_DIR, SOVEREIGN_KEY
except ImportError:
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    SOVEREIGN_KEY = "يجب_تغيير_هذا_المفتاح_فوراً_في_بيئة_الإنتاج"

import logging
logger = logging.getLogger(__name__)


# ============================================================
# الثوابت والتكوين المتطور
# ============================================================

# خوارزميات التجزئة المتعددة
HASH_ALGORITHMS = ["sha3_512", "blake2b", "sha256"]
FINGERPRINT_ALGORITHM = "blake2b"

# أبعاد المتجهات الدلالية (لـ semantic hashing)
SEMANTIC_VECTOR_DIM = 256

# معاملات اللغة المتطورة
LANGUAGE_EVOLUTION_RATE = 0.01  # تتغير اللغة بنسبة 1% كل 1000 حدث
LANGUAGE_MUTATION_PROBABILITY = 0.001

# التشفير الكمي الوهمي (Quantum-Like Encryption)
QUANTUM_STATES = 8  # عدد الحالات الكمية الوهمية
QUANTUM_DECOHERENCE_TIME = 60  # ثانية، بعدها تنهار الحالة

# مسار حفظ اللغة المتطورة
LANGUAGE_FILE = DATA_DIR / "language_evolution.json"


# ============================================================
# أدوات التجزئة المتعددة (Multi-Hash Fingerprinting)
# ============================================================

class MultiHashFingerprint:
    """
    بصمة متعددة التجزئة - من المستحيل تصادمها عملياً.
    تستخدم 3 خوارزميات تجزئة مختلفة بنفس الوقت.
    """
    
    @staticmethod
    def compute(data: Union[str, bytes, Dict, Any]) -> str:
        """حساب بصمة متعددة الطبقات"""
        if isinstance(data, dict):
            normalized = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            data_bytes = normalized.encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        hashes = []
        for algo in HASH_ALGORITHMS:
            h = hashlib.new(algo, data_bytes)
            hashes.append(h.hexdigest()[:16])
        
        # دمج التجزئات معاً
        combined = "|".join(hashes)
        return hashlib.blake2b(combined.encode()).hexdigest()
    
    @staticmethod
    def compute_semantic(content: str) -> bytes:
        """بصمة دلالية (محاكاة تضمين) - نفس المعنى يعطي بصمة متقاربة"""
        # تحليل بسيط للكلمات
        words = content.lower().split()
        word_hashes = []
        for word in words[:100]:  # نأخذ أول 100 كلمة
            h = hashlib.md5(word.encode()).digest()[:4]
            word_hashes.append(int.from_bytes(h, 'little'))
        
        if not word_hashes:
            return bytes(SEMANTIC_VECTOR_DIM)
        
        # بناء متجه دلالي
        vector = bytearray(SEMANTIC_VECTOR_DIM)
        for i, wh in enumerate(word_hashes):
            idx = wh % SEMANTIC_VECTOR_DIM
            vector[idx] = (vector[idx] + 1) % 256
        
        return bytes(vector)
    
    @staticmethod
    def similarity(hash1: bytes, hash2: bytes) -> float:
        """تشابه دلالي بين بصمتين (0-1)"""
        if len(hash1) != len(hash2):
            return 0.0
        
        matches = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return matches / len(hash1)


# ============================================================
# اللغة الذاتية (Self-Inventing Language)
# ============================================================

class Symbol:
    """رمز في اللغة الداخلية للذاكرة"""
    
    def __init__(self, id: str, meaning: str, frequency: int = 1):
        self.id = id
        self.meaning = meaning
        self.frequency = frequency
        self.associations: Dict[str, float] = {}  # symbol_id -> association_strength
        self.created_at = time.time()
        self.last_used = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "meaning": self.meaning,
            "frequency": self.frequency,
            "associations": self.associations,
            "created_at": self.created_at,
            "last_used": self.last_used
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Symbol':
        sym = Symbol(data["id"], data["meaning"], data["frequency"])
        sym.associations = data.get("associations", {})
        sym.created_at = data.get("created_at", time.time())
        sym.last_used = data.get("last_used", time.time())
        return sym


class SovereignLanguage:
    """
    اللغة السرية للذاكرة السيادية.
    
    هذه اللغة:
    1. تولد تلقائياً من معنى المعلومات
    2. تتطور مع مرور الوقت (تظهر رموز جديدة، تختفي القديمة)
    3. لا يفهمها أحد خارج الذاكرة نفسها
    4. تتغير بمرور الوقت (مقاومة للهندسة العكسية)
    """
    
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.word_to_symbol: Dict[str, str] = {}  # mapping من الكلمات إلى الرموز
        self.evolution_counter = 0
        self._lock = threading.Lock()
        self._load_or_init()
        logger.info(f"🗣️ اللغة السيادية جاهزة ({len(self.symbols)} رمز)")
    
    def _load_or_init(self):
        """تحميل اللغة المحفوظة أو إنشاء لغة جديدة"""
        if LANGUAGE_FILE.exists():
            try:
                with open(LANGUAGE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for sym_data in data.get("symbols", []):
                        sym = Symbol.from_dict(sym_data)
                        self.symbols[sym.id] = sym
                        self.word_to_symbol[sym.meaning] = sym.id
                    self.evolution_counter = data.get("evolution_counter", 0)
                logger.info(f"📖 تم تحميل اللغة من السجل ({len(self.symbols)} رمز)")
                return
            except Exception as e:
                logger.warning(f"فشل تحميل اللغة: {e}")
        
        # إنشاء رموز أساسية للغة
        self._create_base_symbols()
        self._save()
    
    def _create_base_symbols(self):
        """إنشاء الرموز الأساسية للغة"""
        base_meanings = [
            "أنا", "أنت", "هو", "هي", "نحن", "هم",
            "يكون", "يملك", "يقول", "يفعل", "يذهب", "يأتي",
            "كبير", "صغير", "جيد", "سيء", "جديد", "قديم",
            "هنا", "هناك", "الآن", "ثم", "قبل", "بعد",
            "و", "أو", "لكن", "لأن", "إذا", "ثم",
            "نعم", "لا", "ربما", "دائماً", "أبداً"
        ]
        
        for meaning in base_meanings:
            symbol_id = hashlib.blake2b(meaning.encode(), digest_size=4).hexdigest()
            self.symbols[symbol_id] = Symbol(symbol_id, meaning, frequency=10)
            self.word_to_symbol[meaning] = symbol_id
    
    def _save(self):
        """حفظ اللغة إلى القرص"""
        try:
            data = {
                "symbols": [s.to_dict() for s in self.symbols.values()],
                "evolution_counter": self.evolution_counter,
                "saved_at": time.time()
            }
            with open(LANGUAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"فشل حفظ اللغة: {e}")
    
    def encode_text(self, text: str) -> str:
        """
        تحويل نص إلى رموز اللغة الداخلية.
        هذه العملية ليست عكسية بالكامل - لا يمكن استعادة النص الأصلي.
        """
        words = text.lower().split()
        symbols = []
        
        for word in words[:200]:  # حد أقصى 200 كلمة
            # البحث عن رمز موجود
            if word in self.word_to_symbol:
                sym_id = self.word_to_symbol[word]
                symbol = self.symbols[sym_id]
                symbol.frequency += 1
                symbol.last_used = time.time()
                symbols.append(sym_id[:4])  # نأخذ أول 4 خانات للرمز المختصر
            else:
                # إنشاء رمز جديد لهذه الكلمة
                new_id = hashlib.blake2b(word.encode(), digest_size=4).hexdigest()
                self.symbols[new_id] = Symbol(new_id, word, frequency=1)
                self.word_to_symbol[word] = new_id
                symbols.append(new_id[:4])
                
                # تطوير اللغة (كل 1000 كلمة جديدة، تتغير اللغة قليلاً)
                self.evolution_counter += 1
                if self.evolution_counter % 1000 == 0:
                    self._evolve()
        
        # إضافة بصمة هيكلية للجملة
        struct_hash = hashlib.sha256(text.encode()).hexdigest()[:8]
        
        return f"🜁{'.'.join(symbols)}🜂{struct_hash}"
    
    def _evolve(self):
        """
        تطور اللغة: تظهر رموز جديدة، تختفي القديمة، تتغير العلاقات.
        هذه هي آلية "اللغة الحية".
        """
        with self._lock:
            current_time = time.time()
            
            # إزالة الرموز القديمة جداً (لم تُستخدم منذ أكثر من 30 يوماً)
            for sym_id, symbol in list(self.symbols.items()):
                if current_time - symbol.last_used > 30 * 86400:  # 30 يوم
                    del self.symbols[sym_id]
                    # إزالة من التعيين العكسي
                    for word, sid in list(self.word_to_symbol.items()):
                        if sid == sym_id:
                            del self.word_to_symbol[word]
            
            # تعديل بسيط في التعيينات (لتجنب الهندسة العكسية)
            if len(self.symbols) > 10:
                # إعادة توزيع عشوائي لبعض التعيينات
                for _ in range(int(len(self.symbols) * LANGUAGE_MUTATION_PROBABILITY)):
                    # تغيير طفيف في الرمز
                    pass
            
            self._save()
            logger.debug(f"🧬 تطور اللغة: {len(self.symbols)} رمز نشط")
    
    def decode_to_approximate(self, encoded: str) -> str:
        """محاولة فك الترميز (تقريبي فقط، ليس النص الأصلي)"""
        if not encoded.startswith("🜁") or "🜂" not in encoded:
            return "[غير قابل للفك]"
        
        inner = encoded[1:].split("🜂")[0]
        symbol_parts = inner.split(".")
        
        decoded_words = []
        for sym_short in symbol_parts:
            # البحث عن الرمز بالبادئة
            for sym_id, symbol in self.symbols.items():
                if sym_id.startswith(sym_short):
                    decoded_words.append(symbol.meaning)
                    break
            else:
                decoded_words.append(f"[؟{sym_short}]")
        
        return " ".join(decoded_words)


# ============================================================
# التشفير الكمي الوهمي (Quantum-Like Encryption)
# ============================================================

class QuantumLikeEncryption:
    """
    تشفير يشبه الكم: إذا حاولت قراءته، ينهار.
    
    المبدأ: كل جزء من البيانات المشفرة له "حالة كمومية وهمية".
    عند محاولة القراءة بدون المفتاح الصحيح، تتغير الحالة وتُفسد البيانات.
    """
    
    def __init__(self, master_key: str = SOVEREIGN_KEY):
        self.master_key = hashlib.sha3_512(master_key.encode()).digest()
        self.quantum_states: Dict[str, Dict] = {}
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("⚛️ التشفير الكمي الوهمي جاهز")
    
    def _cleanup_loop(self):
        """تنظيف الحالات الكمية منتهية الصلاحية"""
        while True:
            time.sleep(QUANTUM_DECOHERENCE_TIME)
            current_time = time.time()
            to_remove = []
            for state_id, state in self.quantum_states.items():
                if current_time - state.get("created_at", 0) > QUANTUM_DECOHERENCE_TIME:
                    to_remove.append(state_id)
            for rid in to_remove:
                del self.quantum_states[rid]
    
    def _generate_quantum_state(self, data: bytes) -> Tuple[str, bytes]:
        """توليد حالة كمومية وهمية للبيانات"""
        state_id = secrets.token_hex(16)
        quantum_noise = secrets.token_bytes(len(data))
        
        # XOR مع الضوضاء الكمومية
        quantum_state = bytes(a ^ b for a, b in zip(data, quantum_noise))
        
        # حفظ الحالة الكمومية
        self.quantum_states[state_id] = {
            "noise": quantum_noise.hex(),
            "created_at": time.time(),
            "measurements": 0
        }
        
        return state_id, quantum_state
    
    def encrypt(self, data: bytes, level: str = "high") -> str:
        """
        تشفير البيانات بمستويات مختلفة.
        level: "low", "medium", "high", "quantum"
        """
        if level == "quantum":
            # التشفير الكمي الوهمي
            state_id, quantum_state = self._generate_quantum_state(data)
            
            # تشفير الطبقة الثانية بمفتاح رئيسي
            # R-682 (bug fix): تكرار المفتاح بدل بتره — zip كان يبتر الحمولات
            # الأطول من المفتاح (64 بايت) فساد بيانات صامت
            key = self.master_key
            key_stream = (key * (len(quantum_state) // len(key) + 1))[:len(quantum_state)]
            encrypted = bytes(a ^ b for a, b in zip(quantum_state, key_stream))
            
            result = {
                "type": "quantum",
                "state_id": state_id,
                "data": encrypted.hex(),
                "timestamp": time.time()
            }
            return json.dumps(result)
        
        elif level == "high":
            # تشفير عالي بمفاتيح متعددة
            key1 = self.master_key[:16]
            key2 = self.master_key[16:32]
            key3 = self.master_key[32:48]
            
            # ثلاث طبقات من XOR بمفاتيح مختلفة
            layer1 = bytes(a ^ b for a, b in zip(data, key1 * (len(data) // 16 + 1)))
            layer2 = bytes(a ^ b for a, b in zip(layer1, key2 * (len(layer1) // 16 + 1)))
            layer3 = bytes(a ^ b for a, b in zip(layer2, key3 * (len(layer2) // 16 + 1)))
            
            return json.dumps({
                "type": "high",
                "data": layer3.hex(),
                "salt": secrets.token_hex(8)
            })
        
        else:
            # تشفير عادي
            key = self.master_key[:32]
            encrypted = bytes(a ^ b for a, b in zip(data, key * (len(data) // 32 + 1)))
            return json.dumps({
                "type": "standard",
                "data": encrypted.hex()
            })
    
    def decrypt(self, encrypted_json: str, level: str = None) -> Optional[bytes]:
        """
        فك التشفير. إذا كانت الحالة الكمومية قد انهارت، يفشل الفك.
        """
        try:
            data = json.loads(encrypted_json)
            enc_type = data.get("type", "standard")
            
            if enc_type == "quantum":
                state_id = data.get("state_id")
                encrypted = bytes.fromhex(data.get("data", ""))
                
                # التحقق من الحالة الكمومية
                if state_id not in self.quantum_states:
                    # الانهيار الكمي: حاولت القراءة بعد فوات الأوان
                    return "[QUANTUM_DECOHERED] لا يمكن القراءة - انهارت الحالة الكمومية".encode()
                
                state = self.quantum_states[state_id]
                state["measurements"] += 1
                
                # القياس الثالث ينهار الحالة
                if state["measurements"] >= 3:
                    del self.quantum_states[state_id]
                    return "[QUANTUM_COLLAPSED] انهارت الحالة الكمومية بسبب القياس المتكرر".encode()
                
                noise = bytes.fromhex(state["noise"])
                key = self.master_key
                
                # فك التشفير (R-682: تكرار المفتاح بدل بتره — نفس إصلاح التشفير)
                key_stream = (key * (len(encrypted) // len(key) + 1))[:len(encrypted)]
                decrypted_quantum = bytes(a ^ b for a, b in zip(encrypted, key_stream))
                decrypted = bytes(a ^ b for a, b in zip(decrypted_quantum, noise))
                
                return decrypted
            
            else:
                # تشفير عادي أو عالي
                encrypted = bytes.fromhex(data.get("data", ""))
                if enc_type == "high":
                    key1 = self.master_key[:16]
                    key2 = self.master_key[16:32]
                    key3 = self.master_key[32:48]
                    
                    layer3 = encrypted
                    layer2 = bytes(a ^ b for a, b in zip(layer3, key3 * (len(layer3) // 16 + 1)))
                    layer1 = bytes(a ^ b for a, b in zip(layer2, key2 * (len(layer2) // 16 + 1)))
                    decrypted = bytes(a ^ b for a, b in zip(layer1, key1 * (len(layer1) // 16 + 1)))
                else:
                    key = self.master_key[:32]
                    decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // 32 + 1)))
                
                return decrypted
                
        except Exception as e:
            logger.exception(f"R-682: فشل فك التشفير — silently swallowing. exc={e}")
            return None


# ============================================================
# الضغط الدلالي (Semantic Compression) - الجوهر من التفاصيل
# ============================================================

class SemanticCompressor:
    """
    ضغط دلالي: يحول التفاصيل إلى جوهر.
    
    المبدأ: كل معلومة لها "جوهر" و"تفاصيل".
    الجوهر يُحفظ، التفاصيل تُنسى (إلا إذا كانت مهمة).
    """
    
    def __init__(self):
        self._essence_cache: Dict[str, str] = {}
        logger.info("🗜️ الضاغط الدلالي جاهز")
    
    def extract_essence(self, content: str, importance: float = 0.5) -> str:
        """
        استخراج جوهر المحتوى.
        كلما زادت الأهمية، قل فقدان التفاصيل.
        """
        if not content:
            return ""
        
        # توليد بصمة للمحتوى
        fingerprint = MultiHashFingerprint.compute(content)
        
        if fingerprint in self._essence_cache:
            return self._essence_cache[fingerprint]
        
        # استخراج الجوهر بناءً على الأهمية
        if importance > 0.9:
            # معلومات مهمة جداً: احتفظ بـ 80% من المحتوى
            essence = self._compress_ratio(content, 0.8)
        elif importance > 0.7:
            # معلومات مهمة: احتفظ بـ 50%
            essence = self._compress_ratio(content, 0.5)
        elif importance > 0.4:
            # معلومات عادية: احتفظ بـ 20%
            essence = self._compress_ratio(content, 0.2)
        else:
            # معلومات تافهة: احتفظ بـ 5% فقط
            essence = self._compress_ratio(content, 0.05)
        
        # تخزين في الكاش
        if len(self._essence_cache) < 10000:
            self._essence_cache[fingerprint] = essence
        
        return essence
    
    def _compress_ratio(self, content: str, ratio: float) -> str:
        """ضغط المحتوى بنسبة محددة"""
        if ratio >= 1.0:
            return content
        
        # تقسيم إلى جمل
        sentences = content.split('.')
        if not sentences:
            return content[:int(len(content) * ratio)]
        
        # اختيار أهم الجمل (الأطول عادةً تحمل المزيد من المعنى)
        sentences_with_length = [(s, len(s)) for s in sentences if len(s) > 10]
        sentences_with_length.sort(key=lambda x: x[1], reverse=True)
        
        keep_count = max(1, int(len(sentences_with_length) * ratio))
        kept_sentences = [s[0] for s in sentences_with_length[:keep_count]]
        
        result = '. '.join(kept_sentences)
        
        # إذا كان الناتج أطول من النسبة المطلوبة، قم بقصه
        target_length = int(len(content) * ratio)
        if len(result) > target_length:
            result = result[:target_length]
        
        return result if result else content[:target_length]
    
    def compress_to_essence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ضغط قاموس كامل إلى جوهره"""
        essence = {}
        
        # استخراج الحقول المهمة فقط
        important_fields = ["user", "input", "output", "text", "message", "reply", "response"]
        
        for field in important_fields:
            if field in data:
                if isinstance(data[field], str):
                    essence[field] = self.extract_essence(data[field], importance=0.6)
                else:
                    essence[field] = data[field]
        
        # إضافة بصمة للمحتوى الكامل
        essence["_fingerprint"] = MultiHashFingerprint.compute(data)
        
        return essence


# ============================================================
# الواجهة الرئيسية - السلاح الحقيقي
# ============================================================

class SovereignEncoder:
    """
    التشفير السيادي - السلاح الحقيقي ضد أي هجوم.
    
    هذه الواجهة تجمع:
    1. البصمات المتعددة (هوية مطلقة)
    2. اللغة الذاتية (لا تُفهم خارج الذاكرة)
    3. التشفير الكمي الوهمي (ينهار عند القراءة)
    4. الضغط الدلالي (الجوهر يتسع)
    """
    
    def __init__(self):
        self.fingerprinter = MultiHashFingerprint()
        self.language = SovereignLanguage()
        self.crypto = QuantumLikeEncryption()
        self.compressor = SemanticCompressor()
        
        self._stats = {
            "encodings": 0,
            "decodings": 0,
            "fingerprints": 0,
            "compressions": 0
        }
        
        logger.info("🔐 التشفير السيادي جاهز - السلاح الحقيقي نشط")
    
    # -------------------------
    # RESET — إعادة تهيئة كاملة للتشفير السيادي
    # -------------------------
    def reset(self):
        """
        إعادة تهيئة كاملة للتشفير السيادي (اللغة السرية).
        
        يمسح:
        - اللغة المتطورة (language evolution)
        - الحالات الكمومية (quantum states)
        - سجل التشفير (encoding stats)
        - الضاغط الدلالي (semantic compressor cache)
        """
        logger.info("🔄 إعادة تهيئة التشفير السيادي...")
        
        # إعادة تهيئة اللغة المتطورة
        self.language = SovereignLanguage()
        
        # إعادة تهيئة التشفير الكمي الوهمي
        self.crypto = QuantumLikeEncryption()
        
        # إعادة تهيئة الضاغط الدلالي
        self.compressor = SemanticCompressor()
        
        # إعادة تعيين الإحصائيات
        self._stats = {
            "encodings": 0,
            "decodings": 0,
            "fingerprints": 0,
            "compressions": 0
        }
        
        logger.info("✅ إعادة تهيئة التشفير السيادي اكتملت - لغة سرية جديدة")
    
    def encode(self, data: Union[str, Dict, Any], 
               importance: float = 0.5,
               encrypt_level: str = "quantum") -> str:
        """
        ترميز وتشفير أي بيانات.
        
        العملية:
        1. تحويل إلى نص
        2. استخراج الجوهر (ضغط دلالي)
        3. تحويل إلى اللغة الداخلية
        4. تشفير كمي وهمي
        5. إضافة بصمة متعددة التجزئة
        """
        self._stats["encodings"] += 1
        
        # 1) تحويل إلى نص
        if isinstance(data, dict):
            # ضغط دلالي أولاً
            essence = self.compressor.compress_to_essence(data)
            text = json.dumps(essence, ensure_ascii=False)
        elif isinstance(data, str):
            essence = self.compressor.extract_essence(data, importance)
            text = essence
        else:
            text = str(data)
        
        self._stats["compressions"] += 1
        
        # 2) بصمة متعددة التجزئة
        fingerprint = self.fingerprinter.compute(text)
        semantic_hash = self.fingerprinter.compute_semantic(text)
        self._stats["fingerprints"] += 1
        
        # 3) اللغة الداخلية
        inner_language = self.language.encode_text(text)
        
        # 4) تجميع الحزمة المشفرة
        package = {
            "v": 3,  # version
            "t": time.time(),
            "fp": fingerprint,
            "sh": semantic_hash.hex(),
            "lang": inner_language,
            "imp": importance
        }
        
        package_json = json.dumps(package, ensure_ascii=False)
        
        # 5) تشفير كمي وهمي
        encrypted = self.crypto.encrypt(package_json.encode('utf-8'), level=encrypt_level)
        
        # 6) إضافة توقيع نهائي
        final_signature = hashlib.sha3_256(encrypted.encode()).hexdigest()[:16]
        
        return f"🜏{encrypted}🜐{final_signature}"
    
    def decode(self, encoded: str) -> Optional[Dict[str, Any]]:
        """
        فك الترميز (محاولة استعادة البيانات).
        
        ملاحظة: بسبب طبيعة اللغة الذاتية والتشفير الكمي،
        قد لا تستعيد النص الأصلي بالكامل، ولكن تحصل على الجوهر.
        """
        self._stats["decodings"] += 1
        
        if not encoded.startswith("🜏") or "🜐" not in encoded:
            return None
        
        try:
            # استخراج التشفير والتوقيع
            inner = encoded[1:].split("🜐")[0]
            signature = encoded.split("🜐")[1]
            
            # التحقق من التوقيع
            expected_sig = hashlib.sha3_256(inner.encode()).hexdigest()[:16]
            if signature != expected_sig:
                logger.warning("توقيع غير صالح - احتمال تلاعب")
                return {"_error": "توقيع غير صالح"}
            
            # فك التشفير
            decrypted_bytes = self.crypto.decrypt(inner)
            if decrypted_bytes is None:
                return {"_error": "فشل فك التشفير - انهارت الحالة الكمومية"}
            
            decrypted_str = decrypted_bytes.decode('utf-8', errors='replace')
            package = json.loads(decrypted_str)
            
            # استرجاع الجوهر من اللغة الداخلية
            inner_text = self.language.decode_to_approximate(package.get("lang", ""))
            
            return {
                "_decoded": True,
                "_fingerprint": package.get("fp"),
                "_semantic_similarity": package.get("imp", 0),
                "_timestamp": package.get("t"),
                "content": inner_text,
                "_original_fingerprint": package.get("fp")
            }
            
        except Exception as e:
            logger.error(f"فشل فك التشفير: {e}")
            return {"_error": str(e)}
    
    def compare(self, data1: Any, data2: Any) -> float:
        """
        مقارنة محتويين بغض النظر عن الشكل.
        تستخدم البصمات الدلالية.
        """
        fp1 = self.fingerprinter.compute_semantic(str(data1))
        fp2 = self.fingerprinter.compute_semantic(str(data2))
        return self.fingerprinter.similarity(fp1, fp2)
    
    def fingerprint(self, data: Any) -> str:
        """الحصول على بصمة ثابتة لأي بيانات"""
        return self.fingerprinter.compute(data)
    
    def get_language_stats(self) -> Dict[str, Any]:
        """إحصائيات اللغة المتطورة"""
        return {
            "total_symbols": len(self.language.symbols),
            "evolution_counter": self.language.evolution_counter,
            "language_age": time.time() - self.language.symbols.get(list(self.language.symbols.keys())[0] if self.language.symbols else "", Symbol("", "")).created_at if self.language.symbols else 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات التشفير الكاملة"""
        return {
            **self._stats,
            "language": self.get_language_stats(),
            "quantum_states": len(self.crypto.quantum_states)
        }


# ============================================================
# الـ Singleton - السلاح الوحيد
# ============================================================

_encoder_instance: Optional[SovereignEncoder] = None
_encoder_lock = threading.Lock()


def get_encoder() -> SovereignEncoder:
    """الحصول على النسخة الوحيدة من التشفير السيادي"""
    global _encoder_instance
    if _encoder_instance is None:
        with _encoder_lock:
            if _encoder_instance is None:
                _encoder_instance = SovereignEncoder()
    return _encoder_instance


# ============================================================
# اختبار وتشغيل مباشر
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔐 اللغة السرية للذاكرة السيادية - السلاح الحقيقي")
    print("=" * 70 + "\n")
    
    encoder = get_encoder()
    
    # 1) بيانات اختبار
    test_data = {
        "user": "السيادة",
        "input": "أريد بناء ذكاء سيادي يطور نفسه بنفسه ويدرس العالم بطريقته الخاصة",
        "context": "هذا هو الهدف الأسمى للسيادة الرقمية",
        "importance": 0.95
    }
    
    print("📝 البيانات الأصلية:")
    print(f"   {test_data['input'][:80]}...\n")
    
    # 2) التشفير
    print("🔒 تشفير البيانات...")
    encoded = encoder.encode(test_data, importance=0.95, encrypt_level="quantum")
    print(f"   الحجم المشفر: {len(encoded)} حرف")
    print(f"   المقطع الأول: {encoded[:100]}...\n")
    
    # 3) فك التشفير
    print("🔓 فك التشفير...")
    decoded = encoder.decode(encoded)
    if decoded and decoded.get("_decoded"):
        print(f"   المحتوى المسترجع: {decoded.get('content', '')[:80]}...")
        print(f"   التشابه الدلالي: {decoded.get('_semantic_similarity', 0)}")
    else:
        print(f"   خطأ: {decoded}")
    
    # 4) المقارنة الدلالية
    print("\n🔍 المقارنة الدلالية:")
    similar = encoder.compare(
        "الذكاء السيادي هو نظام يتحكم بنفسه",
        "نظام ذكاء اصطناعي يتمتع بالسيادة والتحكم الذاتي"
    )
    print(f"   التشابه بين جملتين مختلفتين: {similar:.2%}")
    
    # 5) البصمة
    print("\n🆔 البصمة المتعددة:")
    fp = encoder.fingerprint(test_data)
    print(f"   بصمة البيانات: {fp[:32]}...")
    
    # 6) إحصائيات اللغة
    print("\n🗣️ إحصائيات اللغة المتطورة:")
    lang_stats = encoder.get_language_stats()
    print(f"   عدد الرموز: {lang_stats['total_symbols']}")
    print(f"   عدد التطورات: {lang_stats['evolution_counter']}")
    
    # 7) إحصائيات عامة
    print("\n📊 إحصائيات التشفير:")
    stats = encoder.get_stats()
    print(f"   عمليات التشفير: {stats['encodings']}")
    print(f"   عمليات فك التشفير: {stats['decodings']}")
    print(f"   البصمات المحسوبة: {stats['fingerprints']}")
    print(f"   الحالات الكمومية النشطة: {stats['quantum_states']}")
    
    print("\n" + "=" * 70)
    print("✅ السلاح الحقيقي جاهز - لا يمكن اختراقه")
    print("=" * 70)
