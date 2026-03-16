from pathlib import Path

from testmagick.renderer import render_typst_files
from testmagick.schema import ExamSet


def test_render_typst_files(tmp_path: Path) -> None:
    exam = ExamSet.model_validate(
        {
            "title": "Rendered",
            "problems": [
                {
                    "id": "Q1",
                    "type": "mcq",
                    "question": "Select one.",
                    "choices": ["A", "B"],
                    "answer": 1,
                    "points": 1,
                }
            ],
        }
    )

    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)

    assert rendered.exam_typ.exists()
    assert rendered.answer_typ.exists()
    assert "Select one." in rendered.exam_typ.read_text(encoding="utf-8")
    assert "정답:" in rendered.answer_typ.read_text(encoding="utf-8")


def test_render_typst_passthrough_fields(tmp_path: Path) -> None:
    exam = ExamSet.model_validate(
        {
            "title": "Rendered",
            "problems": [
                {
                    "id": "Q1",
                    "type": "mcq",
                    "question_typst": "Solve $x^2 = 4$.",
                    "choices_typst": ["$x=1$", "$x=2$"],
                    "answer": 2,
                    "points": 1,
                },
                {
                    "id": "Q2",
                    "type": "short",
                    "question_typst": '#raw(block: true, lang: "python", "print(1)")',
                    "answer_typst": "$1$",
                },
            ],
        }
    )

    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    answer_typ = rendered.answer_typ.read_text(encoding="utf-8")

    assert "Solve $x^2 = 4$." in exam_typ
    assert '#raw(block: true, lang: "python", "print(1)")' in exam_typ
    assert "$x=2$" in answer_typ
    assert "$1$" in answer_typ


def test_render_question_blocks(tmp_path: Path) -> None:
    exam = ExamSet.model_validate({
        "title": "Blocks",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "다음을 보고 답하라.",
            "question_blocks": [
                {"type": "formula", "content": "x^2 + y^2 = 1"},
                {"type": "requirements", "content": "단, x > 0"},
                {"type": "table", "headers": ["x", "y"], "rows": [["1", "0"], ["0", "1"]]},
            ],
            "answer": "원",
        }],
    })
    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    assert "x^2 + y^2 = 1" in exam_typ
    assert "x > 0" in exam_typ
    assert '"x"' in exam_typ  # table header


def test_render_subproblems(tmp_path: Path) -> None:
    exam = ExamSet.model_validate({
        "title": "Sub",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "참/거짓을 판단하라.",
            "subproblems": [
                {
                    "id": "(a)",
                    "type": "mcq",
                    "question": "1+1=2인가?",
                    "choices": ["참", "거짓"],
                    "answer": 1,
                    "answer_typst": "참이다.",
                },
                {
                    "id": "(b)",
                    "type": "short",
                    "question": "2+2는?",
                    "answer": "4",
                },
            ],
        }],
    })
    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    answer_typ = rendered.answer_typ.read_text(encoding="utf-8")
    assert "(a)" in exam_typ
    assert "(b)" in exam_typ
    assert "참이다." in answer_typ
    assert "정답:" in answer_typ


def test_render_graph_block(tmp_path: Path) -> None:
    exam = ExamSet.model_validate({
        "title": "Graph",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "그래프를 보고 답하라.",
            "question_blocks": [{
                "type": "graph",
                "nodes": [
                    {"id": "A", "pos": [0, 0]},
                    {"id": "B", "pos": [2, 0]},
                ],
                "edges": [{"from": "A", "to": "B", "label": "$w$"}],
            }],
            "answer": "연결됨",
        }],
    })
    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    assert '"A"' in exam_typ
    assert '"B"' in exam_typ
    assert "$w$" in exam_typ  # edge label rendered
