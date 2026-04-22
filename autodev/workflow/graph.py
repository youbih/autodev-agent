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
console = Console()

# --- 真实的 Architect 节点 ---
def architect_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold blue][Architect][/bold blue] 正在思考项目 '{state['project_name']}' 的系统架构...")
    
    architecture_type = str(state['spec'].get('architecture', '')).lower()
    if '单文件脚本' in architecture_type or 'script' in architecture_type:
        console.print("[bold blue][Architect][/bold blue] 检测到这是一个简单脚本项目，架构师无需设计复杂模型，直接交接给 Coder！")
        state["architect_design"] = "这是一个单文件 Python 脚本项目，不需要数据库设计，请在一个文件内完成所有逻辑。"
        return state
        
    llm = get_llm()
    system_prompt = """你是一个资深的 Python 后端架构师。
你的任务是根据用户的项目需求 (Spec)，设计出合理的数据库模型 (SQLAlchemy) 和 API 数据结构 (Pydantic)。
请以纯文本的 Markdown 格式输出设计思路，并在其中包含且仅包含两段 Python 代码块：
1. 第一段代码块必须是 `models.py` (SQLAlchemy 结构)
2. 第二段代码块必须是 `schemas.py` (Pydantic 结构)"""

    # 不再用 f-string 模板，直接转成 JSON 字符串拼接
    spec_str = json.dumps(state['spec'], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求配置 (Spec):\n{spec_str}"
    
    # 直接组装 Messages，绕开 ChatPromptTemplate
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    
    code_blocks = []
    lines = response.content.split('\n')
    in_block = False; current_block = []
    for line in lines:
        if line.strip().startswith("```python"): in_block = True; current_block = []
        elif line.strip().startswith("```") and in_block: in_block = False; code_blocks.append('\n'.join(current_block))
        elif in_block: current_block.append(line)
            
    if len(code_blocks) >= 2:
        state["files"]["app/models.py"] = code_blocks[0]
        state["files"]["app/schemas.py"] = code_blocks[1]
        console.print("[bold blue][Architect][/bold blue] ✅ 数据库模型和数据结构设计完成！")
    else:
        state["files"]["app/models.py"] = "# 需重试"
        state["files"]["app/schemas.py"] = "# 需重试"

    state["architect_design"] = response.content
    return state

def coder_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold green][Coder][/bold green] 正在为项目 '{state['project_name']}' 编写业务代码...")
    
    llm = get_llm()
    is_fixing = "errors" in state and len(state["errors"]) > 0
    
    architecture_type = str(state['spec'].get('architecture', '')).lower()
    
    if '单文件脚本' in architecture_type or 'script' in architecture_type:
        system_prompt = """你是一个全能的 Python 极客工程师。
用户的需求是一个纯命令行的 Python 脚本程序。绝对不要使用任何 Web 框架 (如 FastAPI) 或复杂的数据库 (如 SQLAlchemy)！
你需要将所有的逻辑完整地写在一个文件里。
请仅输出一段包含 `main.py` 完整代码的 Markdown Python 代码块。"""
    else:
        system_prompt = """你是一个高级 Python 后端工程师，擅长写 FastAPI 框架。
架构师已经为你设计好了 `models.py` (SQLAlchemy) 和 `schemas.py` (Pydantic)。
你的任务是编写 FastAPI 的入口文件 `main.py`，实现用户需求中的所有接口。
请仅输出一段包含 `main.py` 完整代码的 Markdown Python 代码块。"""

    spec_str = json.dumps(state['spec'], ensure_ascii=False, indent=2)
    user_prompt = f"这是用户的需求 (Spec):\n{spec_str}\n\n这是架构师的设计思路:\n{state.get('architect_design', '无')}\n\n请你编写 `main.py`。"

    if is_fixing:
        error_msg = state['errors'][-1]
        console.print(f"[bold yellow][Coder][/bold yellow] 收到报错反馈，正在尝试修复...")
        user_prompt += f"\n\n【警告】你之前写的代码报错了：\n{error_msg}\n请你仔细分析并提供修复后的完整 `main.py` 代码。"
        state["errors"] = []
        state["files"]["fixed"] = "true"
        
    # 直接组装 Messages，绕开 ChatPromptTemplate
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    
    lines = response.content.split('\n')
    in_block = False; current_block = []
    for line in lines:
        if line.strip().startswith("```python"): in_block = True; current_block = []
        elif line.strip().startswith("```") and in_block:
            in_block = False
            state["files"]["app/main.py"] = '\n'.join(current_block)
            break
        elif in_block: current_block.append(line)
            
    if "app/main.py" not in state["files"]:
        console.print("[bold red][Coder] ❌ 代码提取失败！[/bold red]")
    else:
        console.print("[bold green][Coder][/bold green] ✅ main.py 业务代码编写完成！")

    return state

def qa_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold red][QA][/bold red] 正在沙盒中执行真实的语法检查...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. 将 state["files"] 里生成的所有代码，真实地写入临时目录
        for file_path, content in state["files"].items():
            if file_path == "fixed": # 忽略标记位
                continue
            full_path = temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        # 2. 我们降级检查策略：只用 py_compile 检查主文件是否有基础语法错误，不进行 import
        # 因为 import 会受限于当前环境是否安装了 FastAPI 等依赖
        main_file = temp_path / "app/main.py"
        if not main_file.exists():
            state["test_passed"] = False
            state["errors"] = ["缺少 app/main.py 文件"]
            return state

        check_cmd = ["python", "-m", "py_compile", str(main_file)]
        
        console.print(f"[bold red][QA][/bold red] 执行语法检查: {' '.join(check_cmd)}")
        result = subprocess.run(
            check_cmd,
            cwd=str(temp_path),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_log = result.stderr.strip()
            if len(error_log) > 500:
                error_log = "..." + error_log[-500:]
                
            console.print(f"[bold red][QA] ❌ 真实运行报错！发现代码存在语法错误。[/bold red]")
            console.print(f"[dim]{error_log}[/dim]")
            
            state["errors"] = [f"语法检查失败:\n```text\n{error_log}\n```"]
            state["test_passed"] = False
            return state

    console.print("[bold green][QA] ✅ 真实环境验证全绿！代码语法正确。[/bold green]")
    state["test_passed"] = True
    return state

    # 如果 subprocess 返回 0，说明没有任何语法和导入错误
    console.print("[bold green][QA] ✅ 真实环境验证全绿！代码语法及依赖导入正确。[/bold green]")
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
def build_graph():
    workflow = StateGraph(ProjectState)
    
    # 1. 添加节点
    workflow.add_node("architect", architect_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("tech_writer", tech_writer_node)
    
    # 2. 定义流转边
    workflow.set_entry_point("architect")
    workflow.add_edge("architect", "coder")
    workflow.add_edge("coder", "qa")
    
    # QA 节点是条件路由 (Conditional Edge)
    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "coder": "coder",               # 返回重写
            "tech_writer": "tech_writer"    # 去写文档
        }
    )
    
    workflow.add_edge("tech_writer", END)
    
    return workflow.compile()