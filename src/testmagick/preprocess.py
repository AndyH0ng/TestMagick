from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ─── 수식 폰트 감지용 힌트 ────────────────────────────────────────────────────
# PDF에 삽입된 TeX/수학 전용 폰트 이름 패턴 (대소문자 무관)
_MATH_FONT_HINTS = {
    "CMMI",   # Computer Modern Math Italic
    "CMSY",   # Computer Modern Symbols
    "CMEX",   # Computer Modern Extensions
    "MSAM",   # AMS Symbols A
    "MSBM",   # AMS Symbols B
    "EUEX",   # Euler Extended
    "MTSYN",  # MathTime Symbols
    "MTSY",
    "STMARY", # St Mary Road (math)
    "MATHPI",
}


# ─── 결과 타입 ────────────────────────────────────────────────────────────────

@dataclass
class PageDecision:
    page_num: int           # 1-based
    use_image: bool
    reason: str             # "math_font" | "low_quality" | "no_text" | "text_ok"
    quality_score: float    # 0.0 ~ 1.0 (텍스트 품질)
    output_file: Path | None = None


@dataclass
class PreprocessResult:
    method: Literal["text", "images", "mixed", "markdown"]
    text_file: Path | None = None       # text.txt (text/mixed 모드)
    image_files: list[Path] = field(default_factory=list)   # page_*.jpg
    schema_ref: Path = field(default=Path())
    page_decisions: list[PageDecision] = field(default_factory=list)
    page_count: int = 0
    est_tokens: int = 0

    @property
    def all_files(self) -> list[Path]:
        result: list[Path] = []
        if self.text_file:
            result.append(self.text_file)
        result.extend(self.image_files)
        return result


# ─── 의존성 체크 ──────────────────────────────────────────────────────────────

def _require_pymupdf() -> None:
    try:
        import fitz  # noqa: F401
    except ImportError:
        raise ImportError(
            "pymupdf가 설치되어 있지 않습니다.\n"
            "설치 명령: uv pip install 'testmagick[preprocess]'"
        )


# ─── 페이지별 수식 감지 ───────────────────────────────────────────────────────

def _has_math_fonts(page: object) -> bool:
    """페이지에 TeX 수식 전용 폰트가 포함되어 있으면 True."""
    for font in page.get_fonts(full=True):  # type: ignore[attr-defined]
        basename = font[3].upper()  # index 3 = basefont name
        if any(hint in basename for hint in _MATH_FONT_HINTS):
            return True
    return False


def _text_quality_score(text: str) -> float:
    """추출된 텍스트의 가독성 점수를 반환한다 (0.0=수식 파편, 1.0=깨끗한 텍스트).

    수식이 많은 페이지는 x, 1, +, =, (, ) 같은 1~2자 토큰이 많아서 점수가 낮아진다.
    한국어/영어 일반 텍스트는 평균 토큰 길이가 길어서 점수가 높다.
    """
    tokens = text.split()
    if not tokens:
        return 0.0

    avg_len = sum(len(t) for t in tokens) / len(tokens)
    short_frac = sum(1 for t in tokens if len(t) <= 2) / len(tokens)

    # avg_len 5 이상 → 1.0, 짧을수록 감소
    len_score = min(avg_len / 5.0, 1.0)
    # short_frac 0 → 1.0, 0.67 이상 → 0.0
    short_score = max(1.0 - short_frac * 1.5, 0.0)

    return len_score * short_score


def _decide_page(
    page: object, math_font_threshold: bool = True, quality_threshold: float = 0.40
) -> tuple[bool, str, float]:
    """페이지를 이미지로 처리할지 텍스트로 처리할지 결정한다.

    Returns:
        (use_image, reason, quality_score)
    """
    text = _extract_page_text(page).strip()

    if not text:
        return True, "no_text", 0.0

    if math_font_threshold and _has_math_fonts(page):
        score = _text_quality_score(text)
        return True, "math_font", score

    score = _text_quality_score(text)
    if score < quality_threshold:
        return True, "low_quality", score

    return False, "text_ok", score


# ─── 텍스트 추출 (다단 레이아웃 대응) ────────────────────────────────────────

def _extract_page_text(page: object) -> str:
    """다단(multi-column) 레이아웃을 고려한 텍스트 추출.

    page.get_text("blocks")로 블록 단위 추출 후 열(column) 순서로 재정렬한다.
    - 단단(single-column): y0 기준 정렬
    - 2단: 블록 중심 x 좌표로 좌/우 분리 후, 왼쪽 열 → 오른쪽 열 순으로 y0 정렬
    """
    page_rect = page.rect  # type: ignore[attr-defined]
    mid_x = page_rect.width / 2

    blocks = page.get_text("blocks")  # type: ignore[attr-defined]
    # block: (x0, y0, x1, y1, text, block_no, block_type)
    # block_type=0: 텍스트, block_type=1: 이미지
    text_blocks = [
        (b[0], b[1], b[2], b[4])  # (x0, y0, x1, text)
        for b in blocks
        if b[6] == 0 and b[4].strip()
    ]

    if not text_blocks:
        return ""

    # 블록 중심 x 좌표로 좌/우 분리
    left = [(x0, y0, text) for x0, y0, x1, text in text_blocks if (x0 + x1) / 2 < mid_x]
    right = [(x0, y0, text) for x0, y0, x1, text in text_blocks if (x0 + x1) / 2 >= mid_x]

    # 2단 감지: 좌우 모두 블록이 2개 이상이고, 우측이 전체의 25% 이상
    is_multicolumn = (
        len(left) >= 2
        and len(right) >= 2
        and len(right) / len(text_blocks) >= 0.25
    )

    if is_multicolumn:
        ordered = sorted(left, key=lambda b: b[1]) + sorted(right, key=lambda b: b[1])
    else:
        ordered = [(x0, y0, text) for x0, y0, x1, text in sorted(text_blocks, key=lambda b: b[1])]

    return "\n".join(text for _, _, text in ordered)


# ─── 텍스트 정제 ──────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


# ─── 렌더링 헬퍼 ─────────────────────────────────────────────────────────────

_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB (API 한도 5 MB에 여유)
_MAX_IMAGE_PX = 7900               # API 한도 8000 px에 여유


def _render_page(page: object, path: Path, dpi: int, quality: int) -> tuple[int, int]:
    """페이지를 JPEG로 렌더링하고 (width, height)를 반환한다.

    픽셀 크기(8000px) 또는 파일 크기(5MB)를 초과하면 DPI를 낮춰 재렌더링한다.
    """
    import fitz

    cur_dpi = dpi
    while True:
        scale = cur_dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)  # type: ignore[attr-defined]

        if (pix.width > _MAX_IMAGE_PX or pix.height > _MAX_IMAGE_PX) and cur_dpi > 50:
            cur_dpi = int(cur_dpi * 0.8)
            continue

        data = pix.tobytes(output="jpg", jpg_quality=quality)
        if len(data) <= _MAX_IMAGE_BYTES or cur_dpi <= 50:
            path.write_bytes(data)
            return pix.width, pix.height
        cur_dpi = int(cur_dpi * 0.8)


# ─── 토큰 추정 ────────────────────────────────────────────────────────────────

def _est_text_tokens(text: str) -> int:
    return math.ceil(len(text) / 3.5)


def _est_image_tokens(w: int, h: int, n: int = 1) -> int:
    """Claude Vision 기준 (512×512 타일당 ~170토큰)."""
    return math.ceil(w / 512) * math.ceil(h / 512) * 170 * n


# ─── 처리 모드별 구현 ─────────────────────────────────────────────────────────

def _run_text(doc: object, out_dir: Path) -> tuple[Path, list[PageDecision], int]:
    parts: list[str] = []
    decisions: list[PageDecision] = []
    for i, page in enumerate(doc):  # type: ignore[arg-type]
        text = _clean_text(_extract_page_text(page))
        score = _text_quality_score(text)
        decisions.append(PageDecision(i + 1, False, "forced_text", score))
        if text:
            parts.append(f"[페이지 {i + 1}]\n{text}")
    text_path = out_dir / "text.txt"
    text_path.write_text("\n\n".join(parts), encoding="utf-8")
    tokens = _est_text_tokens(text_path.read_text(encoding="utf-8"))
    return text_path, decisions, tokens


def _run_images(
    doc: object, out_dir: Path, dpi: int, quality: int
) -> tuple[list[Path], list[PageDecision], int]:
    paths: list[Path] = []
    decisions: list[PageDecision] = []
    total_tokens = 0
    for i, page in enumerate(doc):  # type: ignore[arg-type]
        path = out_dir / f"page_{i + 1:03d}.jpg"
        w, h = _render_page(page, path, dpi, quality)
        total_tokens += _est_image_tokens(w, h)
        decisions.append(PageDecision(i + 1, True, "forced_images", 0.0, path))
        paths.append(path)
    return paths, decisions, total_tokens


def _run_mixed(
    doc: object, out_dir: Path, dpi: int, quality: int
) -> tuple[Path, list[Path], list[PageDecision], int]:
    """페이지마다 수식 감지 → 이미지 또는 텍스트로 처리."""
    text_parts: list[str] = []
    img_paths: list[Path] = []
    decisions: list[PageDecision] = []
    total_tokens = 0

    for i, page in enumerate(doc):  # type: ignore[arg-type]
        use_img, reason, score = _decide_page(page)

        if use_img:
            img_path = out_dir / f"page_{i + 1:03d}.jpg"
            w, h = _render_page(page, img_path, dpi, quality)
            total_tokens += _est_image_tokens(w, h)
            # txt 파일에 이미지 마커 삽입
            text_parts.append(f"[페이지 {i + 1} → 이미지: page_{i + 1:03d}.jpg]")
            decisions.append(PageDecision(i + 1, True, reason, score, img_path))
            img_paths.append(img_path)
        else:
            text = _clean_text(_extract_page_text(page))
            total_tokens += _est_text_tokens(text)
            if text:
                text_parts.append(f"[페이지 {i + 1}]\n{text}")
            decisions.append(PageDecision(i + 1, False, reason, score))

    text_path = out_dir / "text.txt"
    text_path.write_text("\n\n".join(text_parts), encoding="utf-8")
    return text_path, img_paths, decisions, total_tokens


# ─── 스키마 참조 문서 ─────────────────────────────────────────────────────────

_SCHEMA_REF = """\
# TestMagick YAML 스키마 참조

## 최상위 구조
```yaml
title: "시험지 제목"
course: "과목명"      # 선택
date: "YYYY-MM-DD"   # 선택
problems:
  - id: "1"
    type: mcq         # 또는 short
    ...
```

## Problem 필드
| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | str | 문제 식별자 (필수) |
| `type` | `mcq`\\|`short` | 객관식\\|주관식 |
| `question` | str | 일반 텍스트 문제 |
| `question_typst` | str | Typst 마크업 문제 (question 대신 사용) |
| `question_blocks` | list | 수식·표·그래프 블록 목록 |
| `choices` | list[str] | 객관식 선택지 (plain) |
| `choices_typst` | list[str] | 객관식 선택지 (Typst 수식) |
| `answer` | int\\|str | 정답 (mcq: 1-based 인덱스, short: 텍스트) |
| `answer_typst` | str | Typst 마크업 정답 (answer 대신 사용) |
| `subproblems` | list | 소문제 목록 (short 타입만) |
| `points` | float | 배점 (기본 1.0) |

## question_blocks 타입

### formula — 수식 가운데 정렬
```yaml
- type: formula
  content: "cases(2x_1 + 3x_2 = 8, x_1 - x_2 = 1)"
```

### table — 표
```yaml
- type: table
  headers: ["연도", "매출"]
  rows:
    - ["2022", "1,500"]
    - ["2023", "1,800"]
```

### text — 일반 텍스트 단락
```yaml
- type: text
  content: "첫째항이 3이고 공비가 2인 등비수열이 있다."
```

### requirements — 조건 박스
```yaml
- type: requirements
  content: "단, 소수점 첫째 자리에서 반올림하시오."
```

### typst — 자유 Typst 코드
```yaml
- type: typst
  content: |
    #align(center)[$mat(delim: "[", 1, 2; 3, 4)$]
```

### graph — 방향 그래프
```yaml
- type: graph
  nodes:
    - {id: "A", label: "$A$", pos: [0, 2]}
    - {id: "B", label: "$B$", pos: [2, 2]}
  edges:
    - {from: "A", to: "B", directed: true, bend: 0}
```
`pos`: [x, y], y↑ 기준. `bend`: 양수=왼쪽 굽힘, 음수=오른쪽.

## question vs question_typst 선택 기준
- `question`: 수식이 **전혀 없는** 순수 한국어/영어 텍스트만 사용
- `question_typst`: 문장 안에 수식이 **한 글자라도** 있으면 반드시 사용
  - 인라인 수식(문장 중간)은 `$...$`로 감싼다
  - 예: `"$a_1 eq.not a_2$일 때, 이 연립방정식은 하나의 해만 가짐을 보여라."`

```yaml
# ❌ 잘못된 예 — 수식을 그냥 텍스트로 삽입
question: "a1 ≠ a2일 때, 유일해임을 보여라."

# ✅ 올바른 예 — 인라인 수식을 $...$로 처리
question_typst: "$a_1 eq.not a_2$일 때, 유일해임을 보여라."

# ✅ 또 다른 예 — 여러 인라인 수식
question_typst: "다항식 $p(x) = a_0 + a_1 x + a_2 x^2$이 점 $(1, 3)$을 지날 때 $a_0$를 구하라."
```

## MCQ answer_typst (객관식 해설)
객관식에도 `answer_typst`로 해설을 작성할 수 있다. 선택지 번호(①②③…)는 유지된다.
```yaml
- id: "1"
  type: mcq
  question: "다음 중 참인 것은?"
  choices: ["참", "거짓"]
  answer: 1
  answer_typst: |
    ① 참이다. $x = 0$일 때 성립한다.
```

## choices_typst (수식 선택지)
선택지에 수식이 포함될 경우 `choices_typst`를 사용한다.
```yaml
choices_typst:
  - "$x = 1, 2$"
  - "$x = 2, 3$"
  - "$x = -2, -3$"
answer: 2
```

## subproblem 필드
Problem과 동일 (id, type, question, question_typst, question_blocks, choices, answer, points).
단, subproblems 중첩 불가.

## Section (공통 지문 묶음)
여러 문제가 같은 제시문·데이터를 공유할 때 사용한다.
문제지에서 "다음 ○○를 이용하여 N~M번 물음에 답하라" 형태의 지문 박스가 있으면 반드시 section으로 묶어라.

**주의**: Typst에서 `~`는 non-breaking space로 처리된다. 물결표 문자(~)를 출력하려면 `\\~`로 이스케이프하고 YAML 싱글쿼트로 감싸야 한다.
```yaml
- kind: section
  title_typst: '※ [3\\~8번] 다음 행렬 $A$\\~$H$를 이용하여 물음에 답하라.'
  content_blocks:
    - type: formula
      content: "A = mat(delim: \"[\", 1, 2; 3, 4), quad B = mat(delim: \"[\", 5, 6; 7, 8)"
  problems:
    - id: "3"
      type: short
      question: "각 행렬의 크기를 구하라."
      answer_typst: "..."
    - id: "4"
      ...
```
- `title_typst`: 섹션 제목 (Typst 수식 포함 가능)
- `content_blocks`: 공통 제시문 블록 (formula / table / typst 등)
- `problems`: 섹션 안의 문제 목록 (Problem과 동일 구조, kind 필드 없음)
- section 안 문제에는 제시문을 반복하지 말 것 (content_blocks에 한 번만 작성)


## 자주 쓰는 Typst 수식
| 내용 | Typst |
|------|-------|
| 분수 | `frac(a, b)` |
| 첨자/제곱 | `x_1`, `x^2` |
| 같지 않음 | `eq.not` |
| 행렬 | `mat(delim: "[", 1,2; 3,4)` |
| 첨가행렬 | `mat(delim: "[", augment: #2, 1,2,3; 4,5,6)` |
| 연립방정식 | `cases(x+y=1, x-y=2)` |
| 절댓값 | `abs(x)` |
| 노름 | `norm(x)` |
| 이항계수 | `binom(n, k)` |
| 합·곱 | `sum_(i=1)^n`, `product_(i=1)^n` |
| 극한 | `lim_(x -> 0)` |
| 편미분 | `partial / (partial x)` |
"""

_PROMPT_HINT = """\
# LLM에게 전달할 프롬프트 예시

## mixed 모드 (텍스트+이미지 혼합)
1. schema_ref.md 내용을 시스템 프롬프트 또는 첫 메시지에 붙여넣기
2. text.txt 내용을 이어서 붙여넣기
3. text.txt 내 `[페이지 N → 이미지: page_N.jpg]` 마커에 해당하는 이미지 첨부
4. 아래 요청 프롬프트 입력

## 이미지 전용 모드
1. schema_ref.md 붙여넣기
2. page_*.jpg 이미지 모두 첨부
3. 아래 요청 프롬프트 입력

---

## 요청 프롬프트
```
위 스키마를 참고하여, 첨부한 문제지를 TestMagick YAML 형식으로 변환해주세요.

규칙:
- 각 문제 id는 원본 번호 그대로 사용 ("1", "2", ...)
- 독립 줄 수식(가운데 정렬)은 question_blocks의 formula 타입으로 ($ 없이 Typst 수식 문법)
- 행렬은 mat(delim: "[", ...) 사용, 첨가행렬은 augment: #N 파라미터
- 소문제가 있으면 반드시 subproblems 배열로
- 소문제 id에 부모 문제 번호를 포함하지 말 것: "10a"가 아닌 "a", "(1)", "가" 등 사용
- 풀이/해설은 answer_typst에 Typst 마크업으로 작성
- question 필드에는 수식이 전혀 없는 순수 텍스트만 사용
- 문장 중간에 수식이 한 글자라도 있으면 반드시 question_typst 사용,
  인라인 수식은 $...$로 감쌀 것
  예) question_typst: "$a_1 eq.not a_2$일 때, 유일해임을 보여라."
- choices/answer도 동일: 수식 포함 시 choices_typst, answer_typst 사용
- 공통 지문/제시문이 있는 문제 묶음은 반드시 kind: section으로 묶을 것
  (예: "다음 행렬 A~H를 이용하여 3~8번 물음에 답하라" → section으로 묶고 제시문은 content_blocks에)
- Typst에서 ~는 non-breaking space임. 물결표 문자는 \\~로 이스케이프하고 YAML 싱글쿼트로 감쌀 것
  예) title_typst: '※ [3\\~8번] 다음 행렬 $A$\\~$H$를 이용하여 물음에 답하라.'
- 완전한 YAML만 출력. 반드시 ```yaml 블록으로 감싸서 출력.
```
"""


# ─── Markdown 변환 (marker-pdf) ──────────────────────────────────────────────

def _require_marker() -> None:
    try:
        from marker.converters.pdf import PdfConverter  # noqa: F401
    except ImportError:
        raise ImportError(
            "marker-pdf가 설치되어 있지 않습니다.\n"
            "설치 명령: uv pip install 'testmagick[markdown]'"
        )


def convert_to_markdown(pdf_path: Path) -> str:
    """marker-pdf를 사용해 PDF → Markdown (LaTeX 수식 포함)으로 변환한다."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(pdf_path))
    text, _, _ = text_from_rendered(rendered)
    return text


def _run_markdown(pdf_path: Path, out_dir: Path) -> tuple[Path, int]:
    md_text = convert_to_markdown(pdf_path)
    md_path = out_dir / "content.md"
    md_path.write_text(md_text, encoding="utf-8")
    tokens = _est_text_tokens(md_text)
    return md_path, tokens


# ─── 메인 함수 ────────────────────────────────────────────────────────────────

def preprocess_pdf(
    pdf_path: Path,
    out_dir: Path,
    *,
    method: Literal["auto", "mixed", "text", "images", "markdown"] = "auto",
    dpi: int = 150,
    quality: int = 72,
) -> PreprocessResult:
    """PDF를 LLM 전달에 최적화된 형태로 전처리한다.

    방법:
      auto     : 텍스트 레이어 있으면 mixed, 없으면 images (기본값)
      mixed    : 페이지마다 수식 감지 → 수식 페이지는 이미지, 나머지는 텍스트
      text     : 모든 페이지 텍스트 추출 (강제)
      images   : 모든 페이지 이미지 압축 (강제)
      markdown : marker-pdf로 PDF → LaTeX Markdown 변환 (content.md 출력)
    """
    _require_pymupdf()
    out_dir.mkdir(parents=True, exist_ok=True)

    import fitz
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)

    # auto → 문서 수준 텍스트 레이어 확인 후 mixed/images 결정
    if method == "auto":
        total_chars = sum(len(p.get_text().strip()) for p in doc)
        has_text = (total_chars / max(page_count, 1)) >= 80
        method = "mixed" if has_text else "images"

    text_file: Path | None = None
    image_files: list[Path] = []
    decisions: list[PageDecision] = []
    est_tokens = 0

    if method == "markdown":
        doc.close()
        _require_marker()
        text_file, est_tokens = _run_markdown(pdf_path, out_dir)
    else:
        if method == "text":
            text_file, decisions, est_tokens = _run_text(doc, out_dir)

        elif method == "images":
            image_files, decisions, est_tokens = _run_images(doc, out_dir, dpi, quality)

        elif method == "mixed":
            text_file, image_files, decisions, est_tokens = _run_mixed(doc, out_dir, dpi, quality)

        doc.close()

    schema_ref_path = out_dir / "schema_ref.md"
    schema_ref_path.write_text(_SCHEMA_REF, encoding="utf-8")
    (out_dir / "prompt.md").write_text(_PROMPT_HINT, encoding="utf-8")

    return PreprocessResult(
        method=method,  # type: ignore[arg-type]
        text_file=text_file,
        image_files=image_files,
        schema_ref=schema_ref_path,
        page_decisions=decisions,
        page_count=page_count,
        est_tokens=est_tokens,
    )
