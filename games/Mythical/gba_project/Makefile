PROJ    := Mythical_GBA
TARGET  := $(PROJ)
OBJS    := main.o generated/assets.o generated/maps.o generated/content.o
PYTHON  ?= py -3

export TMPDIR := $(CURDIR)
export TMP    := $(CURDIR)
export TEMP   := $(CURDIR)
DEVKITARM := c:/devkitPro/devkitARM
PREFIX  := $(DEVKITARM)/bin/arm-none-eabi-
CC      := $(PREFIX)gcc
LD      := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy
GBAFIX  := c:/devkitPro/tools/bin/gbafix

ARCH    := -mthumb-interwork -mthumb
SPECS   := -specs=gba.specs
CFLAGS  := $(ARCH) -O2 -Wall -Wextra -std=c99 -fno-strict-aliasing -pipe -I. -Igenerated
LDFLAGS := $(ARCH) $(SPECS) -pipe

.PHONY: build clean assets

build: $(TARGET).gba

assets:
	$(PYTHON) convert_assets.py
	$(PYTHON) convert_content.py

$(TARGET).gba: $(TARGET).elf
	$(OBJCOPY) -v -O binary $< $@
	-@$(GBAFIX) $@

$(TARGET).elf: $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) -o $@

main.o: main.c gba.h generated/assets.h generated/maps.h generated/content.h
	$(CC) $(CFLAGS) -c $< -o $@

generated/assets.o: generated/assets.c generated/assets.h gba.h
	$(CC) $(CFLAGS) -c $< -o $@

generated/maps.o: generated/maps.c generated/maps.h gba.h
	$(CC) $(CFLAGS) -c $< -o $@

generated/content.o: generated/content.c generated/content.h gba.h generated/maps.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	@rm -f main.o generated/*.o $(TARGET).elf $(TARGET).gba
