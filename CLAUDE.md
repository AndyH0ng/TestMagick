# TestMagick — LLM 작업 가이드

## 프로젝트 개요

TestMagick은 **YAML/JSON 파일**을 입력받아 **문제지(exam.pdf)** 와 **정답지(answer.pdf)** 를 생성하는 CLI 도구입니다. 렌더링 엔진으로 Typst를 사용합니다.

---

## 빌드 명령

```bash
# 빌드 (PDF 생성)
./run build --input data/my_exam.yaml --out out/

# 검증만 (PDF 생성 없이 스키마 확인)
./run validate --input data/my_exam.yaml

# PDF 전처리 (LLM 파이프라인용)
./run preprocess --input data/textbook.pdf --out out/prep/
./run preprocess --input data/textbook.pdf --method mixed  # 페이지별 수식 감지
./run preprocess --input data/textbook.pdf --method markdown  # marker-pdf 변환 (별도 설치 필요)
```

> `preprocess` 의존성: `pip install testmagick[preprocess]` (pymupdf) 또는 `testmagick[markdown]` (pymupdf + marker-pdf)

---

## YAML 최상위 구조

```yaml
title: "시험지 제목"          # 선택 (기본: "제목 없는 시험지")
course: "과목명"              # 선택
date: "2026-03-16"           # 선택
problems:
  - ...                      # 문제 목록 (1개 이상 필수)
```

---

## 문제(Problem) 기본 구조

```yaml
- id: "Q1"                   # 필수, 고유한 문자열
  type: "mcq"                # 필수: "mcq"(객관식) 또는 "short"(주관식)
  question: "문제 텍스트"     # question 또는 question_typst 또는 question_blocks 중 하나 필수
  answer: 2                  # mcq: 1-based 번호 또는 선택지 텍스트 / short: 정답 텍스트
  points: 2.0                # 선택 (기본: 1.0)
  source: "출처"              # 선택
```

---

## 문제 텍스트 3가지 방식

### 1. 일반 텍스트 (`question`)

```yaml
question: "다음 중 올바른 것을 고르시오."
```

### 2. Typst 코드 (`question_typst`)

수식이나 코드블록이 포함된 경우 사용합니다.

```yaml
question_typst: |
  방정식 $x^2 - 5x + 6 = 0$의 해를 모두 구하시오.
```

```yaml
question_typst: |
  아래 코드의 출력을 쓰시오.
  #raw(block: true, lang: "python", "for i in range(3):\n    print(i)")
```

### 3. 구조화 블록 (`question_blocks`)

표, 수식, 요구사항 등을 구조적으로 삽입합니다. `question`/`question_typst`와 **함께 쓸 수 있습니다** (question이 먼저 출력됨).

---

## 콘텐츠 블록 (`question_blocks`) 종류

### `text` — 일반 텍스트

```yaml
question_blocks:
  - type: text
    content: "본문 텍스트입니다."
```

### `typst` — 원시 Typst 코드

```yaml
question_blocks:
  - type: typst
    content: |
      #raw(block: true, lang: "python", "print('hello')")
```

### `formula` — 가운데 정렬 수식

`content`에 `$` 없이 Typst 수학 표현식을 씁니다.

```yaml
question_blocks:
  - type: formula
    content: "S_n = n/2 (2a + (n-1)d)"
```

렌더 결과: 수식이 가운데 정렬되어 표시됩니다.

### `requirements` — 요구사항/조건 텍스트

회색 왼쪽 테두리가 있는 이탤릭 블록으로 표시됩니다.

```yaml
question_blocks:
  - type: requirements
    content: "단, 소수점 첫째 자리에서 반올림하시오."
```

### `graph` — 방향 그래프

노드(원)와 엣지(화살표)로 이루어진 방향 그래프를 그립니다. `label`이 있으면 간선 중점에 표시됩니다.

```yaml
question_blocks:
  - type: graph
    nodes:
      - id: "A"
        label: "$A$"    # Typst 콘텐츠; 생략하면 id가 표시됨
        pos: [0, 0]     # [x, y] 좌표 (y축 아래가 양수)
      - id: "B"
        label: "$B$"
        pos: [3, 0]
      - id: "C"
        label: "$C$"
        pos: [0, -3]
      - id: "D"
        label: "$D$"
        pos: [3, -3]
    edges:
      - from: "A"
        to: "B"                  # 단방향 화살표 A → B
      - from: "B"
        to: "C"
        bend: 40                 # 곡선: 양수=진행방향 왼쪽, 음수=오른쪽
      - from: "C"
        to: "D"
        directed: false          # 방향 없는 선 (기본: true)
      - from: "D"
        to: "A"
        bidirectional: true      # 양방향 화살표 ↔
        label: "5"               # 간선 레이블 (선택)
```

- **노드 id**: 빈 문자열 불가, 공백 자동 제거.
- **좌표계**: `x`는 오른쪽, `y`는 **위**가 양수 (수학 좌표계). 노드 간격은 `3`~`4` 권장.
- **이탤릭 라벨** (수학 기호 느낌): `label: "$A$"`. 일반 텍스트: `label: "A"`.
- **bend 방향**: 화살표의 진행 방향 기준.
  - `bend: 50` → 진행 방향 **왼쪽**으로 호 (예: 위로 가는 엣지 → 왼쪽 바깥)
  - `bend: -50` → 진행 방향 **오른쪽**으로 호 (예: 위로 가는 엣지 → 오른쪽 바깥)
  - 바깥쪽 큰 호는 절댓값 `50`~`70` 권장. 값이 클수록 더 크게 굽음.
  - 팁: 그래프 오른쪽 세로 엣지(아래→위)에서 오른쪽 바깥으로 보내려면 `bend: -40`.

### `table` — 표

```yaml
question_blocks:
  - type: table
    headers: ["구분", "2022년", "2023년"]  # 선택 (없으면 첫 번째 행이 기준 열 수)
    rows:
      - ["매출(억원)", "1,200", "1,500"]
      - ["영업이익(억원)", "150", "200"]
```

- `headers` 또는 `rows` 중 최소 하나는 있어야 합니다.
- 모든 행의 열 수는 `headers`(또는 첫 번째 행)와 일치해야 합니다.
- 첫 번째 행은 자동으로 회색 배경 + 볼드 처리됩니다.

---

## 객관식 문제 (`type: "mcq"`)

```yaml
- id: "Q1"
  type: "mcq"
  question: "다음 중 OOP의 4대 원칙이 아닌 것은?"
  choices:
    - "캡슐화"
    - "상속"
    - "컴파일"
    - "다형성"
  answer: 3          # 1-based 번호. "컴파일"이 정답
  points: 2
```

**Typst 선택지** (수식 포함 시):

```yaml
choices_typst:
  - "$x = 1, 2$"
  - "$x = 2, 3$"
  - "$x = -2, -3$"
  - "$x = 3, 6$"
answer: 2
```

- `choices`와 `choices_typst` 둘 다 쓸 경우 길이가 같아야 합니다.
- 선택지 레이블은 ①②③… 원 안의 숫자로 자동 표시됩니다.
- 객관식에도 `answer_typst` 사용 가능 — 선택지 번호(①)는 유지되고 해설을 Typst로 작성할 수 있습니다.

```yaml
# 객관식 + 해설 예시
- id: "Q1"
  type: "mcq"
  question: "다음 중 참인 것은?"
  choices: ["참", "거짓"]
  answer: 2
  answer_typst: |
    거짓이다. 반례: $x = 0$일 때 성립하지 않는다.
```

---

## 주관식 문제 (`type: "short"`)

```yaml
- id: "Q2"
  type: "short"
  question: "뉴턴의 제2법칙을 서술하시오."
  answer: "F = ma (힘 = 질량 × 가속도)"
  points: 3
```

**Typst 정답** (수식/코드 포함 시):

```yaml
answer_typst: |
  $F = m a$
  (힘은 질량과 가속도의 곱이다)
```

---

## 소문제 (`subproblems`)

주관식 문제(`type: "short"`)에만 사용 가능합니다. `subproblems`가 있으면 부모 문제에 `answer`/`answer_typst`를 쓰지 않습니다. 소문제는 객관식/주관식 모두 가능하며, 객관식 소문제에도 `answer_typst`로 해설을 작성할 수 있습니다.

```yaml
- id: "S1"
  type: "short"
  question: "다음 자료를 보고 물음에 답하시오."
  question_blocks:
    - type: table
      headers: ["이름", "국어", "수학"]
      rows:
        - ["김철수", "85", "92"]
        - ["이영희", "90", "75"]
  subproblems:
    - id: "(1)"
      type: "short"
      question: "수학 점수가 더 높은 학생을 쓰시오."
      answer: "김철수"
      points: 1
    - id: "(2)"
      type: "mcq"
      question: "두 학생의 국어 점수 합은?"
      choices: ["170", "175", "180", "185"]
      answer: 2
      points: 1
  points: 2
```

소문제의 `id`는 `(1)`, `(가)`, `a.` 등 자유롭게 사용 가능합니다.

---

## 블록 혼합 사용 예시

```yaml
- id: "COMB"
  type: "short"
  question: "다음을 보고 물음에 답하시오."
  question_blocks:
    - type: table
      headers: ["연도", "매출", "이익"]
      rows:
        - ["2021", "100", "10"]
        - ["2022", "120", "15"]
    - type: requirements
      content: "단, 단위는 억원이며 소수점 이하는 버린다."
    - type: formula
      content: "이익률 = 이익 / 매출 times 100%"
  subproblems:
    - id: "(1)"
      type: "short"
      question: "2022년의 이익률을 구하시오."
      answer: "12.5%"
      points: 2
    - id: "(2)"
      type: "short"
      question: "전년 대비 매출 증가율을 구하시오."
      answer: "20%"
      points: 2
  points: 4
```

---

## Typst 수학 문법 요약

| 표현 | Typst 문법 |
|------|-----------|
| 인라인 수식 | `$x^2 + 1$` |
| 분수 | `$a/b$` 또는 `$frac(a, b)$` |
| 제곱근 | `$sqrt(x)$` |
| 시그마 | `$sum_(i=1)^n x_i$` |
| 적분 | `$integral_0^1 f(x) dif x$` |
| 행렬 | `$mat(a, b; c, d)$` |
| 절댓값 | `$|x|$` |
| 화살표 | `$A -> B$` |
| 이상/이하 | `$x >= 0$`, `$x <= 1$` |
| 그리스 문자 | `$alpha$`, `$beta$`, `$pi$`, `$mu$` |
| 벡터 | `$arrow(v)$` |

---

## 문제지 사진 → YAML 변환 시 지침

문제지 이미지를 보고 YAML을 생성할 때:

1. **문제 번호**를 `id`로 사용 (`"1"`, `"Q1"`, `"문1"` 등).
2. **수식**이 있으면 `question_typst` 또는 `formula` 블록 사용.
3. **표**가 있으면 `table` 블록으로 구조화.
4. **"단, ..."으로 시작하는 조건문**은 `requirements` 블록.
5. **소문제((1)(2)(3) 또는 (가)(나)(다))**는 `subproblems` 사용.
6. **정답**은 객관식은 번호(1-based int), 주관식은 문자열.
7. 수식이 있는 정답은 `answer_typst` 사용.
8. `points`가 명시되어 있으면 그 값을 사용.

### 검증

YAML 작성 후 반드시 스키마 검증을 실행하세요:

```bash
./run validate --input data/my_exam.yaml
```
