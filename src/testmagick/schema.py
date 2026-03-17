from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QuestionType = Literal["mcq", "short"]


# ─── Content Block Types ──────────────────────────────────────────────────────

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    content: str


class TypstBlock(BaseModel):
    type: Literal["typst"] = "typst"
    content: str


class FormulaBlock(BaseModel):
    type: Literal["formula"] = "formula"
    content: str  # Typst math expression (without $ delimiters)


class RequirementsBlock(BaseModel):
    type: Literal["requirements"] = "requirements"
    content: str


class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    headers: list[str] | None = None
    rows: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_table(self) -> TableBlock:
        col_source = self.headers if self.headers is not None else (
            self.rows[0] if self.rows else None
        )
        if col_source is None:
            raise ValueError("TableBlock에는 headers 또는 최소 한 개의 rows가 필요합니다.")
        expected = len(col_source)
        for i, row in enumerate(self.rows):
            if len(row) != expected:
                raise ValueError(
                    f"TableBlock의 {i + 1}번째 행의 열 수({len(row)})가 "
                    f"기준 열 수({expected})와 다릅니다."
                )
        return self


class GraphNode(BaseModel):
    id: str = Field(min_length=1)
    label: str | None = None  # Typst 콘텐츠; None이면 id를 그대로 표시
    pos: list[float]          # [x, y] 그리드 좌표

    @field_validator("id")
    @classmethod
    def _strip_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("GraphNode id는 비워둘 수 없습니다.")
        return cleaned

    @field_validator("pos")
    @classmethod
    def _validate_pos(cls, value: list[float]) -> list[float]:
        if len(value) != 2:
            raise ValueError("pos는 [x, y] 형식으로 정확히 2개의 숫자여야 합니다.")
        return value


class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)

    @field_validator("from_node", "to")
    @classmethod
    def _strip_node_ref(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("GraphEdge의 from/to는 비워둘 수 없습니다.")
        return cleaned
    label: str | None = None   # 간선 레이블 (Typst 콘텐츠)
    bend: float = 0            # 곡선 각도(degree); 양수=왼쪽, 음수=오른쪽
    directed: bool = True      # True → 화살표, False → 선
    bidirectional: bool = False  # 양방향 화살표


class GraphBlock(BaseModel):
    type: Literal["graph"] = "graph"
    nodes: list[GraphNode] = Field(min_length=1)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_edges(self) -> GraphBlock:
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.from_node not in node_ids:
                raise ValueError(f"엣지의 from 노드 '{edge.from_node}'가 nodes에 없습니다.")
            if edge.to not in node_ids:
                raise ValueError(f"엣지의 to 노드 '{edge.to}'가 nodes에 없습니다.")
        return self


class MappingEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(alias="from", min_length=1)
    to: str | list[str]  # 단일 노드 또는 복수 노드 (일대다)

    @field_validator("from_node")
    @classmethod
    def _strip_from(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("MappingEdge의 from은 비워둘 수 없습니다.")
        return cleaned

    @field_validator("to")
    @classmethod
    def _strip_to(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("MappingEdge의 to는 비워둘 수 없습니다.")
            return cleaned
        cleaned = [v.strip() for v in value if v and v.strip()]
        if not cleaned:
            raise ValueError("MappingEdge의 to 목록이 비어 있습니다.")
        return cleaned


class MappingSet(BaseModel):
    label: str | None = None  # 집합 이름 (예: "X", "$A$")
    nodes: list[str] = Field(min_length=1)

    @field_validator("nodes")
    @classmethod
    def _strip_nodes(cls, value: list[str]) -> list[str]:
        cleaned = [v.strip() for v in value if v and v.strip()]
        if not cleaned:
            raise ValueError("MappingSet의 nodes가 비어 있습니다.")
        return cleaned


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    src: str                        # YAML 기준 상대경로 또는 절대경로 (빌드 시 절대경로로 변환)
    width: str = "80%"              # Typst width 값 (예: "60%", "8cm")
    align: str = "center"          # "left" | "center" | "right"


class MappingBlock(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["mapping"] = "mapping"
    arrow_label: str | None = None  # 함수 이름 (예: "f")
    from_set: MappingSet = Field(alias="from")
    to_set: MappingSet = Field(alias="to")
    edges: list[MappingEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_edges(self) -> MappingBlock:
        from_ids = set(self.from_set.nodes)
        to_ids = set(self.to_set.nodes)
        for edge in self.edges:
            if edge.from_node not in from_ids:
                raise ValueError(
                    f"MappingEdge의 from '{edge.from_node}'이 from_set.nodes에 없습니다."
                )
            targets = edge.to if isinstance(edge.to, list) else [edge.to]
            for t in targets:
                if t not in to_ids:
                    raise ValueError(
                        f"MappingEdge의 to '{t}'이 to_set.nodes에 없습니다."
                    )
        return self


QuestionBlock = Annotated[
    Union[
        TextBlock, TypstBlock, FormulaBlock, RequirementsBlock,
        TableBlock, GraphBlock, MappingBlock, ImageBlock,
    ],
    Field(discriminator="type"),
]


# ─── Sub-Problem ──────────────────────────────────────────────────────────────

class SubProblem(BaseModel):
    id: str = Field(min_length=1)
    type: QuestionType = "short"
    question: str | None = None
    question_typst: str | None = None
    question_blocks: list[QuestionBlock] | None = None
    answer: str | int | None = None
    answer_typst: str | None = None
    choices: list[str] | None = None
    choices_typst: list[str] | None = None
    points: float = Field(default=1.0, gt=0)

    @field_validator("id")
    @classmethod
    def _strip_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("소문제 id는 비워둘 수 없습니다.")
        return cleaned

    @field_validator("question", "question_typst", "answer_typst")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("answer")
    @classmethod
    def _normalize_answer(cls, value: str | int | None) -> str | int | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @field_validator("choices", "choices_typst")
    @classmethod
    def _normalize_choices(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [c.strip() for c in value if c and c.strip()]
        return cleaned or None

    @model_validator(mode="after")
    def _validate_shape(self) -> SubProblem:
        if not self.question and not self.question_typst and not self.question_blocks:
            raise ValueError(
                "소문제에는 question, question_typst, 또는 question_blocks 중 하나가 필요합니다."
            )

        if self.type == "mcq":
            plain_count = len(self.choices or [])
            typst_count = len(self.choices_typst or [])
            if plain_count == 0 and typst_count == 0:
                raise ValueError("객관식 소문제에는 choices 또는 choices_typst가 필요합니다.")
            if plain_count > 0 and typst_count > 0 and plain_count != typst_count:
                raise ValueError("choices와 choices_typst를 함께 쓰면 길이가 같아야 합니다.")
            choice_count = plain_count or typst_count
            if choice_count < 2:
                raise ValueError("객관식 소문제 선택지는 최소 2개 이상이어야 합니다.")
            if self.answer is None:
                raise ValueError("객관식 소문제에는 정답(answer)이 필요합니다.")
            if isinstance(self.answer, int):
                if self.answer < 1 or self.answer > choice_count:
                    raise ValueError("객관식 정답 인덱스가 선택지 범위를 벗어났습니다.")
            else:
                answer_text = self.answer.strip() if isinstance(self.answer, str) else ""
                if not self.choices:
                    raise ValueError("텍스트 정답을 쓰려면 일반 choices가 필요합니다.")
                if answer_text not in self.choices:
                    raise ValueError(
                        "객관식 텍스트 정답은 choices 중 하나와 정확히 일치해야 합니다."
                    )
                self.answer = answer_text
        else:
            if self.choices or self.choices_typst:
                raise ValueError("주관식 소문제에는 choices/choices_typst를 넣을 수 없습니다.")
            if isinstance(self.answer, int):
                raise ValueError("주관식 소문제 answer는 텍스트여야 합니다.")
            answer_text = self.answer.strip() if isinstance(self.answer, str) else ""
            if not answer_text and not self.answer_typst:
                raise ValueError(
                    "주관식 소문제에는 answer 또는 answer_typst 중 하나가 필요합니다."
                )
            self.answer = answer_text or None
        return self

    def choice_count(self) -> int:
        if self.type != "mcq":
            return 0
        return len(self.choices_typst or self.choices or [])

    def choice_item(self, index_1_based: int) -> tuple[str, bool]:
        if self.type != "mcq":
            raise ValueError("choice_item은 객관식(mcq) 소문제에서만 사용할 수 있습니다.")
        if self.choices_typst:
            return self.choices_typst[index_1_based - 1], True
        if self.choices:
            return self.choices[index_1_based - 1], False
        raise ValueError("객관식 소문제에 선택지가 없습니다.")

    def resolved_answer_index(self) -> int | None:
        if self.type != "mcq":
            return None
        if isinstance(self.answer, int):
            return self.answer
        if isinstance(self.answer, str) and self.choices:
            try:
                return self.choices.index(self.answer) + 1
            except ValueError:
                return None
        return None


# ─── Problem ──────────────────────────────────────────────────────────────────

class Problem(BaseModel):
    kind: Literal["problem"] = "problem"
    id: str = Field(min_length=1)
    type: QuestionType
    question: str | None = None
    question_typst: str | None = None
    question_blocks: list[QuestionBlock] | None = None
    answer: str | int | None = None
    answer_typst: str | None = None
    choices: list[str] | None = None
    choices_typst: list[str] | None = None
    subproblems: list[SubProblem] | None = None
    source: str | None = None
    points: float = Field(default=1.0, gt=0)

    @field_validator("id")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("필수 텍스트 필드는 비워둘 수 없습니다.")
        return cleaned

    @field_validator("question", "question_typst", "answer_typst", "source")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("텍스트 필드에는 문자열만 입력할 수 있습니다.")
        cleaned = value.strip()
        return cleaned or None

    @field_validator("answer")
    @classmethod
    def _normalize_answer(cls, value: str | int | None) -> str | int | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @field_validator("choices", "choices_typst")
    @classmethod
    def _normalize_choices(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [choice.strip() for choice in value if choice and choice.strip()]
        return cleaned or None

    @model_validator(mode="after")
    def _validate_shape(self) -> Problem:
        if not self.question and not self.question_typst and not self.question_blocks:
            raise ValueError(
                "문항에는 question, question_typst, 또는 question_blocks 중 하나가 필요합니다."
            )

        if self.type == "mcq":
            plain_count = len(self.choices or [])
            typst_count = len(self.choices_typst or [])
            if plain_count == 0 and typst_count == 0:
                raise ValueError("객관식 문항에는 choices 또는 choices_typst가 필요합니다.")
            if plain_count > 0 and typst_count > 0 and plain_count != typst_count:
                raise ValueError("choices와 choices_typst를 함께 쓰면 길이가 같아야 합니다.")

            choice_count = plain_count or typst_count
            if choice_count < 2:
                raise ValueError("객관식 문항 선택지는 최소 2개 이상이어야 합니다.")

            if self.answer is None:
                raise ValueError("객관식 문항에는 정답(answer)이 필요합니다.")
            if isinstance(self.answer, int):
                if self.answer < 1 or self.answer > choice_count:
                    raise ValueError("객관식 정답 인덱스가 선택지 범위를 벗어났습니다.")
            else:
                if not isinstance(self.answer, str):
                    raise ValueError("객관식 정답은 숫자 인덱스 또는 텍스트여야 합니다.")
                answer_text = self.answer.strip()
                if not self.choices:
                    raise ValueError("텍스트 정답을 쓰려면 일반 choices가 필요합니다.")
                if answer_text not in self.choices:
                    raise ValueError(
                        "객관식 텍스트 정답은 choices 중 하나와 정확히 일치해야 합니다."
                    )
                self.answer = answer_text

            if self.subproblems:
                raise ValueError("객관식 문항에는 subproblems를 사용할 수 없습니다.")
        else:
            if self.choices or self.choices_typst:
                raise ValueError("주관식 문항에는 choices/choices_typst를 넣을 수 없습니다.")
            if isinstance(self.answer, int):
                raise ValueError("주관식 answer는 텍스트여야 합니다.")

            if self.subproblems:
                if self.answer is not None or self.answer_typst:
                    raise ValueError(
                        "subproblems가 있는 문항에는 answer/answer_typst를 직접 넣지 마세요."
                    )
            else:
                answer_text = ""
                if isinstance(self.answer, str):
                    answer_text = self.answer.strip()
                if not answer_text and not self.answer_typst:
                    raise ValueError(
                        "주관식 문항에는 answer, answer_typst, 또는"
                        " subproblems 중 하나가 필요합니다."
                    )
                self.answer = answer_text or None
        return self

    def choice_count(self) -> int:
        if self.type != "mcq":
            return 0
        if self.choices_typst:
            return len(self.choices_typst)
        if self.choices:
            return len(self.choices)
        return 0

    def choice_item(self, index_1_based: int) -> tuple[str, bool]:
        if self.type != "mcq":
            raise ValueError("choice_item은 객관식(mcq) 문항에서만 사용할 수 있습니다.")
        if index_1_based < 1 or index_1_based > self.choice_count():
            raise ValueError("선택지 인덱스가 범위를 벗어났습니다.")
        if self.choices_typst:
            return self.choices_typst[index_1_based - 1], True
        if self.choices:
            return self.choices[index_1_based - 1], False
        raise ValueError("객관식 문항에 선택지가 없습니다.")

    def resolved_answer_text(self) -> str:
        if self.type == "mcq":
            answer_index = self.resolved_answer_index()
            if answer_index is None:
                if isinstance(self.answer, str):
                    return self.answer
                raise ValueError("객관식 문항에서 해석 가능한 정답을 찾을 수 없습니다.")
            answer_text, _ = self.choice_item(answer_index)
            return answer_text
        if self.answer_typst:
            return self.answer_typst
        return str(self.answer or "")

    def resolved_answer_index(self) -> int | None:
        if self.type != "mcq":
            return None
        if isinstance(self.answer, int):
            return self.answer
        if not isinstance(self.answer, str):
            return None
        if not self.choices:
            return None
        try:
            return self.choices.index(self.answer) + 1
        except ValueError:
            return None


# ─── Section ──────────────────────────────────────────────────────────────────

class Section(BaseModel):
    kind: Literal["section"] = "section"
    title: str | None = None
    title_typst: str | None = None
    content_blocks: list[QuestionBlock] | None = None
    problems: list[Problem] = Field(min_length=1)


ExamSetItem = Annotated[
    Union[Problem, Section],
    Field(discriminator="kind"),
]


class ExamSet(BaseModel):
    title: str = "제목 없는 시험지"
    course: str | None = None
    date: str | None = None
    problems: list[ExamSetItem] = Field(default_factory=list, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _inject_kind(cls, data: Any) -> Any:
        """YAML에 kind 필드가 없는 항목은 기본값 'problem'을 주입."""
        if isinstance(data, dict):
            raw_problems = data.get("problems", [])
            if isinstance(raw_problems, list):
                injected = []
                for item in raw_problems:
                    if isinstance(item, dict) and "kind" not in item:
                        item = {**item, "kind": "problem"}
                    injected.append(item)
                data = {**data, "problems": injected}
        return data

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title은 비워둘 수 없습니다.")
        return cleaned

    @field_validator("course", "date")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _validate_unique_problem_ids(self) -> ExamSet:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in self.problems:
            ids = [item.id] if isinstance(item, Problem) else [p.id for p in item.problems]
            for pid in ids:
                if pid in seen:
                    duplicates.add(pid)
                seen.add(pid)
        if duplicates:
            duplicate_text = ", ".join(sorted(duplicates))
            raise ValueError(f"중복된 문제 ID가 있습니다: {duplicate_text}")
        return self
