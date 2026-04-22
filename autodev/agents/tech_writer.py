import json

from rich.console import Console
from langchain_core.messages import SystemMessage, HumanMessage

from autodev.workflow.llm import get_llm
from autodev.workflow.state import ProjectState

console = Console()


def tech_writer_node(state: ProjectState) -> ProjectState:
    console.print("[bold magenta][TechWriter][/bold magenta] 正在阅读生成的代码，推导架构并生成专业的 README.md...")

    llm = get_llm()

    code_context = ""
    for file_path, content in state["files"].items():
        if file_path == "fixed":
            continue
        code_context += f"--- {file_path} ---\n```python\n{content}\n```\n\n"

    system_prompt = """你是一个高级技术文档工程师 (Technical Writer)。
开发团队刚刚为你提供了一个基于 FastAPI 编写的完整项目代码。
你的任务是阅读这些代码，然后编写一份极致专业的项目 `README.md` 文档。

要求 README 必须包含以下结构：
1. 项目名称与简介
2. 核心架构图 (Mermaid)，必须放在 ```mermaid 代码块里
3. 环境依赖与安装步骤
4. 快速启动命令
5. 接口说明与 curl 示例

只输出完整的 Markdown 文档，不要包含任何多余的废话。"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求 (Spec):\n{spec_str}\n\n这是开发团队生成的完整项目代码:\n{code_context}\n\n请你开始撰写 README.md！"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    state["readme_content"] = response.content
    state["files"]["README.md"] = response.content

    console.print("[bold magenta][TechWriter][/bold magenta] ✅ 专业文档生成完成！")
    return state