"""generate.py — PDF → LLM 피드백 루프 → YAML → PDF 자동 생성 파이프라인."""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(highlight=False)

# ── 의존성 체크 ────────────────────────────────────────────────────────────────


def _require_anthropic() -> None:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        raise ImportError(
            "anthropic 패키지가 설치되어 있지 않습니다.\n"
            "설치: pip install anthropic  또는  uv pip install anthropic"
        )


# ── 출력 헬퍼 ─────────────────────────────────────────────────────────────────


def _ok(label: str, detail: str = "") -> None:
    line = f"[green]✓[/green] [bold]{escape(label)}[/bold]"
    if detail:
        line += f"  [dim]{escape(detail)}[/dim]"
    console.print(line)


def _warn(label: str, detail: str = "") -> None:
    line = f"[yellow]![/yellow] [bold]{escape(label)}[/bold]"
    if detail:
        line += f"  [yellow]{escape(detail)}[/yellow]"
    console.print(line)


def _err(label: str, detail: str = "") -> None:
    line = f"[red]✗[/red] [bold]{escape(label)}[/bold]"
    if detail:
        line += f"  [red]{escape(detail)}[/red]"
    console.print(line)


def _stream_preview(text: str) -> Text:
    """스트리밍 수신 중 Live 패널에 표시할 미리보기."""
    lines = text.splitlines()
    tail = lines[-14:] if len(lines) > 14 else lines
    t = Text()
    t.append(f"  {len(text):,}자 수신 중...\n\n", style="dim")
    for line in tail:
        t.append(f"  {line}\n", style="dim")
    return t


# ── LLM 요청 구성 ─────────────────────────────────────────────────────────────

_REQUEST_PROMPT = """\
위 스키마를 참고하여 첨부한 문제지를 TestMagick YAML 형식으로 변환해주세요.

규칙:
- 각 문제 id는 원본 번호 그대로 사용 ("1", "2", ...)
- 독립 줄 수식(가운데 정렬)은 question_blocks의 formula 타입으로 ($ 없이 Typst 수식 문법)
- 행렬: mat(delim: "[", ...) / 첨가행렬: augment: #N
- 소문제가 있으면 반드시 subproblems 배열로
- 풀이/해설은 answer_typst에 Typst 마크업으로 작성
- question 필드에는 수식이 전혀 없는 순수 텍스트만 사용
- 문장 중간에 수식이 한 글자라도 있으면 question_typst 사용, 인라인 수식은 $...$
- choices/answer도 동일: 수식 포함 시 choices_typst / answer_typst 사용
- 소문제 id에 부모 문제 번호를 포함하지 말 것: "10a"가 아닌 "a", "(1)", "가" 등 사용
- 공통 지문/제시문이 있는 문제 묶음은 반드시 kind: section으로 묶을 것
  (예: "다음 행렬 A~H를 이용하여 3~8번 물음에 답하라" → section으로 묶고 제시문은 content_blocks에)
- Typst에서 ~는 non-breaking space임. 물결표(~) 문자를 title_typst 등에 쓸 때는 \\~로 이스케이프하고 YAML 싱글쿼트로 감쌀 것
  (예: title_typst: '※ [3\\~8번] ...')
- 완전한 YAML만 출력. 반드시 ```yaml 블록으로 감싸서 출력.
"""

_CORRECTION_PREFIX = (
    "아래 스키마 검증 오류가 발생했습니다. "
    "오류를 모두 수정하여 완전한 YAML을 다시 ```yaml 블록으로만 출력해주세요.\n\n"
)


def _prep_to_blocks(text_file: Path | None, image_files: list[Path]) -> list[dict]:
    """전처리 결과(text_file + image_files)를 content 블록 목록으로 변환한다."""
    image_map = {f.name: f for f in image_files}
    blocks: list[dict] = []

    if text_file and text_file.exists():
        raw = text_file.read_text(encoding="utf-8")
        buf: list[str] = []

        for line in raw.splitlines():
            m = re.match(r"\[페이지 \d+ → 이미지: (page_\d+\.jpg)\]", line)
            if m:
                chunk = "\n".join(buf).strip()
                if chunk:
                    blocks.append({"type": "text", "text": chunk})
                buf = []
                img_path = image_map.get(m.group(1))
                if img_path and img_path.exists():
                    data = base64.standard_b64encode(img_path.read_bytes()).decode()
                    blocks.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
                    })
            else:
                buf.append(line)

        chunk = "\n".join(buf).strip()
        if chunk:
            blocks.append({"type": "text", "text": chunk})

    elif image_files:
        for img_path in sorted(image_files):
            data = base64.standard_b64encode(img_path.read_bytes()).decode()
            blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
            })

    return blocks


def _build_user_content(
    text_file: Path | None,
    image_files: list[Path],
    ans_text_file: Path | None = None,
    ans_image_files: list[Path] | None = None,
) -> list[dict]:
    """LLM 요청의 content 블록 목록을 구성한다. 답지가 있으면 섹션 구분 후 추가."""
    content: list[dict] = []

    if ans_text_file is not None or ans_image_files:
        content.append({"type": "text", "text": "# 문제지"})

    content.extend(_prep_to_blocks(text_file, image_files))

    if ans_text_file is not None or ans_image_files:
        content.append({"type": "text", "text": "# 답지 / 해설\n위 문제들의 정답과 풀이입니다."})
        content.extend(_prep_to_blocks(ans_text_file, ans_image_files or []))

    content.append({"type": "text", "text": _REQUEST_PROMPT})
    return content


# ── YAML 추출 및 검증 ──────────────────────────────────────────────────────────


def _extract_yaml(response: str) -> str | None:
    m = re.search(r"```(?:yaml|YAML)\s*\n(.*?)\n```", response, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"((?:title:|problems:).*)", response, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _normalize_sub_ids(yaml_text: str) -> str:
    """소문제 ID에서 부모 문제 번호 prefix 제거 (예: "10a" → "a", "5-1" → "1")."""
    import yaml as _yaml

    try:
        data = _yaml.safe_load(yaml_text)
    except Exception:
        return yaml_text

    def _fix(problems: list) -> None:
        for item in problems:
            if not isinstance(item, dict):
                continue
            if item.get("kind") == "section":
                _fix(item.get("problems") or [])
                continue
            pid = str(item.get("id", ""))
            subs = item.get("subproblems") or []
            for sub in subs:
                sid = str(sub.get("id", ""))
                if sid.startswith(pid) and len(sid) > len(pid):
                    remainder = sid[len(pid):]
                    # strip separators like '-', '_', '.'
                    sub["id"] = remainder.lstrip("-_.")

    _fix(data.get("problems") or [])
    return _yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _validate_text(yaml_text: str, path: Path):
    from testmagick.io import InputLoadError, load_exam

    path.write_text(yaml_text, encoding="utf-8")
    try:
        return None, load_exam(path)
    except InputLoadError as exc:
        return str(exc), None


def _check_expect(exam, expect_map: dict[str, int]) -> list[tuple[str, int, int]]:
    from testmagick.schema import Section
    actual = {}
    for item in exam.problems:
        probs = item.problems if isinstance(item, Section) else [item]
        for p in probs:
            actual[p.id] = len(p.subproblems or [])
    return [
        (pid, exp, actual.get(pid, 0))
        for pid, exp in expect_map.items()
        if actual.get(pid, 0) < exp
    ]


def _expect_feedback(issues: list[tuple[str, int, int]], yaml_text: str) -> str:
    lines = "\n".join(
        f"- 문제 \"{pid}\": 소문제 {exp}개 필요, 현재 {act}개 ({exp - act}개 누락)"
        for pid, exp, act in issues
    )
    return (
        f"다음 문제에서 소문제가 누락되어 있습니다:\n\n{lines}\n\n"
        "누락된 소문제를 모두 채워서 완성된 YAML을 다시 ```yaml 블록으로 출력해주세요.\n"
        "기존 문제는 그대로 유지하고 누락된 소문제만 추가하세요. 절대 생략하지 마세요.\n\n"
        f"현재 YAML:\n```yaml\n{yaml_text}\n```"
    )


# ── 메인 파이프라인 ────────────────────────────────────────────────────────────


def run_generate(
    pdf_path: Path,
    out_dir: Path,
    *,
    answers_pdf: Path | None = None,
    method: str = "auto",
    dpi: int = 150,
    quality: int = 72,
    model: str = "claude-opus-4-6",
    max_rounds: int = 3,
    no_build: bool = False,
    expect_map: dict[str, int] | None = None,
) -> int:
    _require_anthropic()
    import anthropic

    from testmagick.builder import BuildError, build_exam
    from testmagick.io import InputLoadError
    from testmagick.preprocess import preprocess_pdf

    if not os.getenv("ANTHROPIC_API_KEY"):
        _err("인증 오류", "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        return 1

    client = anthropic.Anthropic()
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 헤더 ──────────────────────────────────────────────────────────────────
    console.print()
    console.rule(
        f"[bold]generate[/bold]  "
        f"[cyan]{escape(str(pdf_path))}[/cyan]  [dim]→[/dim]  "
        f"[cyan]{escape(str(out_dir))}[/cyan]"
    )
    console.print()

    # ── 전처리 ────────────────────────────────────────────────────────────────
    try:
        with console.status("문제지 전처리 중...", spinner="dots"):
            prep = preprocess_pdf(
                pdf_path, out_dir / "prep", method=method, dpi=dpi, quality=quality
            )
    except ImportError as exc:
        _err("전처리", f"의존성 오류: {exc}")
        return 1
    except Exception as exc:
        _err("전처리", str(exc))
        return 1

    img_n = len(prep.image_files)
    prep_detail = f"{prep.method} · {prep.page_count}페이지"
    if img_n:
        prep_detail += f" · 이미지 {img_n}장"
    _ok("문제지 전처리", prep_detail)

    ans_prep = None
    if answers_pdf:
        try:
            with console.status("답지 전처리 중...", spinner="dots"):
                ans_prep = preprocess_pdf(
                    answers_pdf, out_dir / "prep_answers",
                    method=method, dpi=dpi, quality=quality,
                )
        except Exception as exc:
            _err("답지 전처리", str(exc))
            return 1
        ans_img_n = len(ans_prep.image_files)
        ans_detail = f"{ans_prep.method} · {ans_prep.page_count}페이지"
        if ans_img_n:
            ans_detail += f" · 이미지 {ans_img_n}장"
        _ok("답지 전처리", ans_detail)

    system_prompt = prep.schema_ref.read_text(encoding="utf-8")
    messages: list[dict] = [
        {"role": "user", "content": _build_user_content(
            prep.text_file, prep.image_files,
            ans_prep.text_file if ans_prep else None,
            ans_prep.image_files if ans_prep else None,
        )},
    ]

    yaml_path = out_dir / "exam.yaml"
    validated = False
    artifacts = None

    for rnd in range(1, max_rounds + 1):
        console.print()
        console.rule(f"[dim]라운드 {rnd} / {max_rounds}[/dim]", style="dim")
        console.print()

        op_label = "YAML 생성" if rnd == 1 else "YAML 교정"
        response_text = ""
        out_tokens = 0

        # ── LLM 스트리밍 ──────────────────────────────────────────────────────
        try:
            with client.messages.stream(
                model=model,
                max_tokens=16000,
                system=system_prompt,
                messages=messages,
            ) as stream:
                with Live(
                    Text("  시작 중...", style="dim"),
                    console=console,
                    refresh_per_second=12,
                    transient=False,
                ) as live:
                    for chunk in stream.text_stream:
                        response_text += chunk
                        live.update(_stream_preview(response_text))
                final_msg = stream.get_final_message()
                out_tokens = final_msg.usage.output_tokens
        except KeyboardInterrupt:
            console.print("\n\n[dim]중단됨[/dim]")
            return 130
        except anthropic.AuthenticationError:
            _err(op_label, "인증 오류 — ANTHROPIC_API_KEY를 확인하세요")
            return 1
        except anthropic.APIError as exc:
            _err(op_label, str(exc))
            return 1

        _ok(op_label, f"{len(response_text):,}자 · {out_tokens:,} 토큰")
        (out_dir / f"round_{rnd}_response.txt").write_text(response_text, encoding="utf-8")

        # ── YAML 추출 ─────────────────────────────────────────────────────────
        yaml_text = _extract_yaml(response_text)
        if not yaml_text:
            _warn("YAML 추출", "응답에서 YAML 블록을 찾을 수 없음")
            if rnd < max_rounds:
                messages += [
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": (
                        "응답에서 YAML 블록을 찾을 수 없습니다. "
                        "반드시 ```yaml 블록으로 감싸서 완전한 YAML만 다시 출력해주세요."
                    )},
                ]
            continue

        yaml_text = _normalize_sub_ids(yaml_text)
        _ok("YAML 추출", f"{len(yaml_text):,}자")
        (out_dir / f"round_{rnd}.yaml").write_text(yaml_text, encoding="utf-8")

        # ── 스키마 검증 ───────────────────────────────────────────────────────
        err, exam = _validate_text(yaml_text, yaml_path)
        if err is not None:
            short_err = err.splitlines()[0][:80]
            if rnd < max_rounds:
                _warn("스키마 검증", short_err)
                messages += [
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": f"{_CORRECTION_PREFIX}```\n{err}\n```"},
                ]
            else:
                _err("스키마 검증", short_err)
            continue

        _ok("스키마 검증", "통과")

        # ── 문제 수 검증 ──────────────────────────────────────────────────────
        if expect_map:
            issues = _check_expect(exam, expect_map)
            if issues:
                summary = "  ".join(f"{pid}: {act}/{exp}개" for pid, exp, act in issues)
                if rnd < max_rounds:
                    _warn("문제 수 검증", f"누락 {len(issues)}건 — {summary}")
                    messages += [
                        {"role": "assistant", "content": response_text},
                        {"role": "user", "content": _expect_feedback(issues, yaml_text)},
                    ]
                    continue
                else:
                    _warn("문제 수 검증", f"누락 {len(issues)}건 — 최대 라운드 도달")
            else:
                _ok("문제 수 검증", "통과")

        validated = True
        break

    # ── PDF 빌드 ──────────────────────────────────────────────────────────────
    console.print()
    if not no_build and validated:
        try:
            with console.status("PDF 빌드 중...", spinner="dots"):
                artifacts = build_exam(input_path=yaml_path, out_dir=out_dir)
            _ok("PDF 빌드", "완료")
        except (InputLoadError, BuildError) as exc:
            _err("PDF 빌드", str(exc))
            return 1
    elif not validated:
        _warn("PDF 빌드", "검증 실패로 건너뜀")

    # ── 최종 결과 패널 ────────────────────────────────────────────────────────
    console.print()
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", min_width=5)
    grid.add_column(style="cyan")
    grid.add_row("YAML", str(yaml_path.resolve()))
    if artifacts:
        grid.add_row("문제지", str(artifacts.exam_pdf.resolve()))
        grid.add_row("정답지", str(artifacts.answer_pdf.resolve()))

    status = "[green bold]완료[/green bold]" if validated else "[yellow bold]불완전[/yellow bold]"
    border = "green" if validated else "yellow"
    console.print(Panel(grid, title=status, border_style=border, padding=(1, 2)))

    return 0 if validated else 1
