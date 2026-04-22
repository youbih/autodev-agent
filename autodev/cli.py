import typer
import yaml
import os
from pathlib import Path
from rich.console import Console
from autodev.workflow.graph import build_graph

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
def build(spec_path: Path = typer.Argument(..., help="Spec 文件的路径")):
    """
    第二步：读取 Spec，启动多 Agent 工作流生成代码
    """
    if not spec_path.exists():
        console.print(f"[bold red]❌ 找不到文件: {spec_path}[/bold red]")
        raise typer.Exit(1)
        
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
        
    project_name = spec.get("project_name", "unknown_project")
    console.print(f"[bold cyan]🚀 启动 AutoDev 引擎，正在构建项目: {project_name}...[/bold cyan]")
    
    # 准备初始状态
    initial_state = {
        "project_name": project_name,
        "spec": spec,
        "files": {},
        "errors": [],
        "test_passed": False,
        "readme_content": ""
    }
    
    # 运行 LangGraph 工作流
    graph = build_graph()
    final_state = graph.invoke(initial_state)
    
    # 将生成的文件写入磁盘
    project_dir = WORKSPACE_DIR / project_name
    for file_path, content in final_state["files"].items():
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    console.print(f"\n[bold green]🎉 项目 {project_name} 交付完成！[/bold green]")
    console.print(f"代码已保存至: {project_dir.absolute()}")

if __name__ == "__main__":
    app()