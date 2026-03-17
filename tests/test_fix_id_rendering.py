from pathlib import Path

from testmagick.renderer import render_typst_files
from testmagick.schema import ExamSet

def test_render_subproblem_redundant_id_and_quotes(tmp_path: Path) -> None:
    exam = ExamSet.model_validate({
        "title": "SubRedundant",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "판단하라.",
            "subproblems": [
                {
                    "id": "(a)",
                    "type": "short",
                    "question": "(a) 이원 일차방정식...",
                    "answer": "참",
                },
                {
                    "id": "(b)",
                    "type": "short",
                    "question_typst": "(b) $x=y$",
                    "answer_typst": "참",
                },
            ],
        }],
    })
    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    
    # 1. Check for quote fix: it should be text(weight: "bold")[#"(a)"]
    assert 'text(weight: "bold")[#"(a)"]' in exam_typ
    
    # 2. Check for redundant ID stripping in plain question
    assert '#"이원 일차방정식..."' in exam_typ
    assert '#"(a) 이원 일차방정식..."' not in exam_typ

    # 3. Check for redundant ID stripping in question_typst
    assert '$x=y$' in exam_typ
    assert '(b) $x=y$' not in exam_typ

def test_render_subproblem_exact_id_match(tmp_path: Path) -> None:
    exam = ExamSet.model_validate({
        "title": "SubExact",
        "problems": [{
            "id": "Q1",
            "type": "short",
            "question": "판단하라.",
            "subproblems": [
                {
                    "id": "(a)",
                    "type": "short",
                    "question": "(a)",
                    "answer": "참",
                },
                {
                    "id": "(b)",
                    "type": "short",
                    "question_typst": "(b)",
                    "answer_typst": "참",
                },
            ],
        }],
    })
    rendered = render_typst_files(exam_set=exam, out_dir=tmp_path)
    exam_typ = rendered.exam_typ.read_text(encoding="utf-8")
    # print(exam_typ) # debug
    
    # Check for quote fix
    assert 'text(weight: "bold")[#"(a)"]' in exam_typ
    assert 'text(weight: "bold")[#"(b)"]' in exam_typ

    # Check that each ID only appears once in the relevant parts
    # (one for the bold label, and it shouldn't appear in the question part)
    assert exam_typ.count('#"(a)"') == 1
    assert exam_typ.count('#"(b)"') == 1
