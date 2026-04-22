import subprocess
import tempfile
from pathlib import Path
from typing import List

from rich.console import Console

from autodev.agents.qa_env import ensure_qa_venv
from autodev.agents.failure_control import record_failure
from autodev.workflow.state import ProjectState

console = Console()


def _extract_smoke_paths(endpoints: object) -> List[str]:
    if not isinstance(endpoints, list):
        return []

    paths: List[str] = []
    for item in endpoints:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s:
            continue
        path = s.split()[0].strip()
        if not path.startswith("/"):
            continue
        path = path.replace("{id}", "1").replace("{user_id}", "1")
        paths.append(path)

    seen = set()
    out: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _write_fastapi_smoke_test(temp_path: Path, spec: object) -> None:
    endpoints = []
    if isinstance(spec, dict):
        endpoints = _extract_smoke_paths(spec.get("endpoints"))

    lines: List[str] = []
    lines.append("from fastapi.testclient import TestClient")
    lines.append("")
    lines.append("from app.main import app")
    lines.append("")
    lines.append("client = TestClient(app)")
    lines.append("")
    lines.append("def test_openapi_smoke():")
    lines.append("    resp = client.get('/openapi.json')")
    lines.append("    assert resp.status_code == 200")

    if endpoints:
        lines.append("")
        lines.append("def test_endpoints_smoke():")
        for p in endpoints:
            lines.append(f"    resp = client.get('{p}')")
            lines.append("    assert resp.status_code < 500")

    test_path = temp_path / "tests" / "test_smoke.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def qa_node(state: ProjectState) -> ProjectState:
    console.print("[bold red][QA][/bold red] 使用缓存 venv 执行隔离验证...")

    qa_python = ensure_qa_venv()
    run = state.setdefault("run", {})
    artifacts = state.setdefault("artifacts", {})

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for file_path, content in artifacts.items():
            full_path = temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        architecture_type = str(state["spec"].get("architecture", "")).lower()

        if "单文件脚本" in architecture_type or "script" in architecture_type:
            check_cmd = [qa_python, "-m", "py_compile", "app/main.py"]
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
                console.print("[bold red][QA] ❌ 语法检查失败[/bold red]")
                console.print(f"[dim]{error_log}[/dim]")
                run.setdefault("errors", [])
                run["errors"] = [f"QA 语法检查失败:\n```text\n{error_log}\n```"]
                run["qa"] = {"passed": False, "error": error_log, "command": check_cmd}
                record_failure(state, step="qa", reason="py_compile_failed", detail=error_log)
                return state

            smoke_cmd = [qa_python, "app/main.py"]
            check_cmd = smoke_cmd
            console.print(f"[bold red][QA][/bold red] 执行: {' '.join(smoke_cmd)}")
            try:
                result = subprocess.run(
                    smoke_cmd,
                    cwd=str(temp_path),
                    input="q\n",
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
            except subprocess.TimeoutExpired:
                error_log = "CLI smoke test timeout"
                console.print("[bold red][QA] ❌ CLI smoke test 超时[/bold red]")
                run.setdefault("errors", [])
                run["errors"] = [f"QA smoke test 失败:\n```text\n{error_log}\n```"]
                run["qa"] = {"passed": False, "error": error_log, "command": smoke_cmd}
                record_failure(state, step="qa", reason="cli_smoke_timeout", detail=error_log)
                return state
        else:
            _write_fastapi_smoke_test(temp_path, state.get("spec"))
            check_cmd = [qa_python, "-m", "pytest", "-q"]
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
            run.setdefault("errors", [])
            run["errors"] = [f"QA 验证失败:\n```text\n{error_log}\n```"]
            run["qa"] = {"passed": False, "error": error_log, "command": check_cmd}
            record_failure(state, step="qa", reason="sandbox_validation_failed", detail=error_log)
            return state

    console.print("[bold green][QA] ✅ 沙盒验证通过[/bold green]")
    run["qa"] = {"passed": True, "command": check_cmd}
    return state