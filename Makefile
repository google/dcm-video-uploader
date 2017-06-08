.DEFAULT_GOAL := build
.PHONY: clean build

dfareporting_utils.py:
	curl https://raw.githubusercontent.com/googleads/googleads-dfa-reporting-samples/master/python/v2_7/dfareporting_utils.py > dfareporting_utils.py

build: dfareporting_utils.py
	pip install -r requirements.txt

clean:
	rm dfareporting_utils.py
