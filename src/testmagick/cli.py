from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from testmagick.builder import BuildError, build_exam
from testmagick.io import InputLoadError, load_exam


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testmagick",
        description="Typst를 사용해 YAML/JSON 입력으로 문제지/정답지 PDF를 생성합니다.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="입력 파일 스키마만 검증합니다.")
    validate_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="YAML/JSON 입력 파일 경로",
    )
    validate_parser.add_argument(
        "--expect",
        type=str,
        default=None,
        metavar="SPEC",
        help=(
            "소문제 기대치 지정. 형식: '문제ID:개수,...' "
            "(예: '1:5,7:8,8:3'). 실제와 다르면 LLM 교정 프롬프트를 출력."
        ),
    )

    build_parser = subparsers.add_parser(
        "build",
        help=".typ/.pdf 및 선택적으로 .zip 출력 파일을 생성합니다.",
    )
    build_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="YAML/JSON 입력 파일 경로",
    )
    build_parser.add_argument(
        "--out",
        type=Path,
        default=Path("out"),
        help="출력 디렉터리",
    )
    build_parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="문서 제목 강제 덮어쓰기",
    )
    build_parser.add_argument(
        "--no-zip",
        action="store_true",
        help="package.zip 생성을 비활성화합니다.",
    )

    preprocess_parser = subparsers.add_parser(
        "preprocess",
        help="PDF를 LLM 전달용으로 전처리합니다 (텍스트 추출 또는 이미지 압축).",
    )
    preprocess_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="입력 PDF 파일 경로",
    )
    preprocess_parser.add_argument(
        "--out",
        type=Path,
        default=Path("out/prep"),
        help="출력 디렉터리 (기본: out/prep)",
    )
    preprocess_parser.add_argument(
        "--method",
        choices=["auto", "mixed", "text", "images", "markdown"],
        default="auto",
        help=(
            "처리 방식: auto=자동감지(기본), mixed=페이지별 수식 감지,"
            " text=텍스트 강제, images=이미지 강제,"
            " markdown=AI 수식 인식 후 LaTeX Markdown 출력 (marker-pdf 필요)"
        ),
    )
    preprocess_parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="이미지 모드 해상도 (기본: 150)",
    )
    preprocess_parser.add_argument(
        "--quality",
        type=int,
        default=72,
        help="JPEG 압축 품질 0-100 (기본: 72)",
    )

    return parser


def _supports_color() -> bool:
    force_color = os.getenv("FORCE_COLOR")
    if force_color is not None and force_color != "0":
        return True
    if os.getenv("NO_COLOR") is not None:
        return False
    term = os.getenv("TERM", "")
    if term.lower() == "dumb":
        return False
    return sys.stdout.isatty()


def _color(text: str, code: str) -> str:
    if not _supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def _badge(label: str, style_code: str) -> str:
    plain = f"[{label}]"
    if not _supports_color():
        return plain
    return f"\033[{style_code}m {label} \033[0m"


def _ok_tag() -> str:
    # Vite 출력처럼 배경색이 있는 배지 스타일
    return _badge("DONE", "30;48;2;107;204;98;1")


def _err_tag() -> str:
    # Vite 출력처럼 배경색이 있는 배지 스타일
    return _badge("ERROR", "30;48;2;255;107;122;1")


def _path_label(text: str) -> str:
    return _color(text, "36")


def _parse_expect(spec: str) -> dict[str, int]:
    """'1:5,7:8,8:3' 형식을 {problem_id: expected_count} 딕셔너리로 파싱."""
    result: dict[str, int] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"--expect 형식 오류: '{part}' (올바른 형식: '문제ID:개수')")
        pid, count_str = part.rsplit(":", 1)
        result[pid.strip()] = int(count_str.strip())
    return result


def _make_feedback_prompt(input_path: Path, issues: list[tuple[str, int, int]]) -> str:
    yaml_text = input_path.read_text(encoding="utf-8")
    missing_lines = "\n".join(
        f"- 문제 \"{pid}\": 소문제 {exp}개 필요, 현재 {act}개 ({exp - act}개 누락)"
        for pid, exp, act in issues
    )
    return (
        "다음 YAML 파일에서 소문제가 누락되어 있습니다.\n\n"
        f"[누락 항목]\n{missing_lines}\n\n"
        "[현재 YAML]\n"
        "```yaml\n"
        f"{yaml_text.rstrip()}\n"
        "```\n\n"
        "[요청]\n"
        "누락된 소문제를 모두 채워서 완성된 YAML을 출력해주세요.\n"
        "기존 문제는 그대로 유지하고, 누락된 소문제만 추가하세요.\n"
        "절대 생략하거나 '...' 처리하지 마세요."
    )


def _run_validate(input_path: Path, expect: str | None = None) -> int:
    try:
        exam_set = load_exam(input_path)
    except InputLoadError as exc:
        print(f"{_err_tag()} {exc}")
        return 1

    problems = exam_set.problems
    total_sub = sum(len(p.subproblems) for p in problems if p.subproblems)
    total_pts = sum(
        sum(s.points for s in p.subproblems) if p.subproblems else p.points
        for p in problems
    )

    print(f"{_ok_tag()} 검증 완료: {_color(str(input_path), '36')}")
    print()

    col_n   = max(len(str(len(problems))), 1)
    col_id  = max((len(p.id) for p in problems), default=2)
    col_pts = 6

    header = (
        f"  {'#':>{col_n}}  "
        f"{'ID':<{col_id}}  "
        f"{'배점':>{col_pts}}  "
        f"소문제"
    )
    print(_color(header, "2"))
    print(_color("  " + "─" * (len(header) - 2), "2"))

    for i, p in enumerate(problems, 1):
        if p.subproblems:
            pts = sum(s.points for s in p.subproblems)
            sub_ids = " ".join(s.id for s in p.subproblems)
            sub_summary = f"{len(p.subproblems)}개  {_color(sub_ids, '2')}"
        else:
            pts = p.points
            sub_summary = _color("─", "2")

        pts_str = f"{pts:.1f}pt"
        print(f"  {i:>{col_n}}  {p.id:<{col_id}}  {pts_str:>{col_pts}}  {sub_summary}")

    print()
    parts = [
        f"문제 {len(problems)}개",
        f"소문제 {total_sub}개" if total_sub else None,
        f"총 {total_pts:.1f}pt",
    ]
    print("  " + "  |  ".join(p for p in parts if p))
    print()

    if not expect:
        return 0

    try:
        expected_map = _parse_expect(expect)
    except ValueError as exc:
        print(f"{_err_tag()} {exc}")
        return 1

    actual_map = {p.id: len(p.subproblems or []) for p in problems}
    issues: list[tuple[str, int, int]] = []
    for pid, exp_count in expected_map.items():
        act_count = actual_map.get(pid, 0)
        if act_count < exp_count:
            issues.append((pid, exp_count, act_count))

    if not issues:
        print(f"{_ok_tag()} 소문제 수가 기대치와 일치합니다.")
        print()
        return 0

    warn_tag = _badge("WARN", "30;48;2;255;190;0;1")
    print(f"{warn_tag} 소문제 부족 — {len(issues)}개 문제에서 누락 발견\n")
    for pid, exp, act in issues:
        print(f"  문제 {_color(pid, '1')}: 예상 {exp}개, 실제 {act}개 "
              f"({_color(str(exp - act) + '개 누락', '33')})")
    print()
    print(_color("── LLM 교정 프롬프트 (복사해서 LLM에 붙여넣기) ──", "2"))
    print()
    print(_make_feedback_prompt(input_path, issues))
    print()
    return 1


def _run_build(input_path: Path, out_dir: Path, title: str | None, no_zip: bool) -> int:
    try:
        artifacts = build_exam(
            input_path=input_path,
            out_dir=out_dir,
            title_override=title,
            include_zip=not no_zip,
        )
    except (InputLoadError, BuildError) as exc:
        print(f"{_err_tag()} {exc}")
        return 1

    print(f"{_ok_tag()} 빌드를 마쳤습니다.")
    print(f"- {_path_label('문제지 typ:')} {artifacts.exam_typ.resolve()}")
    print(f"- {_path_label('정답지 typ:')} {artifacts.answer_typ.resolve()}")
    print(f"- {_path_label('문제지 pdf:')} {artifacts.exam_pdf.resolve()}")
    print(f"- {_path_label('정답지 pdf:')} {artifacts.answer_pdf.resolve()}")
    if artifacts.package_zip is not None:
        print(f"- {_path_label('압축파일:')}   {artifacts.package_zip.resolve()}")
    return 0


_REASON_LABEL: dict[str, str] = {
    "math_font": "수식 폰트",
    "low_quality": "텍스트 품질 낮음",
    "no_text": "텍스트 없음",
    "text_ok": "텍스트",
    "forced_text": "텍스트(강제)",
    "forced_images": "이미지(강제)",
}


def _run_preprocess(
    pdf_path: Path,
    out_dir: Path,
    method: str,
    dpi: int,
    quality: int,
) -> int:
    from testmagick.preprocess import preprocess_pdf

    try:
        result = preprocess_pdf(
            pdf_path,
            out_dir,
            method=method,  # type: ignore[arg-type]
            dpi=dpi,
            quality=quality,
        )
    except ImportError as exc:
        print(f"{_err_tag()} {exc}")
        return 1
    except Exception as exc:
        print(f"{_err_tag()} PDF 전처리 실패: {exc}")
        return 1

    method_labels = {
        "text": "텍스트 추출",
        "images": f"이미지 압축 ({dpi} dpi · JPEG {quality}%)",
        "mixed": f"mixed (페이지별 수식 감지 · 이미지 {dpi} dpi)",
        "markdown": "AI 수식 인식 → LaTeX Markdown (marker-pdf)",
    }
    method_label = method_labels.get(result.method, result.method)

    img_pages = sum(1 for d in result.page_decisions if d.use_image)
    txt_pages = result.page_count - img_pages

    print(f"{_ok_tag()} 전처리 완료 [{method_label}] — {result.page_count}페이지")
    print()

    # 페이지별 결정 표 (mixed 모드일 때만)
    if result.method == "mixed":
        for d in result.page_decisions:
            bar = "▓" if not d.use_image else "░"
            kind = _REASON_LABEL.get(d.reason, d.reason)
            score_str = f"  score={d.quality_score:.2f}" if d.reason != "no_text" else ""
            print(f"  p{d.page_num:>2}  {bar}  {kind}{score_str}")
        print()
        print(f"  텍스트 페이지: {txt_pages}  /  이미지 페이지: {img_pages}")
        print()

    # 출력 파일 목록
    for f in result.all_files:
        size_kb = f.stat().st_size / 1024
        print(f"  {_path_label(f.name):<26} {size_kb:>7.1f} KB")
    schema_kb = result.schema_ref.stat().st_size / 1024
    print(f"  {_path_label('schema_ref.md'):<26} {schema_kb:>7.1f} KB")
    print(f"  {_path_label('prompt.md')}")
    print()

    # 토큰 추정
    schema_tokens = int(schema_kb * 1024 / 3.5)
    total_tokens = result.est_tokens + schema_tokens
    print(f"  {'추정 토큰 (본문)':<20} ~{result.est_tokens:>6,}")
    print(f"  {'스키마 참조':<20} ~{schema_tokens:>6,}")
    print(f"  {'합계':<20} ~{total_tokens:>6,}")

    if result.method in ("images", "mixed") and img_pages > 0:
        import math
        orig_w = int((1240 / 150) * 300)
        orig_h = int((1754 / 150) * 300)
        orig_tiles = math.ceil(orig_w / 512) * math.ceil(orig_h / 512)
        orig_img_tokens = orig_tiles * 170 * img_pages
        cur_img_tokens = result.est_tokens  # 근사
        if orig_img_tokens > 0:
            saved_pct = max(0.0, (1 - cur_img_tokens / orig_img_tokens) * 100)
            print(f"\n  이미지 {img_pages}페이지 기준, 300dpi 대비 ~{saved_pct:.0f}% 토큰 절감")

    print(f"\n출력 경로: {_path_label(str(out_dir.resolve()))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate(input_path=args.input, expect=args.expect)
    if args.command == "build":
        return _run_build(
            input_path=args.input,
            out_dir=args.out,
            title=args.title,
            no_zip=args.no_zip,
        )
    if args.command == "preprocess":
        return _run_preprocess(
            pdf_path=args.input,
            out_dir=args.out,
            method=args.method,
            dpi=args.dpi,
            quality=args.quality,
        )

    parser.print_help()
    return 1
