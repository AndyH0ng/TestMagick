# TestMagick

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](./.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Typst](https://img.shields.io/badge/typst-0.14%2B-239DAD)](https://typst.app/)
[![상태](https://img.shields.io/badge/status-active-6BCC62)](#뉴스)

<p align="center">
<img align="center" src="./docs/images/testmagick-hero.png" alt="TestMagick 대표 이미지" width="420"/>
</p>

## TestMagick란?

TestMagick는 구조화된 문제 파일(YAML/JSON)에서 문제지와 정답지를 자동으로 생성하는 로컬 CLI 도구입니다.
LLM(Claude, GPT 등)과 협업하여 기존 시험지 PDF를 데이터로 변환하고, 이를 Typst 기반으로 조판하여 컴파일합니다.

## 기능 및 특징

TestMagick는 다음 기능을 제공합니다.

- **PDF 파일 전처리 (`preprocess`)**: PDF를 분석하여 텍스트/이미지를 분리 추출하거나 Markdown(LaTeX)으로 변환해 토큰 비용을 최소화
- **LLM 피드백 루프 (`validate --expect`)**: LLM이 생성한 YAML의 문제 누락을 자동 감지하고 재학습용 교정 프롬프트 생성
- **복합 문항 지원**: `subproblems`(소문제), `question_blocks`(수식, 표, 그래프, 조건 박스 등) 스키마 지원
- **Typst 조판 렌더링 (`build`)**: 구조화된 데이터를 기반으로 시험지/해설지 고품질 PDF 일괄 생성

## 설치

사전 준비:

1. Python 3.11 이상
2. [Typst CLI](https://typst.app/docs/installation/) (PDF 컴파일용)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# PDF 전처리 기능을 사용하려면 추가 패키지 설치
pip install -e ".[preprocess]"

# Markdown 변환(marker-pdf) 기능을 사용하려면 추가 패키지 설치
pip install -e ".[markdown]"
```

## 워크플로우 및 사용 방법

### 1. PDF 전처리 (LLM 입력용 변환)
원본 시험지 PDF를 LLM에 전달하기 좋은 형태로 최적화합니다.
```bash
python -m testmagick preprocess input.pdf --out preprocessed/
```
- `preprocessed/` 폴더에 LLM 프롬프트 가이드(`prompt.md`), 스키마 요약(`schema_ref.md`), 그리고 텍스트/이미지 파일이 생성됩니다.
- 옵션: `--method` (`auto`, `mixed`, `text`, `images`, `markdown`)

### 2. 검증 (Validation 및 자동 교정)
LLM이 작성한 YAML 파일의 문법과 구조를 검사합니다.
```bash
python -m testmagick validate --input data/exam.yaml
```
**누락 검사 및 피드백 프롬프트 생성:**
문제가 길어 LLM이 소문제를 누락했는지 확인하려면 `--expect` 옵션을 사용하세요.
```bash
python -m testmagick validate --input data/exam.yaml --expect "1:5, 7:8"
```
기대 개수(예: 1번 문항 5개, 7번 문항 8개)와 다를 경우, LLM에게 다시 복사해 넣을 수 있는 **교정용 프롬프트**를 자동 출력합니다.

### 3. PDF 빌드 (Typst 컴파일)
검증된 YAML 데이터를 바탕으로 Typst 문서를 렌더링하고 PDF로 추출합니다.
```bash
python -m testmagick build --input data/exam.yaml --out out/
```

## 입력 형식 (YAML 스키마)

TestMagick은 유연하고 강력한 스키마를 제공합니다. 자세한 내용은 전처리 시 생성되는 `schema_ref.md`를 참고하세요.

**주요 특징:**
- `mcq`(객관식), `short`(주관식) 타입 지원
- 인라인 수식은 `$ ... $`와 함께 `question_typst` 등에 작성
- `question_blocks`를 통해 가운데 정렬 수식(`formula`), 표(`table`), 그래프(`graph`) 삽입 가능
- 주관식 문항은 `subproblems` 배열을 통해 여러 개의 소문제를 포함 가능

## 출력 결과

`build` 명령을 실행하면 지정한 출력 폴더(`out/`)에 다음 파일들이 생성됩니다.

- `exam.typ` / `answer.typ` (생성된 Typst 소스 코드)
- `exam.pdf` / `answer.pdf` (최종 컴파일된 시험지 및 정답지 PDF)
- `package.zip` (모든 산출물이 압축된 아카이브, `--no-zip`으로 비활성화 가능)
