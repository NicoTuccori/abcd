CXX = g++
CXXFLAGS = -fPIC -O3 -Wall -std=c++17 -m64 -DLINUX -pthread

PWD := $(shell pwd)

# Python version and virtual environment
VENV_NAME = abtp2py
PYTHON_VERSION = 3.9
PYTHON_BIN := ./${VENV_NAME}/bin/python
PYTHON_CONFIG := python$(PYTHON_VERSION)-config
PYTHON_INCLUDE := $(shell $(PYTHON_CONFIG) --includes)

PYTHON_LIBS = -lpython$(PYTHON_VERSION)

BOOST_PYTHON_LIB = -lboost_python3 -lboost_regex

LIBS = $(BOOST_PYTHON_LIB) $(PYTHON_LIBS) -liniparser -laio -lrt -lpthread
INCLUDES = $(PYTHON_INCLUDE) $(INIPARSER_INCLUDE) -I$(SRC_PETSYS_RAW) -I$(SRC_PETSYS_DAQD) 

.PHONY: all venv clean petsys_copy build_shm build_daqd build_writeraw

all: venv petsys_copy $(SHM_OUT) $(DAQD_OUT) $(WRITERAW_OUT)

venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Virtualenv NOT active"; \
		if [ ! -d "$(VENV_NAME)" ]; then \
			echo "Create virtualenv $(VENV_NAME) using Python $(PYTHON_VERSION)"; \
			echo "For example, python$(PYTHON_VERSION) -m venv $(VENV_NAME)"; \
		else \
			echo "Virtualenv $(VENV_NAME) exists, please activate it."; \
			echo "For example, source $(VENV_NAME)/bin/activate"; \
		fi; \
		exit 1; \
	else \
		echo "Virtualenv active at $$VIRTUAL_ENV"; \
	fi

clean:
	rm -rf $(PETSYS_DEST)