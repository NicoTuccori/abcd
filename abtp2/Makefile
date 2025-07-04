CXX = clang++  # or g++
CXXFLAGS = -fPIC -O2 -Wall -std=c++17

# Detect OS
UNAME_S := $(shell uname -s)
PWD := $(shell pwd)

# PETsys paths
PETSYS_DIR := /Users/nt292/PETsys/sussex_petsys
SRC_PETSYS = $(PETSYS_DIR)/src
SRC_PETSYS_LIB = $(SRC_PETSYS)/petsys_py_lib
SRC_PETSYS_RAW = $(SRC_PETSYS)/raw_data

# Python version and virtual environment
VENV_NAME = abtp2py
PYTHON_VERSION = 3.11
PYTHON_BIN := ./${VENV_NAME}/bin/python
PYTHON_CONFIG := python$(PYTHON_VERSION)-config
PYTHON_INCLUDE := $(shell $(PYTHON_CONFIG) --includes)
PYTHON_LIBS := $(shell $(PYTHON_CONFIG) --ldflags)

BOOST_PYTHON_LIB = -lboost_python$(subst .,,$(PYTHON_VERSION))

# OS-specific libraries
ifeq ($(UNAME_S),Linux)
	MACPORTS_PREFIX =
	EXTRA_LIBS = -laio
	INIPARSER_INCLUDE = -I/usr/include/iniparser
else
	MACPORTS_PREFIX = /opt/local
	EXTRA_LIBS =
	INIPARSER_INCLUDE =  # add if needed on macOS
endif

LIBS = $(BOOST_PYTHON_LIB) $(PYTHON_LIBS) -liniparser $(EXTRA_LIBS)
INCLUDES = $(PYTHON_INCLUDE) $(INIPARSER_INCLUDE) -I$(SRC_PETSYS_RAW)

# Files to copy
PETSYS_SCRIPTS = \
	__init__.py tofpet2b.py tofpet2c.py info.py daqd.py bitarray_utils.py config.py \
	spi.py i2c.py bias.py boot.py fe_temperature.py fe_eeprom.py fe_power.py \
	fe_power_8k.py meta.py

# Directory creation target
PETSYS_DEST = $(PWD)/petsys_lib
$(PETSYS_DEST):
	@if [ ! -d "$(PETSYS_DEST)" ]; then \
		mkdir -p "$(PETSYS_DEST)"; \
		echo "Created directory $(PETSYS_DEST)"; \
	else \
		echo "Directory $(PETSYS_DEST) already exists"; \
	fi

# Copy python scripts - pattern rule
$(PETSYS_DEST)/%: $(SRC_PETSYS_LIB)/% | $(PETSYS_DEST)
	cp $< $@

PY_SCRIPTS_DST := $(addprefix $(PETSYS_DEST)/, $(PETSYS_SCRIPTS))

# C++ module
SHM_SRC = $(SRC_PETSYS_RAW)/shm_raw.cpp $(SRC_PETSYS_RAW)/shm_raw_py.cpp
SHM_OUT = $(PETSYS_DEST)/shm_raw.so

# Rule to build shared module; depends on the output directory
$(SHM_OUT): $(SHM_SRC) | $(PETSYS_DEST)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -shared $^ -o $@ \
		-L$(MACPORTS_PREFIX)/lib $(LIBS)

.PHONY: all venv clean petsys_copy build_shm

all: venv petsys_copy $(SHM_OUT)

petsys_copy: $(PY_SCRIPTS_DST)

venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Virtualenv NOT active"; \
		if [ ! -d "$(VENV_NAME)" ]; then \
			echo "Create virtualenv $(VENV_NAME) using Python $(PYTHON_VERSION)"; \
			echo "For example, $(PYTHON_BIN) -m venv $(VENV_NAME)"; \
			echo "For example, python$(PYTHON_VERSION) -m venv $(VENV_NAME)"; \
		else \
			echo "Virtualenv $(VENV_NAME) exists, please activate it."; \
			echo "For example, source $(VENV_NAME)/bin/activate"; \
		fi; \
		exit 1; \
	else \
		echo "Virtualenv active at $$VIRTUAL_ENV"; \
	fi

build_shm: $(SHM_OUT)

clean:
	rm -rf $(PETSYS_DEST)