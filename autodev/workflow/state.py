from typing import TypedDict, Dict, List, Any

class ProjectState(TypedDict):
    """
    定义贯穿整个生成过程的状态数据
    """
    project_name: str
    spec: Dict[str, Any]          # 用户定义的需求配置
    architect_design: str         # 架构师的设计思路 (给 Coder 看的)
    human_feedback: str           # 老板(用户)的打回修改意见
    files: Dict[str, str]         # 生成的文件集合 {文件路径: 代码内容}
    errors: List[str]             # 运行测试时的报错信息 (用于后续自愈)
    test_passed: bool             # QA 验证是否通过
    readme_content: str           # 最终生成的 README