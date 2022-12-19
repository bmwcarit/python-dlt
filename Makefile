# Non released dlt-daemon version based on 2.18.8
LIBDLT_VERSION=v2.18.8

IMAGE=python-dlt/python-dlt-unittest
TAG?=latest
DK_CMD=docker run --rm -v $(shell pwd):/pydlt -w /pydlt
TEST_ARGS?="-e py3,lint"

.PHONY: all
all:
	@echo "python-dlt testing commands, libdlt version: ${LIBDLT_VERSION}"
	@echo "  make unit-test       -- Run unit tests with tox (Run 'make build-image' the first time)"
	@echo "  make build-image     -- Build docker image for the usage of 'make unit-test'"
	@echo "  make clean           -- Remove all temporary files"

.PHONY: test
test:
	mkdir -p junit_reports;
	nosetests --no-byte-compile \
		--with-xunit --xunit-file=junit_reports/python-dlt_tests.xml \
		tests

.PHONY: unit-test
unit-test:
	${DK_CMD} ${IMAGE}:${TAG} tox ${TEST_ARGS}

.PHONY: lint
lint:
	${DK_CMD} ${IMAGE}:${TAG} tox -e lint

.PHONY: build-image
build-image:
	docker build --build-arg LIBDLT_VERSION=${LIBDLT_VERSION} \
		--tag ${IMAGE}:${TAG} .
	docker build --build-arg LIBDLT_VERSION=${LIBDLT_VERSION} \
		--tag ${IMAGE}:${LIBDLT_VERSION} .

.PHONY: bash
bash:
	${DK_CMD} -it ${IMAGE}:${TAG}

.PHONY: clean
clean:
ifeq (,$(wildcard /.dockerenv))
	${DK_CMD} ${IMAGE}:${TAG} make clean
else
	find . -name "__pycache__" | xargs -n1 rm -rf
	find . -name "*.pyc" | xargs -n1 rm -rf
	rm -rf .coverage
	rm -rf *.egg-info
	rm -rf .eggs
	rm -rf junit_reports
	rm -rf .tox
endif
