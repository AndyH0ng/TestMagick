# TestMagick

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](./.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Typst](https://img.shields.io/badge/typst-0.14%2B-239DAD)](https://typst.app/)
[![상태](https://img.shields.io/badge/status-active-6BCC62)](#뉴스)

<p align="center">
<img align="center" src="./docs/images/testmagick-hero.png" alt="TestMagick 대표 이미지" width="420"/>
</p>

TestMagick는 구조화된 문제 파일에서 문제지와 정답지를 자동으로 생성하는 로컬 CLI 도구입니다.  
입력 데이터를 Typst 문서로 렌더링한 뒤 PDF로 컴파일하여, 반복적인 시험 대비 문서 작업을 빠르게 처리할 수 있습니다.

## TestMagick란?

TestMagick는 개인 학습/출제 워크플로우를 위해 설계되었습니다.

- 웹 서버 배포 없이 로컬에서 바로 실행
- 문제 데이터를 한 번에 정리하여 반복 출력
- 수식이나 코드가 포함된 문제 깔끔하게 렌더링

## 기능 및 특징

TestMagick는 다음 기능을 제공합니다.

- [Pydantic](https://docs.pydantic.dev/) 기반 입력 스키마 검증
- YAML/JSON 입력 파일 로딩
- Typst 템플릿 렌더링
- 수식 렌더링
- 코드 블록 렌더링

## 설치

사전 준비:

1. Python 3.11 이상
2. Typst CLI

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 입력 형식

입력 파일은 YAML 또는 JSON을 사용할 수 있습니다.

참고 예시:

- `./data/sample_problems.yaml`

다음을 포함해야 합니다:

- `mcq`의 `answer`는 1부터 시작하는 인덱스(예: `2`) 또는 선택지 텍스트
- `short` 문제는 `choices`를 포함하면 안 됨
- 수식/코드 렌더링은 `question_typst`, `choices_typst`, `answer_typst` 사용

## 사용 방법

빠른 실행:

```bash
./run
```

검증만:

```bash
./run validate --input data/sample_problems.yaml
```

PDF 생성:

```bash
./run build --input data/sample_problems.yaml --out out
```

모듈 직접 실행:

```bash
python -m testmagick validate --input data/sample_problems.yaml
python -m testmagick build --input data/sample_problems.yaml --out out
```

## 출력 결과

기본적으로 `out/` 디렉터리에 아래 파일이 생성됩니다.

- `exam.typ`
- `answer.typ`
- `exam.pdf`
- `answer.pdf`
- `package.zip`
