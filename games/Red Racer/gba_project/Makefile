PROJ    := RedRacer_Phys
TARGET  := $(PROJ)
OBJS    := main.o

# Toolchain definitions (devkitARM) — env-var driven so Linux + Windows both
# work. On Linux: install via `sudo dkp-pacman -S gba-dev`, defaults to
# /opt/devkitpro. On Windows: export DEVKITPRO=C:/devkitPro before make.
DEVKITPRO ?= /opt/devkitpro
DEVKITARM ?= $(DEVKITPRO)/devkitARM
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
GBAFIX := $(DEVKITPRO)/tools/bin/gbafix

$(TARGET).gba : $(TARGET).elf
	$(OBJCOPY) -v -O binary $< $@
	-@$(GBAFIX) $@

$(TARGET).elf : $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) -o $@

main.o : main.c gba.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	@rm -f *.o *.elf *.gba
