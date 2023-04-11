.PHONY: test
test:
	tox

.PHONY: hooks
hooks:
	tox -re pre-commit --notest
	.tox/pre-commit/bin/pre-commit install
	.tox/pre-commit/bin/pre-commit install-hooks
