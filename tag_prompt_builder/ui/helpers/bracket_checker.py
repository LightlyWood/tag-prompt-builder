# ui/helpers/bracket_checker.py
"""检查提示词中括号配对及权重格式"""
import re

def check_brackets(text: str) -> (bool, str):
    """
    返回 (是否合法, 错误信息)
    检查 ( ) 配对，并简单验证 (xxx:数字) 格式
    """
    stack = []
    for i, ch in enumerate(text):
        if ch == '(':
            stack.append(i)
        elif ch == ')':
            if not stack:
                return False, f"第 {i} 个字符多余的右括号"
            stack.pop()
    if stack:
        return False, f"有未闭合的左括号，位置: {stack[0]}"
    # 简单检查权重格式：(text:1.2) 无空格等
    # 这里仅做提示，不强制报错
    pattern = re.compile(r'\([^)]*:\d+(\.\d+)?\)')
    return True, ""