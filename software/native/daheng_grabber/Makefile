GALAXY_ROOT ?= $(HOME)/Galaxy_camera
CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -fPIC
CPPFLAGS += -I$(GALAXY_ROOT)/inc -I.
LDFLAGS += -L$(GALAXY_ROOT)/lib/x86_64 -Wl,-rpath,$(GALAXY_ROOT)/lib/x86_64
LDLIBS += -lgxiapi -lpthread

LIB := libdaheng_grabber.so
SRC := daheng_grabber.cpp

.PHONY: all clean

all: $(LIB)

$(LIB): $(SRC) daheng_grabber.h
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -shared -o $@ $(SRC) $(LDFLAGS) $(LDLIBS)

# Prefer system/conda g++ — Zig-built .so aborts on Galaxy CNotImplementedError.
# Example: micromamba run -n gxbuild make


clean:
	rm -f $(LIB)
