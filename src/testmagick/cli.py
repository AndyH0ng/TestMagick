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
    validate_parser.add_argument("--input", required=True, type=Path, help="YAML/JSON 입력 파일 경로")

    build_parser = subparsers.add_parser("build", help=".typ/.pdf 및 선택적으로 .zip 출력 파일을 생성합니다.")
    build_parser.add_argument("--input", required=True, type=Path, help="YAML/JSON 입력 파일 경로")
    build_parser.add_argument("--out", type=Path, default=Path("out"), help="출력 디렉터리")
    build_parser.add_argument("--title", type=str, default=None, help="문서 제목 강제 덮어쓰기")
    build_parser.add_argument("--no-zip", action="store_true", help="package.zip 생성을 비활성화합니다.")
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


def _run_validate(input_path: Path) -> int:
    try:
        exam_set = load_exam(input_path)
    except InputLoadError as exc:
        print(f"{_err_tag()} {exc}")
        return 1

    print(f"{_ok_tag()} {input_path}에서 문제 {len(exam_set.problems)}개를 검증했습니다.")
    return 0


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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate(input_path=args.input)
    if args.command == "build":
        return _run_build(
            input_path=args.input,
            out_dir=args.out,
            title=args.title,
            no_zip=args.no_zip,
        )

    parser.print_help()
    return 1
