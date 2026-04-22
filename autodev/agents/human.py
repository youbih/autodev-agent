from rich.console import Console

from autodev.workflow.state import ProjectState

console = Console()


def human_review_node(state: ProjectState) -> ProjectState:
    architecture_type = str(state["spec"].get("architecture", "")).lower()
    if "单文件脚本" in architecture_type or "script" in architecture_type:
        return state

    console.print("\n[bold cyan]================ 👨‍💻 人工审查环节 =================[/bold cyan]")
    console.print(f"[dim]{state.get('architect_design', '无设计稿')}[/dim]")
    console.print("[bold cyan]==================================================[/bold cyan]")

    feedback = console.input("[bold yellow]架构设计是否通过？(输入 'y' 或直接回车同意，输入具体的修改意见让架构师重做): [/bold yellow]")

    if feedback.strip().lower() in ["y", "yes", "ok", ""]:
        state["human_feedback"] = ""
    else:
        state["human_feedback"] = feedback

    return state


def route_after_review(state: ProjectState) -> str:
    if state.get("human_feedback"):
        return "architect"
    return "coder"