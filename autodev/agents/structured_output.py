import json
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage


def _strip_code_fences(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def invoke_json(
    llm: Any,
    *,
    system_prompt: str,
    user_prompt: str,
    max_attempts: int = 3,
    extra_messages: Optional[List[Any]] = None,
) -> Tuple[Dict[str, Any], str]:
    messages: List[Any] = [SystemMessage(content=system_prompt)]
    if extra_messages:
        messages.extend(extra_messages)
    messages.append(HumanMessage(content=user_prompt))

    last_text = ""
    for i in range(max_attempts):
        resp = llm.invoke(messages)
        last_text = getattr(resp, "content", "") or ""
        candidate = _strip_code_fences(last_text)
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj, last_text
        except Exception as e:
            err = str(e)
            messages.append(
                HumanMessage(
                    content=(
                        "你的上一条输出不是合法 JSON。\n"
                        f"错误信息：{err}\n"
                        "请你重新输出，只能输出一个 JSON 对象，不要 Markdown，不要代码块，不要任何额外文本。"
                    )
                )
            )

        if i == max_attempts - 1:
            break

    return {}, last_text