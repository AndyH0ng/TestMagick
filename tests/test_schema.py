from testmagick.schema import ExamSet


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
    except Exception as exc:  # pragma: no cover - 예외 타입은 pydantic 내부 구현에 따라 달라질 수 있음
        assert "중복된 문제 ID가 있습니다: Q1" in str(exc)
    else:
        raise AssertionError("중복 ID 검증 오류가 발생해야 합니다.")
