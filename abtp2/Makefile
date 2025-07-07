CXX = g++
CXXFLAGS = -fPIC -O3 -Wall -std=c++17 -m64 -DLINUX -pthread

PWD := $(shell pwd)

# PETsys paths
PETSYS_DIR := /home/petsys/sw_daq_tofpet2_abcd
SRC_PETSYS = $(PETSYS_DIR)/src
SRC_PETSYS_LIB = $(SRC_PETSYS)/petsys_py_lib
SRC_PETSYS_RAW = $(SRC_PETSYS)/raw_data
SRC_PETSYS_DAQD = $(SRC_PETSYS)/daqd
SHM_SRC = $(SRC_PETSYS_RAW)/shm_raw.cpp $(SRC_PETSYS_RAW)/shm_raw_py.cpp
SHM_OUT = $(PETSYS_DEST)/shm_raw.so

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

# Files to copy
PETSYS_PY_LIB = \
	__init__.py tofpet2b.py tofpet2c.py info.py daqd.py bitarray_utils.py config.py \
	spi.py i2c.py bias.py boot.py fe_temperature.py fe_eeprom.py fe_power.py \
	fe_power_8k.py # meta.py

# Directory creation target
PETSYS_DEST = $(PWD)/abtp2_py_lib/petsys_lib
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

PY_SCRIPTS_DST := $(addprefix $(PETSYS_DEST)/, $(PETSYS_PY_LIB))

# C++ module
SHM_SRC = $(SRC_PETSYS_RAW)/shm_raw.cpp $(SRC_PETSYS_RAW)/shm_raw_py.cpp
SHM_OUT = $(PETSYS_DEST)/shm_raw.so

# Rule to build shared module; depends on the output directory
$(SHM_OUT): $(SHM_SRC) | $(PETSYS_DEST)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -shared $^ -o $@ $(LIBS)

# Daqd daemon
DAQD_SOURCES := \
	$(SRC_PETSYS_DAQD)/daqd.cpp \
	$(SRC_PETSYS_DAQD)/Client.cpp \
	$(SRC_PETSYS_DAQD)/FrameServer.cpp \
	$(SRC_PETSYS_DAQD)/UDPFrameServer.cpp \
	$(SRC_PETSYS_DAQD)/DAQFrameServer.cpp \
	$(SRC_PETSYS_DAQD)/PFP_KX7.cpp \
	$(SRC_PETSYS_RAW)/shm_raw.cpp

DAQD_OUT = $(PETSYS_DEST)/daqd

$(DAQD_OUT):
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $(DAQD_SOURCES) $(LIBS)

# Compilation rule
%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

.PHONY: all venv clean petsys_copy build_shm build_daqd

all: venv petsys_copy $(SHM_OUT) $(DAQD_OUT)

petsys_copy: $(PY_SCRIPTS_DST)

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

build_shm: $(SHM_OUT)

build_daqd: $(DAQD_OUT)

clean:
	rm -rf $(PETSYS_DEST)