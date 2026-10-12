"""Security regression tests for sovereign-key configuration."""

import os
import subprocess
import sys


def _run_config(env):
    command = [
        sys.executable,
        "-c",
        "import config; print(config.SOVEREIGN_KEY)",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def test_development_without_key_uses_random_ephemeral_key():
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"

    first = _run_config(env)
    second = _run_config(env)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout.strip()
    assert second.stdout.strip()
    assert first.stdout.strip() != second.stdout.strip()
    assert "مفتاح_افتراضي_غير_آمن" not in first.stdout


def test_production_without_key_fails_closed():
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "production"

    result = _run_config(env)

    assert result.returncode != 0
    assert "لم يتم تعيين مفتاح السيد" in (result.stderr + result.stdout)
