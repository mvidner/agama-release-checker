MAIN = .
check: check-black check-mypy check-pytest
check-black:
	black --diff --check ${MAIN}
check-mypy:
	mypy ${MAIN}
check-pytest:
	PYTHONPATH=src pytest tests/