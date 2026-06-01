# tests/test_utils.py
from tag_prompt_builder.ui.helpers.bracket_checker import check_brackets

def test_valid_brackets():
    valid, msg = check_brackets("(masterpiece:1.2)")
    assert valid is True
    assert msg == ""

def test_missing_left():
    valid, msg = check_brackets("text)")
    assert valid is False
    assert "多余的右括号" in msg

def test_unclosed_left():
    valid, msg = check_brackets("(text")
    assert valid is False
    assert "未闭合的左括号" in msg

def test_nested():
    valid, msg = check_brackets("((nested))")
    assert valid is True