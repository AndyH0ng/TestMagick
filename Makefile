PYTHON ?= python3
INPUT ?= data/sample_problems.yaml
OUT ?= out

.PHONY: install validate build test lint

install:
	$(PYTHON) -m pip install -e ".[dev]"

validate:
	PYTHONPATH=src $(PYTHON) -m testmagick validate --input $(INPUT)

build:
	PYTHONPATH=src $(PYTHON) -m testmagick build --input $(INPUT) --out $(OUT)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
