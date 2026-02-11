MAIN = agama-release-checker.py
check: check-black check-mypy
check-black:
	black --diff --check ${MAIN}
check-mypy:
	mypy ${MAIN}