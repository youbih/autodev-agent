import json

from rich.console import Console

from autodev.workflow.llm import get_llm
from autodev.workflow.state import ProjectState
from autodev.agents.structured_output import invoke_json
from autodev.agents.failure_control import record_failure

console = Console()


def coder_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold green][Coder][/bold green] 正在为项目 '{state['project_name']}' 编写业务代码...")

    llm = get_llm()
    run = state.setdefault("run", {})
    artifacts = state.setdefault("artifacts", {})
    errors = run.get("errors") or []
    is_fixing = len(errors) > 0

    architecture_type = str(state["spec"].get("architecture", "")).lower()

    if "单文件脚本" in architecture_type or "script" in architecture_type:
        system_prompt = """你是一个全能的 Python 极客工程师。
用户的需求是一个纯命令行的 Python 脚本程序。绝对不要使用任何 Web 框架 (如 FastAPI) 或复杂的数据库 (如 SQLAlchemy)！
你需要将所有的逻辑完整地写在一个文件里。

要求：
- 仅使用 Python 标准库
- 使用 input()/print() 进行交互
- 提供清晰的中文提示与必要的异常处理（输入校验等）

输出要求：
- 你必须只输出一个严格 JSON 对象，不能输出 Markdown、不能输出代码块标记、不能输出任何额外文本。
- JSON 格式必须为：{"files": {"app/main.py": "完整源码"}, "summary": "一句话摘要"}"""
    else:
        system_prompt = """你是一个高级 Python 后端工程师，擅长写 FastAPI 框架。
架构师已经为你设计好了 `models.py` (SQLAlchemy) 和 `schemas.py` (Pydantic)。
你的任务是编写 FastAPI 的入口文件 `main.py`，实现用户需求中的所有接口。

【运行约定（必须遵守）】
- main.py 必须暴露 FastAPI 实例变量名：app（即 app = FastAPI()）

【导入规范（必须遵守）】
- 项目内模块必须使用包导入：from app.xxx import ... 或 from app import xxx
- 严禁使用裸导入：import models / import schemas / import database
- 除标准库/第三方库外，main.py 中所有本地模块导入必须以 app. 开头（例如 from app.models import User）

【数据库模块约定（必须遵守）】
- 数据库连接模块固定为 app/database.py
- 如需使用 SessionLocal/engine，必须写：from app.database import SessionLocal, engine
- 禁止使用 app.core.database 或其他路径（比如 from app.core.database ... / from database ... 都不允许）

输出要求：
- 你必须只输出一个严格 JSON 对象，不能输出 Markdown、不能输出代码块标记、不能输出任何额外文本。
- JSON 格式必须为：{"files": {"app/main.py": "完整源码"}, "summary": "一句话摘要"}"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = (
        f"这是用户的需求 (Spec):\n{spec_str}\n\n"
        f"这是架构师的设计思路:\n{state.get('architect_design', '无')}\n\n"
        "请你编写 `main.py`。"
    )

    if is_fixing:
        error_msg = errors[-1]
        console.print("[bold yellow][Coder][/bold yellow] 收到报错反馈，正在尝试修复...")
        user_prompt += (
            f"\n\n【警告】你之前写的代码报错了：\n{error_msg}\n"
            "请你仔细分析并提供修复后的完整 `main.py` 代码。"
        )
        run["errors"] = []
        run.setdefault("flags", {})["fixed"] = True

    parsed, raw_text = invoke_json(llm, system_prompt=system_prompt, user_prompt=user_prompt, max_attempts=3)
    files = parsed.get("files") if isinstance(parsed, dict) else None
    if isinstance(files, dict):
        for p, c in files.items():
            if isinstance(p, str) and isinstance(c, str):
                artifacts[p] = c
    run.setdefault("agent_summaries", {})["coder"] = str(parsed.get("summary") or "")

    if "app/main.py" not in artifacts:
        console.print("[bold red][Coder] ❌ 代码提取失败！[/bold red]")
        run.setdefault("errors", [])
        run["errors"].append(f"Coder JSON 输出解析失败:\n```text\n{raw_text}\n```")
        record_failure(state, step="coder", reason="invalid_json_or_missing_main", detail=raw_text)
    else:
        console.print("[bold green][Coder][/bold green] ✅ main.py 业务代码编写完成！")

    return state