import json

from rich.console import Console

from autodev.workflow.llm import get_llm
from autodev.workflow.state import ProjectState
from autodev.agents.structured_output import invoke_json
from autodev.agents.failure_control import record_failure

console = Console()


def tech_writer_node(state: ProjectState) -> ProjectState:
    console.print("[bold magenta][TechWriter][/bold magenta] 正在阅读生成的代码，推导架构并生成专业的 README.md...")

    llm = get_llm()
    run = state.setdefault("run", {})
    artifacts = state.setdefault("artifacts", {})

    code_context = ""
    for file_path, content in artifacts.items():
        code_context += f"--- {file_path} ---\n```python\n{content}\n```\n\n"

    system_prompt = """你是一个高级技术文档工程师 (Technical Writer)。
开发团队刚刚为你提供了一个完整的项目代码。
你的任务是阅读这些代码，然后编写一份极致专业的项目 `README.md` 文档，并生成一份对应的 `requirements.txt`。

要求 README 必须包含以下结构：
1. 项目名称与简介
2. 核心架构图 (Mermaid)，必须放在 ```mermaid 代码块里（如果是单文件脚本可省略此项）
3. 环境依赖与安装步骤
4. 快速启动命令
5. 接口说明与 curl 示例（如果是脚本则提供运行示例）

要求 requirements.txt：
1. 包含项目中所有导入的第三方依赖（如 fastapi, uvicorn, sqlalchemy, pydantic 等）。
2. 每行一个依赖包。

你必须只输出一个严格 JSON 对象，不能输出 Markdown、不能输出代码块标记、不能输出任何额外文本。

JSON 格式必须为：
{
  "files": {
    "README.md": "完整 Markdown 文档",
    "requirements.txt": "完整的依赖声明文件"
  },
  "summary": "一句话摘要"
}"""

    spec_str = json.dumps(state["spec"], ensure_ascii=False, indent=2)
    user_prompt = f"这是项目的需求 (Spec):\n{spec_str}\n\n这是开发团队生成的完整项目代码:\n{code_context}\n\n请你开始撰写 README.md！"

    parsed, raw_text = invoke_json(llm, system_prompt=system_prompt, user_prompt=user_prompt, max_attempts=3)
    files = parsed.get("files") if isinstance(parsed, dict) else None
    
    readme = None
    reqs = None
    if isinstance(files, dict):
        readme = files.get("README.md")
        reqs = files.get("requirements.txt")
        
    run.setdefault("agent_summaries", {})["tech_writer"] = str(parsed.get("summary") or "")

    if isinstance(readme, str) and readme.strip():
        run["readme_content"] = readme
        artifacts["README.md"] = readme
    else:
        run["readme_content"] = raw_text
        artifacts["README.md"] = raw_text
        record_failure(state, step="tech_writer", reason="invalid_json_or_missing_readme", detail=raw_text)

    if isinstance(reqs, str) and reqs.strip():
        artifacts["requirements.txt"] = reqs

    console.print("[bold magenta][TechWriter][/bold magenta] ✅ 专业文档生成完成！")
    return state