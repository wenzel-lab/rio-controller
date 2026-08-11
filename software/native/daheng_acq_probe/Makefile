# Build Daheng C++ Acq.FPS probe (Galaxy SDK).
# Requires: g++, Galaxy headers/libs (default: ~/Galaxy_camera).

GALAXY_ROOT ?= $(HOME)/Galaxy_camera
CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra
CPPFLAGS += -I$(GALAXY_ROOT)/inc
LDFLAGS += -L$(GALAXY_ROOT)/lib/x86_64 -Wl,-rpath,$(GALAXY_ROOT)/lib/x86_64
LDLIBS += -lgxiapi -lpthread

TARGET := daheng_acq_probe
SRC := daheng_acq_probe.cpp

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $< $(LDFLAGS) $(LDLIBS)

clean:
	rm -f $(TARGET)

# Stop Rio / Galaxy first — camera is exclusive.
run: $(TARGET)
	./$(TARGET) --sn $${RIO_DAHENG_SN:-FDQ23120254} --width 200 --height 200 --exposure-us 20 --seconds 15
