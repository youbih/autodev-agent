import json
from langgraph.graph import StateGraph, END
from autodev.workflow.state import ProjectState
from rich.console import Console
from langchain_core.prompts import ChatPromptTemplate
from autodev.workflow.llm import get_llm
import subprocess
import os
import tempfile
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
import docker
from docker.errors import ContainerError, ImageNotFound, APIError
import sys
import autodev.workflow.graph as g
console = Console()

# 获取当前工作目录（你运行命令的那个目录，即 autodev_project）
PROJECT_ROOT = Path(os.getcwd()).absolute()

# 全部使用绝对路径！
QA_ROOT = PROJECT_ROOT / ".autodev"
QA_VENV = QA_ROOT / "qa_venv"
QA_MARKER = QA_ROOT / ".deps_installed"
PIP_CACHE = QA_ROOT / "pip_cache"
QA_DEPS = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]

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

# --- 真实的 Architect 节点 ---
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

def human_review_node(state: ProjectState) -> ProjectState:
    # 只有非简单脚本（也就是有架构设计输出的），才需要审查
    architecture_type = str(state['spec'].get('architecture', '')).lower()
    if '单文件脚本' in architecture_type or 'script' in architecture_type:
        return state
        
    console.print("\n[bold cyan]================ 👨‍💻 人工审查环节 =================[/bold cyan]")
    console.print(f"[dim]{state.get('architect_design', '无设计稿')}[/dim]")
    console.print("[bold cyan]==================================================[/bold cyan]")
    
    # 暂停程序的执行，等待用户在终端输入
    feedback = console.input("[bold yellow]架构设计是否通过？(输入 'y' 或直接回车同意，输入具体的修改意见让架构师重做): [/bold yellow]")
    
    if feedback.strip().lower() in ['y', 'yes', 'ok', '']:
        state["human_feedback"] = ""  # 同意放行
    else:
        state["human_feedback"] = feedback  # 记录意见，准备打回
        
    return state


def coder_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold green][Coder][/bold green] 正在为项目 '{state['project_name']}' 编写业务代码...")

    llm = get_llm()
    is_fixing = "errors" in state and len(state["errors"]) > 0

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
- 请仅输出一段包含 `main.py` 完整代码的 Markdown Python 代码块。"""
    else:
        system_prompt = """你是一个高级 Python 后端工程师，擅长写 FastAPI 框架。
架构师已经为你设计好了 `models.py` (SQLAlchemy) 和 `schemas.py` (Pydantic)。
你的任务是编写 FastAPI 的入口文件 `main.py`，实现用户需求中的所有接口。

【导入规范（必须遵守）】
- 项目内模块必须使用包导入：from app.xxx import ... 或 from app import xxx
- 严禁使用裸导入：import models / import schemas / import database
- 除标准库/第三方库外，main.py 中所有本地模块导入必须以 app. 开头（例如 from app.models import User）

【数据库模块约定（必须遵守）】
- 数据库连接模块固定为 app/database.py
- 如需使用 SessionLocal/engine，必须写：from app.database import SessionLocal, engine
- 禁止使用 app.core.database 或其他路径（比如 from app.core.database ... / from database ... 都不允许）

输出要求：
- 请仅输出一段包含 `main.py` 完整代码的 Markdown Python 代码块。"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = (
        f"这是用户的需求 (Spec):\n{spec_str}\n\n"
        f"这是架构师的设计思路:\n{state.get('architect_design', '无')}\n\n"
        "请你编写 `main.py`。"
    )

    if is_fixing:
        error_msg = state["errors"][-1]
        console.print("[bold yellow][Coder][/bold yellow] 收到报错反馈，正在尝试修复...")
        user_prompt += (
            f"\n\n【警告】你之前写的代码报错了：\n{error_msg}\n"
            "请你仔细分析并提供修复后的完整 `main.py` 代码。"
        )
        state["errors"] = []
        state["files"]["fixed"] = "true"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    lines = response.content.split("\n")
    in_block = False
    current_block = []
    for line in lines:
        if line.strip().startswith("```python"):
            in_block = True
            current_block = []
        elif line.strip().startswith("```") and in_block:
            in_block = False
            state["files"]["app/main.py"] = "\n".join(current_block)
            break
        elif in_block:
            current_block.append(line)

    if "app/main.py" not in state["files"]:
        console.print("[bold red][Coder] ❌ 代码提取失败！[/bold red]")
    else:
        console.print("[bold green][Coder][/bold green] ✅ main.py 业务代码编写完成！")

    return state

def qa_node(state: ProjectState) -> ProjectState:
    console.print("[bold red][QA][/bold red] 使用缓存 venv 执行隔离验证...")

    qa_python = ensure_qa_venv()
    console.print(f"[bold red][QA][/bold red] 使用的解释器: {qa_python}")
    console.print(f"[QA] graph.py 路径: {g.__file__}")
    console.print(f"[QA] QA_VENV: {QA_VENV}")
    console.print(f"[QA] qa_python: {qa_python}")
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




def tech_writer_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold magenta][TechWriter][/bold magenta] 正在阅读生成的代码，推导架构并生成专业的 README.md...")
    
    llm = get_llm()
    
    # 1. 准备大模型阅读的“代码库”上下文
    code_context = ""
    for file_path, content in state["files"].items():
        if file_path == "fixed": continue
        code_context += f"--- {file_path} ---\n```python\n{content}\n```\n\n"
        
    # 2. 编写文档工程师的 System Prompt
    system_prompt = """你是一个高级技术文档工程师 (Technical Writer)。
开发团队刚刚为你提供了一个基于 FastAPI 编写的完整项目代码。
你的任务是阅读这些代码，然后编写一份极致专业的项目 `README.md` 文档。

要求 README 必须包含以下结构：
1. **项目名称与简介** (从 Spec 中提取)
2. **核心架构图 (Mermaid)**: 根据你阅读的 models, schemas, main.py 逻辑，使用 mermaid 的 graph TD 语法画出组件交互图或 ER 模型图。必须把 mermaid 放在 ```mermaid 代码块里。
3. **环境依赖**: 明确列出如何创建虚拟环境，以及需要安装的依赖 (如 fastapi, uvicorn, sqlalchemy 等)。
4. **快速启动**: 写出启动 uvicorn 服务的具体命令。
5. **接口说明**: 列出主要的 API 路由 (Endpoints) 及对应的 curl 测试命令。

只输出完整的 Markdown 文档，不要包含任何多余的废话。"""

    # 这里我们不用 f-string template，直接拼好最终的字符串
    spec_str = json.dumps(state['spec'], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求 (Spec):\n{spec_str}\n\n这是开发团队生成的完整项目代码:\n{code_context}\n\n请你开始撰写 README.md！"

    # 3. 手动构建消息列表（避免 LangChain 的模板花括号解析冲突）
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # 4. 调用大模型
    response = llm.invoke(messages)
    
    # 5. 把大模型生成的文档保存下来
    state["readme_content"] = response.content
    state["files"]["README.md"] = response.content
    
    console.print("[bold magenta][TechWriter][/bold magenta] ✅ 专业文档生成完成！")
    
    return state

# --- 边定义 (Routing Logic) ---

def route_after_qa(state: ProjectState) -> str:
    """QA 运行完后决定下一步去哪：报错就回 Coder 修复，通过就去写文档"""
    if not state.get("test_passed", False):
        return "coder" # 修复循环
    return "tech_writer"

# --- 构建图 ---
def route_after_review(state: ProjectState) -> str:
    """如果有人类意见，就打回给 architect；否则放行给 coder"""
    if state.get("human_feedback"):
        return "architect"
    return "coder"

def build_graph():
    workflow = StateGraph(ProjectState)
    
    # 添加节点
    workflow.add_node("architect", architect_node)
    workflow.add_node("human_review", human_review_node)  # <--- 增加新节点
    workflow.add_node("coder", coder_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("tech_writer", tech_writer_node)
    
    # 连线
    workflow.set_entry_point("architect")
    workflow.add_edge("architect", "human_review")        # Architect 完事后，先给人看
    
    # 人类看完后，条件路由
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "architect": "architect",  # 打回重做
            "coder": "coder"           # 同意放行
        }
    )
    
    workflow.add_edge("coder", "qa")
    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "coder": "coder",
            "tech_writer": "tech_writer"
        }
    )
    workflow.add_edge("tech_writer", END)
    
    return workflow.compile()