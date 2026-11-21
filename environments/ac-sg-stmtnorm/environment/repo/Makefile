.PHONY: test ci cov-html

test:
	python -m pytest -q

# What CI runs on every merge request.
ci:
	python -m coverage erase
	python -m coverage run -m pytest -q
	python -m coverage report

cov-html:
	python -m coverage html
