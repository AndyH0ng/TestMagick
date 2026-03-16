import pytest

from testmagick.schema import ExamSet, GraphBlock, GraphEdge, GraphNode, TableBlock


def test_valid_examset_parses() -> None:
    exam = ExamSet.model_validate(
        {
            "title": "Sample",
            "problems": [
                {
                    "id": "Q1",
                    "type": "mcq",
                    "question": "2+2?",
                    "choices": ["3", "4", "5"],
                    "answer": 2,
                },
                {
                    "id": "Q2",
                    "type": "short",
                    "question": "Define vector space.",
                    "answer": "A set closed under addition and scalar multiplication.",
                },
            ],
        }
    )
    assert exam.problems[0].resolved_answer_text() == "4"
    assert exam.problems[0].resolved_answer_index() == 2


def test_mcq_typst_choices_with_index_answer() -> None:
    exam = ExamSet.model_validate(
        {
            "title": "Sample",
            "problems": [
                {
                    "id": "Q1",
                    "type": "mcq",
                    "question_typst": "Solve $x^2 = 4$.",
                    "choices_typst": ["$x=1$", "$x=2$"],
                    "answer": 2,
                }
            ],
        }
    )
    assert exam.problems[0].resolved_answer_index() == 2
    assert exam.problems[0].resolved_answer_text() == "$x=2$"


def test_short_accepts_answer_typst_only() -> None:
    exam = ExamSet.model_validate(
        {
            "title": "Sample",
            "problems": [
                {
                    "id": "Q1",
                    "type": "short",
                    "question": "Compute the integral.",
                    "answer_typst": "$1/3$",
                }
            ],
        }
    )
    assert exam.problems[0].resolved_answer_text() == "$1/3$"


def test_duplicate_problem_id_fails() -> None:
    try:
        ExamSet.model_validate(
            {
                "title": "Sample",
                "problems": [
                    {
                        "id": "Q1",
                        "type": "short",
                        "question": "A?",
                        "answer": "B",
                    },
                    {
                        "id": "Q1",
                        "type": "short",
                        "question": "C?",
                        "answer": "D",
                    },
                ],
            }
        )
    except Exception as exc:  # pragma: no cover - pydantic 내부 구현에 따라 달라질 수 있음
        assert "중복된 문제 ID가 있습니다: Q1" in str(exc)
    else:
        raise AssertionError("중복 ID 검증 오류가 발생해야 합니다.")


# ─── TableBlock 유효성 검사 ───────────────────────────────────────────────────

def test_table_block_valid_with_headers() -> None:
    block = TableBlock.model_validate({
        "type": "table",
        "headers": ["A", "B"],
        "rows": [["1", "2"], ["3", "4"]],
    })
    assert len(block.rows) == 2


def test_table_block_valid_no_headers() -> None:
    block = TableBlock.model_validate({
        "type": "table",
        "rows": [["x", "y"], ["1", "2"]],
    })
    assert block.headers is None


def test_table_block_empty_fails() -> None:
    with pytest.raises(Exception, match="headers 또는 최소 한 개의 rows"):
        TableBlock.model_validate({"type": "table"})


def test_table_block_mismatched_row_length_fails() -> None:
    with pytest.raises(Exception, match="열 수"):
        TableBlock.model_validate({
            "type": "table",
            "headers": ["A", "B", "C"],
            "rows": [["1", "2"]],
        })


# ─── GraphNode / GraphEdge 제약 ───────────────────────────────────────────────

def test_graph_node_empty_id_fails() -> None:
    with pytest.raises(Exception):
        GraphNode.model_validate({"id": "  ", "pos": [0, 0]})


def test_graph_edge_empty_from_fails() -> None:
    with pytest.raises(Exception):
        GraphEdge.model_validate({"from": "", "to": "B"})


def test_graph_edge_empty_to_fails() -> None:
    with pytest.raises(Exception):
        GraphEdge.model_validate({"from": "A", "to": "  "})


def test_graph_block_valid() -> None:
    block = GraphBlock.model_validate({
        "type": "graph",
        "nodes": [
            {"id": "A", "pos": [0, 0]},
            {"id": "B", "pos": [1, 0]},
        ],
        "edges": [{"from": "A", "to": "B", "label": "$w$"}],
    })
    assert block.edges[0].label == "$w$"


def test_graph_block_invalid_edge_ref_fails() -> None:
    with pytest.raises(Exception, match="nodes에 없습니다"):
        GraphBlock.model_validate({
            "type": "graph",
            "nodes": [{"id": "A", "pos": [0, 0]}],
            "edges": [{"from": "A", "to": "Z"}],
        })


# ─── MCQ + answer_typst (schema 허용 확인) ────────────────────────────────────

def test_mcq_subproblem_with_answer_typst() -> None:
    exam = ExamSet.model_validate({
        "title": "T",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "참/거짓을 판단하고 설명하라.",
            "subproblems": [{
                "id": "(a)",
                "type": "mcq",
                "question": "명제가 참인가?",
                "choices": ["참", "거짓"],
                "answer": 2,
                "answer_typst": "거짓이다. 반례: ...",
            }],
        }],
    })
    sub = exam.problems[0].subproblems[0]  # type: ignore[index]
    assert sub.answer_typst == "거짓이다. 반례: ..."


def test_mcq_problem_with_answer_typst() -> None:
    exam = ExamSet.model_validate({
        "title": "T",
        "problems": [{
            "id": "Q1",
            "type": "mcq",
            "question": "다음 중 옳은 것은?",
            "choices": ["A", "B", "C"],
            "answer": 1,
            "answer_typst": "A가 옳다. 이유: ...",
        }],
    })
    assert exam.problems[0].answer_typst == "A가 옳다. 이유: ..."
