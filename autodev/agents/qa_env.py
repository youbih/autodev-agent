import os
import sys
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QA_ROOT = PROJECT_ROOT / ".autodev"
QA_VENV = QA_ROOT / "qa_venv"
QA_MARKER = QA_ROOT / ".deps_installed"
PIP_CACHE = QA_ROOT / "pip_cache"
# 修改为（增加 pydantic[email] 即可自动带上 email-validator）:
QA_DEPS = ["fastapi", "uvicorn", "sqlalchemy", "pydantic[email]"]


def _qa_python_path() -> Path:
    if os.name == "nt":
        return QA_VENV / "Scripts" / "python.exe"
    return QA_VENV / "bin" / "python"


def ensure_qa_venv() -> str:
    QA_ROOT.mkdir(parents=True, exist_ok=True)
    PIP_CACHE.mkdir(parents=True, exist_ok=True)

    py = _qa_python_path()

    if not py.exists():
        console.print("[bold red][QA][/bold red] 初始化 QA 缓存 venv...")
        subprocess.run([sys.executable, "-m", "venv", str(QA_VENV)], check=True)

    if not QA_MARKER.exists():
        console.print("[bold red][QA][/bold red] 首次安装 QA 依赖（只会发生一次）...")
        env = os.environ.copy()
        env["PIP_CACHE_DIR"] = str(PIP_CACHE)

        subprocess.run([str(py), "-m", "pip", "install", "-U", "pip"], check=True, env=env)
        subprocess.run([str(py), "-m", "pip", "install", *QA_DEPS], check=True, env=env)

        QA_MARKER.write_text("\n".join(QA_DEPS), encoding="utf-8")

    return str(py)