# tag_prompt_builder/utils.py
def make_tag_id(parent_id: str, name: str, sort_order: int) -> str:
    """统一的标签 ID 生成规则"""
    if parent_id == '#root':
        return f"#root/{name}#{sort_order}"
    return f"{parent_id}/{name}#{sort_order}"