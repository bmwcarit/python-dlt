all:
	true
build:
	true
test:
	mkdir -p junit_reports;
	PYTHONPATH="${PYTHONPATH}:${BCI_SOURCES_DIR}/dlt"
	nosetests tests --with-xunit --xunit-file=junit_reports/python-dlt_tests.xml
