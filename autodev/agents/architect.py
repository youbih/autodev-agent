import json

from rich.console import Console

from autodev.workflow.llm import get_llm
from autodev.workflow.state import ProjectState
from autodev.agents.structured_output import invoke_json
from autodev.agents.failure_control import record_failure

console = Console()


def architect_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold blue][Architect][/bold blue] 正在思考项目 '{state['project_name']}' 的系统架构...")

    architecture_type = str(state["spec"].get("architecture", "")).lower()
    if "单文件脚本" in architecture_type or "script" in architecture_type:
        console.print("[bold blue][Architect][/bold blue] 检测到这是一个简单脚本项目，架构师无需设计复杂模型，直接交接给 Coder！")
        state["architect_design"] = "这是一个单文件 Python 脚本项目，不需要数据库设计，请在一个文件内完成所有逻辑。"
        return state

    llm = get_llm()
    system_prompt = """你是一个资深的 Python 后端架构师。
你的任务是根据用户的项目需求 (Spec)，设计出合理的数据库模型 (SQLAlchemy) 和 API 数据结构 (Pydantic)。
你必须只输出一个严格 JSON 对象，不能输出 Markdown、不能输出代码块标记、不能输出任何额外文本。

JSON 格式必须为：
{
  "design": "你的设计说明（可用 Markdown 字符串）",
  "files": {
    "app/models.py": "完整源码",
    "app/schemas.py": "完整源码",
    "app/database.py": "完整源码（如需要，SQLite + SQLAlchemy SessionLocal）"
  },
  "summary": "一句话摘要"
}"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求配置 (Spec):\n{spec_str}"

    run = state.setdefault("run", {})
    artifacts = state.setdefault("artifacts", {})

    human_feedback = run.get("human_feedback")
    if human_feedback:
        console.print(f"[bold yellow][Architect][/bold yellow] 收到老板的修改意见：'{human_feedback}'，正在重做架构设计...")
        user_prompt += (
            f"\n\n【重要】用户对你上次的设计提出了修改意见：\n{human_feedback}\n"
            "请你反思上次的设计，并严格根据意见重新输出设计思路和完整的代码块！"
        )
        run["human_feedback"] = ""

    parsed, raw_text = invoke_json(llm, system_prompt=system_prompt, user_prompt=user_prompt, max_attempts=3)
    files = parsed.get("files") if isinstance(parsed, dict) else None
    if isinstance(files, dict):
        for p, c in files.items():
            if isinstance(p, str) and isinstance(c, str):
                artifacts[p] = c
        console.print("[bold blue][Architect][/bold blue] ✅ 数据库模型和数据结构设计完成！")
    else:
        artifacts["app/models.py"] = "# 需重试"
        artifacts["app/schemas.py"] = "# 需重试"
        record_failure(state, step="architect", reason="invalid_json_or_missing_files", detail=raw_text)

    state["architect_design"] = str(parsed.get("design") or raw_text or "")
    run.setdefault("agent_summaries", {})["architect"] = str(parsed.get("summary") or "")

    if "app/database.py" not in artifacts:
        artifacts["app/database.py"] = """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
"""

    return state