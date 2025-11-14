

TARGET = dynsch

CC = gcc
LD = $(CC)

SOURCE_PATH  = .
INCLUDE_PATH = .
OBJ_PATH     = obj

CFLAGS     = -g -I$(INCLUDE_PATH) -D_C_EXE_ -std=c++1z
LD_CFLAGS  = -lstdc++ -lm -lcomgraph

SOURCE_FILES  = $(wildcard $(SOURCE_PATH)/*.cpp)
OBJ_FILES     = $(addprefix $(OBJ_PATH)/, $(addsuffix .o,$(notdir $(basename $(SOURCE_FILES)))))

.PHONY:all clean

all: $(TARGET)

$(TARGET): $(OBJ_FILES)
	$(LD) -o $@ $^ $(LD_CFLAGS)
	@cp $(TARGET) -rf /usr/bin/
	
$(OBJ_PATH)/%.o: $(SOURCE_PATH)/%.cpp
	@if [ ! -d $(OBJ_PATH) ];then mkdir $(OBJ_PATH); fi
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf $(OBJ_PATH)
	rm -rf $(TARGET)