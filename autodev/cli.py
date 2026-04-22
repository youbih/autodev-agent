import hashlib
import json
import typer
import yaml
import os
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from autodev.workflow.graph import build_graph
from autodev.agents.failure_control import init_run_controls
from autodev.workflow.schema import ProjectSpec
from pydantic import ValidationError

app = typer.Typer(help="AutoDev: 企业级后端代码生成与交付 Agent")
console = Console()

WORKSPACE_DIR = Path("workspace")

@app.command()
def init(name: str = typer.Option(..., help="项目名称"), 
         desc: str = typer.Option("基于 FastAPI 的后端服务", help="项目描述")):
    """
    第一步：初始化项目的 Spec 配置文件
    """
    project_dir = WORKSPACE_DIR / name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    spec_path = project_dir / "spec.yaml"
    
    spec_content = {
        "project_name": name,
        "description": desc,
        "framework": "FastAPI",
        "architecture": "layered (api -> service -> repo -> model)",
        "database": "SQLite + SQLAlchemy",
        "endpoints": [
            "/users (GET, POST)",
            "/users/{id} (GET, PUT, DELETE)"
        ]
    }
    
    with open(spec_path, "w", encoding="utf-8") as f:
        yaml.dump(spec_content, f, allow_unicode=True, sort_keys=False)
        
    console.print(f"[bold green]✅ 初始化成功！[/bold green] Spec 文件已生成至: {spec_path}")
    console.print("你可以手动修改该文件，然后运行 `autodev build` 开始生成代码。")

@app.command()
def build(
    spec_path: Path = typer.Argument(..., help="Spec 文件的路径"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="禁用人工审查，适配批量构建/CI"),
):
    """
    第二步：读取 Spec，启动多 Agent 工作流生成代码
    """
    if not spec_path.exists():
        console.print(f"[bold red]❌ 找不到文件: {spec_path}[/bold red]")
        raise typer.Exit(1)
        
    with open(spec_path, "r", encoding="utf-8") as f:
        try:
            raw_spec = yaml.safe_load(f)
            # Pydantic schema validation!
            validated_spec = ProjectSpec(**raw_spec)
            spec = validated_spec.model_dump()
        except ValidationError as e:
            console.print("[bold red]❌ Spec 文件格式不合法！[/bold red]")
            for err in e.errors():
                loc = " -> ".join([str(x) for x in err["loc"]])
                msg = err["msg"]
                console.print(f"  [yellow]- {loc}[/yellow]: {msg}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[bold red]❌ 解析 YAML 失败: {e}[/bold red]")
            raise typer.Exit(1)
        
    project_name = spec.get("project_name", "unknown_project")
    console.print(f"[bold cyan]🚀 启动 AutoDev 引擎，正在构建项目: {project_name}...[/bold cyan]")
    
    # 准备初始状态
    initial_state = {
        "project_name": project_name,
        "spec": spec,
        "artifacts": {},
        "architect_design": "",
        "run": {
            "errors": [],
            "qa": {"passed": False},
        },
    }
    init_run_controls(initial_state)
    initial_state["run"]["max_retries"] = int(spec.get("max_retries", initial_state["run"].get("max_retries", 3)))
    initial_state["run"]["non_interactive"] = bool(non_interactive)
    initial_state["run"]["human_review_enabled"] = (not non_interactive) and bool(spec.get("human_review_enabled", True))
    
    # 运行 LangGraph 工作流
    graph = build_graph()
    final_state = graph.invoke(initial_state)
    
    # 将生成的文件写入磁盘
    project_dir = WORKSPACE_DIR / project_name
    for file_path, content in final_state.get("artifacts", {}).items():
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    artifacts_index = []
    for file_path, content in final_state.get("artifacts", {}).items():
        if not isinstance(content, str):
            continue
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        artifacts_index.append({"path": file_path, "sha256": digest, "bytes": len(content.encode("utf-8"))})

    report = {
        "project_name": project_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": spec,
        "run": final_state.get("run", {}),
        "artifacts": artifacts_index,
    }

    report_path = project_dir / "build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            
    console.print(f"\n[bold green]🎉 项目 {project_name} 交付完成！[/bold green]")
    console.print(f"代码已保存至: {project_dir.absolute()}")

if __name__ == "__main__":
    app()
