include ../common_definitions.mk

# File names
EXEC = tofpet2

PETSYS_DIR := /home/petsys/sussex_petsys_v4

DAQD_SOURCES = \
    $(PETSYS_DIR)/src/daqd/daqd.cpp \
    $(PETSYS_DIR)/src/daqd/Client.cpp \
    $(PETSYS_DIR)/src/daqd/FrameServer.cpp \
    $(PETSYS_DIR)/src/daqd/UDPFrameServer.cpp \
    $(PETSYS_DIR)/src/daqd/DAQFrameServer.cpp \
    $(PETSYS_DIR)/src/daqd/PFP_KX7.cpp \
    $(PETSYS_DIR)/src/raw_data/shm_raw.cpp

SOURCES = $(DAQD_SOURCES) $(SRC_DIR)/actions.cpp $(SRC_DIR)/states.cpp 

OBJECTS = $(SOURCES:.cpp=.o)

CXXFLAGS += -I $(PETSYS_DIR)/src/daqd -I $(PETSYS_DIR)/src/raw_data -I /usr/include/iniparser
LDFLAGS += -L $(PETSYS_DIR)/src/daqd -L $(PETSYS_DIR)/src/raw_data -lrt -lboost_system -lboost_filesystem -lpthread -laio -ljansson

.PHONY: all clean

all: $(EXEC)

# To obtain object files
%.o: %.cpp
	$(CXX) -c $(CXXFLAGS) $< -o $@

# Main target
$(EXEC): $(OBJECTS) $(EXEC).cpp
	$(CXX) $(CXXFLAGS) $(EXEC).cpp $(OBJECTS) $(LDFLAGS) -o $(EXEC)

# To remove generated files
clean:
	rm -f $(EXEC) $(OBJECTS)
