from app.graph.nodes.rag import _strip_context_tags


def test_strips_context_tags_from_both_ends():
    raw = "<context>There are three steps in the complaint procedure.</context>"
    assert _strip_context_tags(raw) == "There are three steps in the complaint procedure."


def test_leaves_ordinary_text_unchanged():
    clean = "Performance reviews happen annually (Employee Handbook, p. 4)."
    assert _strip_context_tags(clean) == clean


def test_is_case_insensitive_and_handles_stray_tags_anywhere():
    raw = "<Context>Some answer</Context> extra <context>more"
    assert "<" not in _strip_context_tags(raw)
    assert ">" not in _strip_context_tags(raw)
