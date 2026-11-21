CXXFLAGS ?= -O3 -Wall -Wextra -Wpedantic
CORE = src/board.cpp src/eval.cpp src/search.cpp
HEADERS = include/micro.hpp include/weights.hpp src/geometry.hpp

all: build/kittenfishmicro build/micro_tests

build:
	mkdir -p build

build/kittenfishmicro: $(CORE) $(HEADERS) benchmarks/driver.cpp | build
	$(CXX) $(CXXFLAGS) -std=c++14 -Iinclude $(CORE) benchmarks/driver.cpp -o $@

build/micro_tests: $(CORE) $(HEADERS) tests/tests.cpp | build
	$(CXX) $(CXXFLAGS) -std=c++14 -Iinclude $(CORE) tests/tests.cpp -o $@

test: build/micro_tests
	./build/micro_tests

clean:
	rm -rf build

.PHONY: all test clean
