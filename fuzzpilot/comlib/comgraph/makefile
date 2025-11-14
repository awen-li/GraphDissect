

TARGET = libcomgraph.so

CC = g++
LD = $(CC)

SOURCE_PATH  = source
INCLUDE_PATH = include
OBJ_PATH     = obj
INSTALL_HEADER = /usr/include/comgraph
INSTALL_HEADER2 = /root/anaconda3/include/comgraph

CFLAGS     = -fPIC -O3 -I$(INCLUDE_PATH) #-D__DEBUG__ 
LD_CFLAGS  = -fPIC -shared -lstdc++ 

SOURCE_FILES  = $(wildcard $(SOURCE_PATH)/*.cpp)
OBJ_FILES     = $(addprefix $(OBJ_PATH)/, $(addsuffix .o,$(notdir $(basename $(SOURCE_FILES)))))

.PHONY:all clean

all: $(TARGET)

$(TARGET): $(OBJ_FILES)
	$(LD) -o $@ $^ $(LD_CFLAGS)
	@cp $(TARGET) -rf /usr/lib/
	@if [ -d "/root/anaconda3" ];then cp $(TARGET) -rf /root/anaconda3/lib/;fi
	@if [ ! -d $(INSTALL_HEADER) ];then mkdir $(INSTALL_HEADER); fi
	@cp $(INCLUDE_PATH)/* -rf $(INSTALL_HEADER)/
	@if [ ! -d $(INSTALL_HEADER2) ];then mkdir -p $(INSTALL_HEADER2); fi
	@cp $(INCLUDE_PATH)/* -rf $(INSTALL_HEADER2)/
	
$(OBJ_PATH)/%.o: $(SOURCE_PATH)/%.cpp
	@if [ ! -d $(OBJ_PATH) ];then mkdir $(OBJ_PATH); fi
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf $(OBJ_PATH)
	rm -rf $(TARGET)
