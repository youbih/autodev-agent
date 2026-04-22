import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

from autodev.agents.qa_env import ensure_qa_venv
from autodev.workflow.state import ProjectState

console = Console()


def qa_node(state: ProjectState) -> ProjectState:
    console.print("[bold red][QA][/bold red] 使用缓存 venv 执行隔离验证...")

    qa_python = ensure_qa_venv()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for file_path, content in state["files"].items():
            if file_path == "fixed":
                continue
            full_path = temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        architecture_type = str(state["spec"].get("architecture", "")).lower()

        if "单文件脚本" in architecture_type or "script" in architecture_type:
            check_cmd = [qa_python, "-m", "py_compile", "app/main.py"]
        else:
            check_cmd = [
                qa_python,
                "-c",
                "import sys; sys.path.insert(0, '.'); import app.main",
            ]

        console.print(f"[bold red][QA][/bold red] 执行: {' '.join(check_cmd)}")
        result = subprocess.run(
            check_cmd,
            cwd=str(temp_path),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_log = (result.stderr or result.stdout or "").strip()
            if len(error_log) > 800:
                error_log = "..." + error_log[-800:]
            console.print("[bold red][QA] ❌ 沙盒验证失败[/bold red]")
            console.print(f"[dim]{error_log}[/dim]")
            state["errors"] = [f"QA 验证失败:\n```text\n{error_log}\n```"]
            state["test_passed"] = False
            return state

    console.print("[bold green][QA] ✅ 沙盒验证通过[/bold green]")
    state["test_passed"] = True
    return state