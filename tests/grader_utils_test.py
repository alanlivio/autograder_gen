from autograder_gen.grader_utils import normalize, StudentMessage, StudentMessageStr


def test_normalize_function():
    assert normalize("hello  \r\nworld   \r\n") == "hello\nworld"
    assert normalize("  \n  test  \t  \n \n ") == "  test"
    assert normalize("hello\n\nworld") == "hello\n\nworld"
    assert normalize("hello\n   \nworld") == "hello\n\nworld"
    assert normalize("\n\nhello\n\nworld\n\n") == "hello\n\nworld"
    assert normalize("hello\nworld   ") == "hello\nworld"
    assert normalize(None) == ""
    assert normalize("") == ""


def test_normalize_strips_leading_and_trailing_empty_lines():
    assert normalize("\nhello\nworld") == "hello\nworld"
    assert normalize("\n\n\nhello\nworld") == "hello\nworld"
    assert normalize("   \n \t \nhello\nworld") == "hello\nworld"
    assert normalize("hello\nworld\n") == "hello\nworld"
    assert normalize("hello\nworld\n\n\n") == "hello\nworld"
    assert normalize("hello\nworld\n   \n \t ") == "hello\nworld"
    assert normalize("\n\nhello\nworld\n\n") == "hello\nworld"


def test_normalize_removes_trailing_characters_on_last_line():
    assert normalize("hello\nworld   ") == "hello\nworld"
    assert normalize("hello\nworld\t  ") == "hello\nworld"
    assert normalize("single line   ") == "single line"
    assert normalize("single line \t \t ") == "single line"


def test_normalize_preserves_internal_empty_lines_and_indentation():
    assert normalize("first\n\nsecond") == "first\n\nsecond"
    assert normalize("first\n\n\nsecond") == "first\n\n\nsecond"
    assert normalize("first\n   \nsecond") == "first\n\nsecond"
    assert normalize("  def foo():\n      return 42") == "  def foo():\n      return 42"
    assert normalize("\n\n  def foo():\n\n      return 42\n\n") == "  def foo():\n\n      return 42"


def test_normalize_whitespace_only_strings():
    assert normalize("   ") == ""
    assert normalize("\n\n\n") == ""
    assert normalize("  \n \t \n  ") == ""
