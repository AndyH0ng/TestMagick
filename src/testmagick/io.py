from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from testmagick.schema import ExamSet


class InputLoadError(RuntimeError):
    """입력 파일 로딩 또는 검증에 실패했을 때 발생하는 예외."""


def load_exam(input_path: Path) -> ExamSet:
    if not input_path.exists():
        raise InputLoadError(f"입력 파일을 찾을 수 없습니다: {input_path}")
    if not input_path.is_file():
        raise InputLoadError(f"입력 경로가 파일이 아닙니다: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")
    suffix = input_path.suffix.lower()
    try:
        if suffix == ".json":
            payload = json.loads(raw_text)
        elif suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw_text)
        else:
            raise InputLoadError("입력 파일 확장자는 .yaml/.yml 또는 .json 이어야 합니다.")
    except json.JSONDecodeError as exc:
        raise InputLoadError(f"JSON 형식이 올바르지 않습니다: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InputLoadError(f"YAML 형식이 올바르지 않습니다: {exc}") from exc

    if not isinstance(payload, dict):
        raise InputLoadError("최상위 입력 객체는 딕셔너리(object)여야 합니다.")

    try:
        return ExamSet.model_validate(payload)
    except ValidationError as exc:
        raise InputLoadError(f"스키마 검증에 실패했습니다:\n{exc}") from exc
