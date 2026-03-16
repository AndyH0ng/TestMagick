from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader

from testmagick.schema import (
    ExamSet,
    FormulaBlock,
    GraphBlock,
    MappingBlock,
    Problem,
    QuestionBlock,
    RequirementsBlock,
    SubProblem,
    TableBlock,
    TypstBlock,
)

OPTION_LABELS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
ProblemPayload = dict[str, Any]


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


def _fix_latex_braces(math: str) -> str:
    """LaTeX 스타일 _{...} / ^{...} → Typst 스타일 _(...) / ^(...) 변환 (비중첩 한정)."""
    import re
    return re.sub(r'([_^])\{([^{}]*)\}', r'\1(\2)', math)


def typst_cell(value: str) -> str:
    """Typst content block [...] 안에서 사용. $...$ 또는 #으로 시작하면 raw, 아니면 #"..." 이스케이프."""
    s = value.strip()
    if s.startswith("$") and s.endswith("$") and len(s) > 2:
        return _fix_latex_braces(s)
    if s.startswith("#"):
        return s
    return "#" + json.dumps(value, ensure_ascii=False)


def _bend_ctrl(
    from_pos: list[float], to_pos: list[float], bend_deg: float
) -> list[list[float]] | None:
    """곡선 엣지의 cubic bezier 제어점 2개 계산. bend_deg=0이면 None(직선).
    bend > 0: 진행 방향 기준 왼쪽 굽힘, bend < 0: 오른쪽 굽힘.
    """
    if bend_deg == 0:
        return None
    fx, fy = from_pos
    tx, ty = to_pos
    dx, dy = tx - fx, ty - fy
    d = math.sqrt(dx * dx + dy * dy)
    if d < 1e-9:
        return None
    # 진행 방향 기준 왼쪽 수직 단위벡터
    perp_x, perp_y = -dy / d, dx / d
    offset = d * math.tan(math.radians(bend_deg)) * 0.5
    # 1/3, 2/3 지점에서 수직 오프셋 → 자연스러운 호 모양
    c1 = [fx + dx / 3 + perp_x * offset, fy + dy / 3 + perp_y * offset]
    c2 = [fx + 2 * dx / 3 + perp_x * offset, fy + 2 * dy / 3 + perp_y * offset]
    return [c1, c2]


def _mapping_payload(block: MappingBlock) -> dict[str, Any]:
    from_nodes = block.from_set.nodes
    to_nodes = block.to_set.nodes
    fn, tn = len(from_nodes), len(to_nodes)

    oval_hw = 1.2        # oval half-width
    node_spacing = 0.9
    pad_y = 0.55         # vertical padding inside oval

    def node_ys(n: int) -> list[float]:
        top = (n - 1) * node_spacing / 2
        return [top - i * node_spacing for i in range(n)]

    left_ys = node_ys(fn)
    right_ys = node_ys(tn)

    left_cx = -2.5
    right_cx = 2.5
    left_hh = max(fn - 1, 0) * node_spacing / 2 + pad_y
    right_hh = max(tn - 1, 0) * node_spacing / 2 + pad_y
    left_radius = round(min(oval_hw, left_hh), 4)
    right_radius = round(min(oval_hw, right_hh), 4)

    from_idx = {n: i for i, n in enumerate(from_nodes)}
    to_idx = {n: i for i, n in enumerate(to_nodes)}

    edges_out = []
    for edge in block.edges:
        if edge.from_node not in from_idx:
            continue
        fi = from_idx[edge.from_node]
        fy = left_ys[fi]
        targets = edge.to if isinstance(edge.to, list) else [edge.to]
        for t in targets:
            if t not in to_idx:
                continue
            ti = to_idx[t]
            edges_out.append({
                "left_idx": fi + 1,   # 1-based (matches Jinja loop.index)
                "right_idx": ti + 1,
            })

    return {
        "type": "mapping",
        "from_label": block.from_set.label,
        "to_label": block.to_set.label,
        "arrow_label": block.arrow_label,
        "left_cx": left_cx,
        "left_hh": round(left_hh, 4),
        "left_radius": left_radius,
        "right_cx": right_cx,
        "right_hh": round(right_hh, 4),
        "right_radius": right_radius,
        "oval_hw": oval_hw,
        "left_nodes": [
            {"label": n, "x": left_cx, "y": round(left_ys[i], 4)}
            for i, n in enumerate(from_nodes)
        ],
        "right_nodes": [
            {"label": n, "x": right_cx, "y": round(right_ys[i], 4)}
            for i, n in enumerate(to_nodes)
        ],
        "edges": edges_out,
    }


def _block_payload(block: QuestionBlock) -> dict[str, Any]:
    if isinstance(block, TableBlock):
        return {
            "type": "table",
            "headers": block.headers,
            "rows": block.rows,
        }
    if isinstance(block, FormulaBlock):
        return {"type": "formula", "content": block.content}
    if isinstance(block, RequirementsBlock):
        return {"type": "requirements", "content": block.content}
    if isinstance(block, TypstBlock):
        return {"type": "typst", "content": block.content}
    if isinstance(block, MappingBlock):
        return _mapping_payload(block)
    if isinstance(block, GraphBlock):
        node_pos = {n.id: n.pos for n in block.nodes}
        return {
            "type": "graph",
            "nodes": [
                {"id": n.id, "label": n.label if n.label is not None else n.id, "pos": n.pos}
                for n in block.nodes
            ],
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to,
                    "ctrl_pos": _bend_ctrl(node_pos[e.from_node], node_pos[e.to], e.bend),
                    "label": e.label,
                    "directed": e.directed,
                    "bidirectional": e.bidirectional,
                    "is_self_loop": e.from_node == e.to,
                }
                for e in block.edges
            ],
        }
    # TextBlock
    return {"type": "text", "content": block.content}  # type: ignore[union-attr]


def _answer_label(problem: Problem) -> str:
    if problem.subproblems:
        return "—"
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
    if problem.subproblems:
        return {"label": "—", "value": "", "is_typst": False}

    if problem.type == "mcq":
        answer_index = problem.resolved_answer_index()
        if answer_index is None:
            return {"label": "TEXT", "value": "", "is_typst": False}
        answer_value, answer_is_typst = problem.choice_item(answer_index)
        label = option_label(answer_index - 1)
        if problem.answer_typst:
            return {"label": label, "value": problem.answer_typst, "is_typst": True}
        return {"label": label, "value": answer_value, "is_typst": answer_is_typst}

    if problem.answer_typst:
        return {"label": "TEXT", "value": problem.answer_typst, "is_typst": True}
    return {"label": "TEXT", "value": problem.resolved_answer_text(), "is_typst": False}


def _sub_choice_payload(sub: SubProblem) -> list[dict[str, str | bool]]:
    if sub.type != "mcq":
        return []
    choices: list[dict[str, str | bool]] = []
    for i in range(1, sub.choice_count() + 1):
        value, is_typst = sub.choice_item(i)
        choices.append({"label": option_label(i - 1), "value": value, "is_typst": is_typst})
    return choices


def _sub_answer_payload(sub: SubProblem) -> dict[str, str | bool]:
    if sub.type == "mcq":
        answer_index = sub.resolved_answer_index()
        if answer_index is None:
            return {"label": "TEXT", "value": "", "is_typst": False}
        answer_value, answer_is_typst = sub.choice_item(answer_index)
        label = option_label(answer_index - 1)
        if sub.answer_typst:
            return {"label": label, "value": sub.answer_typst, "is_typst": True}
        return {"label": label, "value": answer_value, "is_typst": answer_is_typst}
    if sub.answer_typst:
        return {"label": "TEXT", "value": sub.answer_typst, "is_typst": True}
    return {"label": "TEXT", "value": str(sub.answer or ""), "is_typst": False}


def _subproblem_payload(sub: SubProblem) -> dict[str, Any]:
    answer = _sub_answer_payload(sub)
    
    question = sub.question or ""
    if question == sub.id:
        question = ""
    elif question.startswith(sub.id + " "):
        question = question[len(sub.id) + 1 :].lstrip()

    question_typst = sub.question_typst or ""
    if question_typst == sub.id:
        question_typst = ""
    elif question_typst.startswith(sub.id + " "):
        question_typst = question_typst[len(sub.id) + 1 :].lstrip()

    return {
        "id": sub.id,
        "type": sub.type,
        "question": question,
        "question_typst": question_typst,
        "question_is_typst": bool(question_typst),
        "question_blocks": [_block_payload(b) for b in (sub.question_blocks or [])],
        "choices": _sub_choice_payload(sub),
        "answer_text": str(answer["value"]),
        "answer_is_typst": bool(answer["is_typst"]),
        "answer_label": str(answer["label"]),
        "points": sub.points,
    }


def _problem_payload(problem: Problem) -> ProblemPayload:
    answer = _answer_payload(problem)
    has_subproblems = bool(problem.subproblems)
    return {
        "id": problem.id,
        "type": problem.type,
        "question": problem.question or "",
        "question_typst": problem.question_typst or "",
        "question_is_typst": bool(problem.question_typst),
        "question_blocks": [_block_payload(b) for b in (problem.question_blocks or [])],
        "choices": _choice_payload(problem),
        "points": problem.points,
        "answer_text": str(answer["value"]),
        "answer_is_typst": bool(answer["is_typst"]),
        "answer_label": str(answer["label"]) or _answer_label(problem),
        "source": problem.source,
        "has_subproblems": has_subproblems,
        "subproblems": [_subproblem_payload(sp) for sp in (problem.subproblems or [])],
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
    env.filters["typst_cell"] = typst_cell
    return env


def render_typst_files(
    exam_set: ExamSet,
    out_dir: Path,
    title_override: str | None = None,
) -> RenderedFiles:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _create_environment()
    payload = {
        "title": title_override or exam_set.title,
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
