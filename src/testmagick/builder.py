from __future__ import annotations

import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from testmagick.io import load_exam
from testmagick.renderer import render_typst_files


class BuildError(RuntimeError):
    """문서 생성 또는 컴파일 단계가 실패했을 때 발생하는 예외."""


@dataclass(frozen=True)
class BuildArtifacts:
    exam_typ: Path
    answer_typ: Path
    exam_pdf: Path
    answer_pdf: Path
    package_zip: Path | None


def ensure_typst_available() -> None:
    if shutil.which("typst") is None:
        raise BuildError(
            "PATH에서 typst CLI를 찾을 수 없습니다. Typst 설치 후 `typst --version`으로 확인하세요."
        )


def compile_typst(input_typ: Path, output_pdf: Path) -> None:
    cmd = ["typst", "compile", str(input_typ), str(output_pdf)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        error_detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise BuildError(f"{input_typ.name} 컴파일에 실패했습니다: {error_detail}") from exc


def create_package(package_path: Path, files: list[Path]) -> Path:
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            zf.write(file_path, arcname=file_path.name)
    return package_path


def build_exam(
    input_path: Path,
    out_dir: Path,
    title_override: str | None = None,
    include_zip: bool = True,
) -> BuildArtifacts:
    ensure_typst_available()
    exam_set = load_exam(input_path)
    rendered = render_typst_files(exam_set=exam_set, out_dir=out_dir, title_override=title_override)

    exam_pdf = out_dir / "exam.pdf"
    answer_pdf = out_dir / "answer.pdf"

    compile_typst(rendered.exam_typ, exam_pdf)
    compile_typst(rendered.answer_typ, answer_pdf)

    package_zip: Path | None = None
    if include_zip:
        package_zip = create_package(out_dir / "package.zip", [exam_pdf, answer_pdf])

    return BuildArtifacts(
        exam_typ=rendered.exam_typ,
        answer_typ=rendered.answer_typ,
        exam_pdf=exam_pdf,
        answer_pdf=answer_pdf,
        package_zip=package_zip,
    )
