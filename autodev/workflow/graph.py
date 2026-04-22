import json
from langgraph.graph import StateGraph, END
from autodev.workflow.state import ProjectState
from rich.console import Console
from langchain_core.prompts import ChatPromptTemplate
from autodev.workflow.llm import get_llm

console = Console()

# --- 真实的 Architect 节点 ---
def architect_node(state: ProjectState) -> ProjectState:
    console.print(f"[bold blue][Architect][/bold blue] 正在思考项目 '{state['project_name']}' 的系统架构...")
    
    llm = get_llm()
    
    # 1. 编写架构师的 System Prompt
    system_prompt = """你是一个资深的 Python 后端架构师。
你的任务是根据用户的项目需求 (Spec)，设计出合理的数据库模型 (SQLAlchemy) 和 API 数据结构 (Pydantic)。
请以纯文本的 Markdown 格式输出设计思路，并在其中包含且仅包含两段 Python 代码块：
1. 第一段代码块必须是 `models.py` (SQLAlchemy 结构)
2. 第二段代码块必须是 `schemas.py` (Pydantic 结构)

请保持代码规范，包含必要的字段，并加上详细的中文注释。"""

    user_prompt = "这是项目的需求配置 (Spec):\n{spec_json}"
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    # 2. 调用大模型
    chain = prompt_template | llm
    response = chain.invoke({"spec_json": json.dumps(state["spec"], ensure_ascii=False, indent=2)})
    
    design_content = response.content
    
    # 3. 解析大模型返回的代码块 (简单写一个提取 Markdown Python 代码块的逻辑)
    code_blocks = []
    lines = design_content.split('\n')
    in_block = False
    current_block = []
    
    for line in lines:
        if line.strip().startswith("```python"):
            in_block = True
            current_block = []
        elif line.strip().startswith("```") and in_block:
            in_block = False
            code_blocks.append('\n'.join(current_block))
        elif in_block:
            current_block.append(line)
            
    # 4. 把提取到的代码存入全局状态 (State)
    if len(code_blocks) >= 2:
        state["files"]["app/models.py"] = code_blocks[0]
        state["files"]["app/schemas.py"] = code_blocks[1]
        console.print("[bold blue][Architect][/bold blue] ✅ 数据库模型和数据结构设计完成！")
    else:
        console.print("[bold red][Architect] ❌ 架构师没有按格式输出两段代码块！[/bold red]")
        # 兜底：如果没有正确输出，就存一点假代码防止流程断掉
        state["files"]["app/models.py"] = "# LLM 解析失败，需重试"
        state["files"]["app/schemas.py"] = "# LLM 解析失败，需重试"

    # 把架构师的原始思考过程也存下来，以后可以写进 README
    state["architect_design"] = design_content
    
    return state

def coder_node(state: ProjectState) -> ProjectState:
    console.print("[bold green][Coder][/bold green] 正在编写 FastAPI 业务代码...")
    
    # 检查是否是从 QA 节点“打回”来修复的
    if "errors" in state and len(state["errors"]) > 0:
        console.print(f"[bold yellow][Coder][/bold yellow] 收到报错信息，正在尝试修复: {state['errors'][-1]}")
        # Mock: 假装修复了错误，关键是我们要把 errors 清空！
        state["errors"] = []
        # 给 QA 留个记号，告诉它我们修复过了
        state["files"]["fixed"] = "true" 
    
    # Mock: 生成业务代码
    state["files"]["app/main.py"] = "from fastapi import FastAPI\napp = FastAPI()"
    state["files"]["tests/test_api.py"] = "def test_ping(): assert True"
    
    return state

def qa_node(state: ProjectState) -> ProjectState:
    console.print("[bold red][QA][/bold red] 正在沙盒中安装依赖并运行 pytest...")
    
    # 核心修复逻辑：
    # 如果 files 里没有 "fixed" 标记，说明这是第一次运行，我们故意报错
    if "fixed" not in state.get("files", {}):
        console.print("[bold red][QA] ❌ 测试失败！发现 Pydantic schemas 导入错误。[/bold red]")
        state["errors"] = ["ImportError: cannot import name 'UserCreate' from 'app.schemas'"]
        state["test_passed"] = False
        return state
             
    # 如果有了 "fixed" 标记，说明 Coder 已经尝试修复过了，这次我们让它通过
    console.print("[bold green][QA] ✅ 测试全绿！代码验证通过。[/bold green]")
    state["test_passed"] = True
    return state




def tech_writer_node(state: ProjectState) -> ProjectState:
    console.print("[bold magenta][TechWriter][/bold magenta] 正在生成含 Mermaid 架构图的 README.md...")
    # Mock: 生成 README
    state["readme_content"] = f"# {state['project_name']}\n\n这是自动生成的后端项目。\n\n```mermaid\ngraph TD;\nAPI-->Service;\n```"
    state["files"]["README.md"] = state["readme_content"]
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