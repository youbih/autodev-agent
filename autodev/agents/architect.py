import json

from rich.console import Console
from langchain_core.messages import SystemMessage, HumanMessage

from autodev.workflow.llm import get_llm
from autodev.workflow.state import ProjectState

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
请以纯文本的 Markdown 格式输出设计思路，并在其中包含且仅包含两段 Python 代码块：
1. 第一段代码块必须是 `models.py` (SQLAlchemy 结构)
2. 第二段代码块必须是 `schemas.py` (Pydantic 结构)"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求配置 (Spec):\n{spec_str}"

    if state.get("human_feedback"):
        console.print(f"[bold yellow][Architect][/bold yellow] 收到老板的修改意见：'{state['human_feedback']}'，正在重做架构设计...")
        user_prompt += (
            f"\n\n【重要】用户对你上次的设计提出了修改意见：\n{state['human_feedback']}\n"
            "请你反思上次的设计，并严格根据意见重新输出设计思路和完整的代码块！"
        )
        state["human_feedback"] = ""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    code_blocks = []
    lines = response.content.split("\n")
    in_block = False
    current_block = []
    for line in lines:
        if line.strip().startswith("```python"):
            in_block = True
            current_block = []
        elif line.strip().startswith("```") and in_block:
            in_block = False
            code_blocks.append("\n".join(current_block))
        elif in_block:
            current_block.append(line)

    if len(code_blocks) >= 2:
        state["files"]["app/models.py"] = code_blocks[0]
        state["files"]["app/schemas.py"] = code_blocks[1]
        console.print("[bold blue][Architect][/bold blue] ✅ 数据库模型和数据结构设计完成！")
    else:
        state["files"]["app/models.py"] = "# 需重试"
        state["files"]["app/schemas.py"] = "# 需重试"

    state["architect_design"] = response.content

    if "app/database.py" not in state["files"]:
        state["files"]["app/database.py"] = """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
"""

    return state