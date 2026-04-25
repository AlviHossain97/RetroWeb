PROJ    := RedRacer_Phys
TARGET  := $(PROJ)
OBJS    := main.o

# Toolchain definitions (devkitARM)
DEVKITARM := c:/devkitPro/devkitARM
PREFIX  := $(DEVKITARM)/bin/arm-none-eabi-
CC   := $(PREFIX)gcc
LD   := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy

# Architecture flags
ARCH    := -mthumb-interwork -mthumb
SPECS   := -specs=gba.specs

# Compiler flags
CFLAGS  := $(ARCH) -O2 -Wall -fno-strict-aliasing

# Linker flags
LDFLAGS := $(ARCH) $(SPECS)

.PHONY : build clean

build: $(TARGET).gba

# Tools
GBAFIX := c:/devkitPro/tools/bin/gbafix

$(TARGET).gba : $(TARGET).elf
	$(OBJCOPY) -v -O binary $< $@
	-@$(GBAFIX) $@

$(TARGET).elf : $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) -o $@

main.o : main.c gba.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	@rm -f *.o *.elf *.gba
