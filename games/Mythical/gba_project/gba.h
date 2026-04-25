#ifndef MYTHICAL_GBA_H
#define MYTHICAL_GBA_H

#include <stdint.h>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef volatile u8 vu8;
typedef volatile u16 vu16;
typedef volatile u32 vu32;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;

#define MEM_IO 0x04000000
#define MEM_VRAM 0x06000000

#define REG_DISPCNT (*(vu16 *)(MEM_IO + 0x0000))
#define REG_VCOUNT (*(vu16 *)(MEM_IO + 0x0006))
#define REG_KEYINPUT (*(vu16 *)(MEM_IO + 0x0130))
#define REG_BG0CNT (*(vu16 *)(MEM_IO + 0x0008))
#define REG_BG1CNT (*(vu16 *)(MEM_IO + 0x000A))
#define REG_BG2CNT (*(vu16 *)(MEM_IO + 0x000C))
#define REG_BG3CNT (*(vu16 *)(MEM_IO + 0x000E))
#define REG_BG0HOFS (*(vu16 *)(MEM_IO + 0x0010))
#define REG_BG0VOFS (*(vu16 *)(MEM_IO + 0x0012))
#define REG_BG1HOFS (*(vu16 *)(MEM_IO + 0x0014))
#define REG_BG1VOFS (*(vu16 *)(MEM_IO + 0x0016))
#define REG_BG2HOFS (*(vu16 *)(MEM_IO + 0x0018))
#define REG_BG2VOFS (*(vu16 *)(MEM_IO + 0x001A))
#define REG_BG3HOFS (*(vu16 *)(MEM_IO + 0x001C))
#define REG_BG3VOFS (*(vu16 *)(MEM_IO + 0x001E))

#define REG_DMA3SAD (*(vu32 *)(MEM_IO + 0x00D4))
#define REG_DMA3DAD (*(vu32 *)(MEM_IO + 0x00D8))
#define REG_DMA3CNT (*(vu32 *)(MEM_IO + 0x00DC))

#define MODE_0 0x0000
#define MODE_3 0x0003
#define BG2_ENABLE 0x0400
#define BG0_ENABLE 0x0100
#define BG1_ENABLE 0x0200
#define BG3_ENABLE 0x0800
#define OBJ_ENABLE 0x1000
#define OBJ_MAP_1D 0x0040

#define BG_PRIORITY(n) ((n) & 0x0003)
#define BG_CHARBLOCK(n) (((n) & 0x0003) << 2)
#define BG_256_COLOR 0x0080
#define BG_SCREENBLOCK(n) (((n) & 0x001F) << 8)
#define BG_SIZE_32X32 0x0000
#define BG_SIZE_64X32 0x4000
#define BG_SIZE_32X64 0x8000
#define BG_SIZE_64X64 0xC000

#define DMA_ON 0x80000000
#define DMA_16 0x00000000

#define VRAM ((vu16 *)(uintptr_t)MEM_VRAM)
#define BG_PALETTE ((vu16 *)(uintptr_t)0x05000000)
#define OBJ_PALETTE ((vu16 *)(uintptr_t)0x05000200)

#define SCREEN_WIDTH 240
#define SCREEN_HEIGHT 160

#define RGB15(r, g, b) ((r) | ((g) << 5) | ((b) << 10))

#define KEY_A 0x0001
#define KEY_B 0x0002
#define KEY_SELECT 0x0004
#define KEY_START 0x0008
#define KEY_RIGHT 0x0010
#define KEY_LEFT 0x0020
#define KEY_UP 0x0040
#define KEY_DOWN 0x0080
#define KEY_R 0x0100
#define KEY_L 0x0200

#ifndef EWRAM_DATA
#define EWRAM_DATA __attribute__((section(".ewram_data")))
#endif

typedef struct {
  u16 attr0;
  u16 attr1;
  u16 attr2;
  u16 pad;
} ObjAttr;

#define OAM ((ObjAttr *)(uintptr_t)0x07000000)
#define CHARBLOCK(n) ((vu16 *)(uintptr_t)(MEM_VRAM + ((n) * 0x4000)))
#define SCREENBLOCK(n) ((vu16 *)(uintptr_t)(MEM_VRAM + ((n) * 0x800)))
#define OBJ_TILE_MEM ((vu16 *)(uintptr_t)(MEM_VRAM + 0x10000))

#define ATTR0_REGULAR 0x0000
#define ATTR0_HIDE 0x0200
#define ATTR0_8BPP 0x2000
#define ATTR0_SQUARE 0x0000

#define ATTR1_SIZE_8 0x0000
#define ATTR1_SIZE_16 0x4000
#define ATTR1_SIZE_32 0x8000

#define ATTR2_PRIORITY(n) (((n) & 0x0003) << 10)

static inline void waitForVBlank(void) {
  while (REG_VCOUNT >= 160) {
  }
  while (REG_VCOUNT < 160) {
  }
}

static inline void dmaCopy16(const void *src, void *dst, u32 halfwords) {
  REG_DMA3CNT = 0;
  REG_DMA3SAD = (u32)(uintptr_t)src;
  REG_DMA3DAD = (u32)(uintptr_t)dst;
  REG_DMA3CNT = halfwords | DMA_ON | DMA_16;
}

static inline void dmaCopy32(const void *src, void *dst, u32 words) {
  REG_DMA3CNT = 0;
  REG_DMA3SAD = (u32)(uintptr_t)src;
  REG_DMA3DAD = (u32)(uintptr_t)dst;
  REG_DMA3CNT = words | DMA_ON | 0x04000000;
}

#endif
