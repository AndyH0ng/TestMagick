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
