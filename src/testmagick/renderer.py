from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader

from testmagick.schema import ExamSet, Problem

OPTION_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class RenderedFiles:
    exam_typ: Path
    answer_typ: Path


def option_label(index: int) -> str:
    if index < 0:
        return "?"
    if index < len(OPTION_LABELS):
        return OPTION_LABELS[index]
    return str(index + 1)


def typst_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _answer_label(problem: Problem) -> str:
    answer_index = problem.resolved_answer_index()
    if answer_index is None:
        return "TEXT"
    return option_label(answer_index - 1)


def _choice_payload(problem: Problem) -> list[dict[str, str | bool]]:
    if problem.type != "mcq":
        return []
    choices: list[dict[str, str | bool]] = []
    for index in range(1, problem.choice_count() + 1):
        value, is_typst = problem.choice_item(index)
        choices.append(
            {
                "label": option_label(index - 1),
                "value": value,
                "is_typst": is_typst,
            }
        )
    return choices


def _answer_payload(problem: Problem) -> dict[str, str | bool]:
    if problem.type == "mcq":
        answer_index = problem.resolved_answer_index()
        if answer_index is None:
            return {"label": "TEXT", "value": "", "is_typst": False}
        value, is_typst = problem.choice_item(answer_index)
        return {
            "label": option_label(answer_index - 1),
            "value": value,
            "is_typst": is_typst,
        }

    if problem.answer_typst:
        return {"label": "TEXT", "value": problem.answer_typst, "is_typst": True}
    return {"label": "TEXT", "value": problem.resolved_answer_text(), "is_typst": False}


def _problem_payload(problem: Problem) -> dict[str | Any, str | bool | list[dict[str, str | bool]] | float | Any]:
    answer = _answer_payload(problem)
    return {
        "id": problem.id,
        "type": problem.type,
        "question": problem.question or "",
        "question_typst": problem.question_typst or "",
        "question_is_typst": bool(problem.question_typst),
        "choices": _choice_payload(problem),
        "points": problem.points,
        "answer_text": str(answer["value"]),
        "answer_is_typst": bool(answer["is_typst"]),
        "answer_label": str(answer["label"]) or _answer_label(problem),
        "source": problem.source,
        "tags_text": ", ".join(problem.tags),
    }


def _create_environment() -> Environment:
    env = Environment(
        loader=PackageLoader("testmagick", "templates"),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["option_label"] = option_label
    env.filters["typst_string"] = typst_string
    return env


def render_typst_files(exam_set: ExamSet, out_dir: Path, title_override: str | None = None) -> RenderedFiles:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _create_environment()
    payload = {
        "title": title_override or exam_set.title,
        "subtitle": exam_set.subtitle,
        "course": exam_set.course,
        "date": exam_set.date,
        "problems": [_problem_payload(p) for p in exam_set.problems],
    }

    exam_typ_content = env.get_template("exam.typ.j2").render(**payload)
    answer_typ_content = env.get_template("answer.typ.j2").render(**payload)

    exam_typ_path = out_dir / "exam.typ"
    answer_typ_path = out_dir / "answer.typ"
    exam_typ_path.write_text(exam_typ_content, encoding="utf-8")
    answer_typ_path.write_text(answer_typ_content, encoding="utf-8")

    return RenderedFiles(exam_typ=exam_typ_path, answer_typ=answer_typ_path)
