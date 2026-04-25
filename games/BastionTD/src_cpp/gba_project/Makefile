#---------------------------------------------------------------------------------------------------------------------
# BastionTD — butano build. Reuses ../src/core for all simulation code; GBA
# renderer and SRAM-backed save manager live under src/.
#---------------------------------------------------------------------------------------------------------------------
TARGET          := BastionTD
BUILD           := build
LIBBUTANO       := ../tools/butano/butano
PYTHON          := python3
SOURCES         := src ../core ../states
INCLUDES        := include ../tools/butano/common/include ..
DATA            :=
GRAPHICS        := graphics ../tools/butano/common/graphics
AUDIO           := audio
AUDIOBACKEND    := maxmod
AUDIOTOOL       :=
DMGAUDIO        := dmg_audio
DMGAUDIOBACKEND := default
ROMTITLE        := BASTIONTD
ROMCODE         := BTDB
USERFLAGS       := -DBASTION_GBA -DBN_CFG_SPRITES_MAX_ITEMS=512 -DBN_CFG_SPRITES_MAX_SORT_LAYERS=32
USERCXXFLAGS    := -std=gnu++23 -Wno-switch-default -Wno-c++23-extensions
USERASFLAGS     :=
USERLDFLAGS     :=
USERLIBDIRS     :=
USERLIBS        :=
DEFAULTLIBS     := 1
STACKTRACE      :=
USERBUILD       :=
EXTTOOL         :=

ifndef LIBBUTANOABS
    export LIBBUTANOABS := $(realpath $(LIBBUTANO))
endif

include $(LIBBUTANOABS)/butano.mak
