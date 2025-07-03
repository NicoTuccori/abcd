include ../common_definitions.mk

# File names
EXEC = tofpet2

PETSYS_DIR := /Users/nt292/Library/CloudStorage/OneDrive-UniversityofSussex/Documents/Git/sussex_petsys

SOURCES = $(SRC_DIR)/actions.cpp $(SRC_DIR)/states.cpp
OBJECTS = $(SOURCES:.cpp=.o)

CXXFLAGS += -I $(PETSYS_DIR)/src/daqd -I $(PETSYS_DIR)/src/raw_data -I/opt/local/include
LDFLAGS += -L /opt/local/lib -ljansson -L $(PETSYS_DIR)/src/daqd -L $(PETSYS_DIR)/src/raw_data

.PHONY: all clean

all: $(EXEC)

# To obtain object files
%.o: %.cpp
	$(CXX) -c $(CXXFLAGS) $< -o $@

# Main target
$(EXEC): $(OBJECTS) $(EXEC).cpp
	$(CXX) $(CXXFLAGS) $(EXEC).cpp $(OBJECTS) $(LDFLAGS) $(PICO_LIBS) -o $(EXEC)

# To remove generated files
clean:
	rm -f $(EXEC) $(OBJECTS)
