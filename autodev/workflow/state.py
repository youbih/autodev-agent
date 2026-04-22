from typing import Any, Dict, TypedDict

class ProjectState(TypedDict, total=False):
    project_name: str
    spec: Dict[str, Any]
    artifacts: Dict[str, str]
    architect_design: str
    run: Dict[str, Any]