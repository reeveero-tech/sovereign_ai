"""اختبارات إعدادات Ollama — OLLAMA_ENABLED/BASE_URL/MODEL/API_KEY/TIMEOUT.

بطلب المالك (2026-10-20، جولة R-704): ربط مستودع السيادي بخادم Ollama
محلي كعقل LLM بديلًا عن APIs الخارجية (OpenAI/DeepSeek/Google).

مبادئ التصميم (مثبتة هنا):
- العقل معطل افتراضيًا (OLLAMA_ENABLED=False) — لا اتصال ضمني في الاختبارات
  ولا افتراض خادم يعمل عند المطور.
- النموذج صريح لا افتراضي (OLLAMA_MODEL=None) — لا يُفترض نموذج غير مثبت.
- القراءة: متغير البيئة أولًا ثم ملف .env (قابل للعزل عبر OLLAMA_ENV_FILE
  للاختبارات) — دون المساس بقواعد مفتاح السيد.
- Ollama المحلي لا يتطلب مفتاح API (يبقى None) — المفتاح لخوادم التوثيق فقط.
"""

import os
import subprocess
import sys


def _run_config(env):
    """عملية مستقلة معزولة — نفس نمط test_config_security.py."""
    command = [
        sys.executable,
        "-c",
        "import config; "
        "print(config.OLLAMA_ENABLED); "
        "print(config.OLLAMA_BASE_URL); "
        "print(config.OLLAMA_MODEL); "
        "print(config.OLLAMA_API_KEY)",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def _base_env(tmp_path):
    """بيئة معزولة: لا متغيرات Ollama، لا ملف .env (مسار معدوم)،
    وجذر بيانات مؤقت — لا يُلمس مفتاح التشغيل الحقيقي ولا .env للمطور."""
    env = os.environ.copy()
    for var in ("OLLAMA_BASE_URL", "OLLAMA_API_KEY", "OLLAMA_MODEL", "OLLAMA_ENABLED"):
        env.pop(var, None)
    env["AI_ENVIRONMENT"] = "development"
    # عزل فعلي من .env للمطور: مسار معدوم + جذر بيانات مؤقت
    env["OLLAMA_ENV_FILE"] = str(tmp_path / "nonexistent.env")
    env["SOVEREIGN_DATA_ROOT"] = str(tmp_path / "data")
    return env


def test_ollama_disabled_by_default(tmp_path):
    """العقل معطل افتراضيًا — لا اتصال ضمني عند عدم الضبط الصريح."""
    result = _run_config(_base_env(tmp_path))
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    enabled, _, _, _ = result.stdout.strip().splitlines()
    assert enabled == "False", "OLLAMA_ENABLED must be False by default (explicit opt-in)"


def test_ollama_defaults(tmp_path):
    """بلا ضبط: العنوان الافتراضي 127.0.0.1:11434 والنموذج والمفتاح None."""
    result = _run_config(_base_env(tmp_path))
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    _, base_url, model, api_key = result.stdout.strip().splitlines()
    assert base_url == "http://127.0.0.1:11434", (
        "OLLAMA_BASE_URL must default to the standard local Ollama port"
    )
    assert model == "None", "OLLAMA_MODEL must be explicit (None by default)"
    assert api_key == "None", "OLLAMA_API_KEY must be optional (None by default)"


def test_ollama_base_url_from_env(tmp_path):
    """العنوان يُقرأ من البيئة — خادم على الشبكة المحلية مثالًا (محايد)."""
    env = _base_env(tmp_path)
    env["OLLAMA_BASE_URL"] = "http://10.0.0.5:11434"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    _, base_url, _, _ = result.stdout.strip().splitlines()
    assert base_url == "http://10.0.0.5:11434", (
        "OLLAMA_BASE_URL must be overridable via environment"
    )


def test_ollama_api_key_optional(tmp_path):
    """المفتاح يُقرأ من البيئة إن وُجد — اختياري لأن Ollama المحلي بلا توثيق."""
    env = _base_env(tmp_path)
    env["OLLAMA_API_KEY"] = "test-key-value"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    *_, api_key = result.stdout.strip().splitlines()
    assert api_key == "test-key-value", (
        "OLLAMA_API_KEY must be readable via environment when set"
    )


def test_ollama_reads_env_file(tmp_path):
    """الإعدادات تُقرأ من ملف .env (عبر OLLAMA_ENV_FILE) عند غياب متغير البيئة."""
    env_file = tmp_path / "ollama.env"
    env_file.write_text(
        "OLLAMA_ENABLED=true\n"
        "OLLAMA_BASE_URL=http://10.0.0.7:11434\n"
        "OLLAMA_MODEL=qwen2.5:7b\n",
        encoding="utf-8",
    )
    env = _base_env(tmp_path)
    env["OLLAMA_ENV_FILE"] = str(env_file)
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    enabled, base_url, model, _ = result.stdout.strip().splitlines()
    assert enabled == "True", "OLLAMA_ENABLED must load from env file"
    assert base_url == "http://10.0.0.7:11434", "OLLAMA_BASE_URL must load from env file"
    assert model == "qwen2.5:7b", "OLLAMA_MODEL must load from env file"


def test_env_takes_priority_over_env_file(tmp_path):
    """متغير البيئة يعلو على ملف .env عند تعارضهما."""
    env_file = tmp_path / "ollama.env"
    env_file.write_text("OLLAMA_MODEL=from-file\n", encoding="utf-8")
    env = _base_env(tmp_path)
    env["OLLAMA_ENV_FILE"] = str(env_file)
    env["OLLAMA_MODEL"] = "from-env"
    result = _run_config(env)
    assert result.returncode == 0, f"config run failed: {result.stderr}"
    *_, model, _ = result.stdout.strip().splitlines()
    assert model == "from-env", "environment variable must override .env file"
