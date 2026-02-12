MAIN = .
check: check-black check-mypy
check-black:
	black --diff --check ${MAIN}
check-mypy:
	mypy ${MAIN}