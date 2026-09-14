#include <ultra64.h>
#ifdef PORT
/* TEMP D69: probe below uses fprintf/getenv. */
#include <stdio.h>
#include <stdlib.h>
#include "pcmodels.h" /* D50: PC-layout model sidecars */
#include "pccg.h"     /* D69: PC-layout bg/stan sidecars */
#if defined(ASC_SETUP_ENABLE_HOT_RELOAD)
#include "asc_setup_hotreload.h"
#endif
#endif
#include "macro.h"
#include "ob.h"
#include <deb.h>
#include <memp.h>
#include <assets/obseg/obseg.h>
#include "decompress.h"
#include "indy_comms.h"
#include "assets/obseg/file_resource_id_enums.h"

//bss
//800888b0

 resource_lookup_data_entry resource_lookup_data_array[OBJ_INDEX_MAX];


// data
//D:80046050
s32 ob_c_debug_notice_list_entry = 0;


#include <assets/obseg/file_resource_table.inc.c>
/* struct fileentry file_resource_table[] =
   {
       blah;
    };
 */


//D:800482D4
s32 file_entry_max = OBJ_INDEX_END;




void load_resource(u8 *ptrdata, s32 bytes,  fileentry *srcfile,  resource_lookup_data_entry *lookupdata)
{
    u8 *source;
    u8  buffer[0x2100];
    s32 unused;


    if (bytes == 0)
    {
        romCopy(ptrdata, srcfile->hw_address, lookupdata->rom_size);
        return;
    }
    source = (ptrdata + bytes) - ((lookupdata->rom_size + 7) & -8);
    if ((u32) (source - ptrdata) < 8U)
    {
        lookupdata->poolRemaining = 0;
    }
    else
    {
#if DEBUG
        char sp54[128];
        u32  stack[2];
#endif

        romCopy(source, srcfile->hw_address, lookupdata->rom_size);
        lookupdata->poolRemaining = decompressdata(source, ptrdata, buffer);;
#if DEBUG
        if (result == 0)
        {
            sprintf(sp54, "DMA-Crash %s %d Ram: %02x%02x%02x%02x%02x%02x%02x%02x", "ob.c", 204, scratch[0], scratch[1], scratch[2], scratch[3], scratch[4], scratch[5], scratch[6], scratch[7]);
            crashSetMessage(sp54);
            CRASH();
        }
#endif

    }
}

void resource_load_from_indy(u8 *ptrdata, s32 bytes,  fileentry *srcfile,  resource_lookup_data_entry *lookupdata)
{
    u8 *pPayload;
    u8 buffer[8448];
    s32 size;
    static const u8 rz_header_1[] = {0x11, 0x72, 0x00, 0x00};
    static const u8 rz_header_2[] = {0x11, 0x72, 0x00, 0x00};

    if (!bytes)
    {
        indycommHostLoadFile(srcfile->filename, ptrdata);
        return;
    }
    indycommHostCheckFileExists(srcfile->filename, &lookupdata->pc_size);
    pPayload = (ptrdata + bytes) - ((lookupdata->pc_size + 7) & -8);
    if ((pPayload - ptrdata) < 8U)
    {
        lookupdata->poolRemaining = 0;
    }
    else
    {
        indycommHostLoadFile(srcfile->filename, pPayload);
        if ((pPayload[0] == rz_header_1[0]) && (pPayload[1] == rz_header_2[1]))
        {
            size = decompressdata(pPayload, ptrdata, &buffer);
        }
        else
        {
            bcopy(pPayload, ptrdata, lookupdata->pc_size);
            size = lookupdata->pc_size;
        }
        lookupdata->poolRemaining = size;
    }
}





void obInit(void)
{
    s32 size;
    s32 i;

    debTryAdd(&ob_c_debug_notice_list_entry, "ob_c_debug");
    
    for (i = 1; i < file_entry_max - 1; i++)
    {
        size = (file_resource_table[i + 1].hw_address - file_resource_table[i].hw_address);

        resource_lookup_data_array[i].rom_size = size;
        resource_lookup_data_array[i].poolRemaining = 0;
        resource_lookup_data_array[i].pc_size = 0;
        resource_lookup_data_array[i].rom_remaining = 0;

        if (size);
    }

#ifdef PORT
    /* D69/D50: patch file_resource_table->hw_address / rom_size to point at
     * the converted PC sidecars now that obInit() has populated the table.
     * Previously this only happened lazily on the first model load
     * (load_object_fill_header); a direct "-level_XX" boot loads a stage
     * before any model loads, so load_bg_file would read raw big-endian ROM
     * and crash. Both calls are one-shot/idempotent. */
    pcmodelsPatchTable();
    pccgPatchTable();
#endif
}


#if !defined(LEFTOVERDEBUG)
/* VERSION_EU */
/* same as below version, shuffled in EU */
void obLoadBGFileBytesAtOffset(u8 *bgname, u8 *target, s32 offset, s32 len)
{
  s32 index;
   fileentry *fileentry;

  index = fileGetIndex(bgname);
  fileentry = &file_resource_table[index];

#ifdef PORT
  /* TEMP D69: trace BG-file loads (env GE_D69=1). */
  if (getenv("GE_D69"))
    fprintf(stderr, "D69 obLoadBGFile %s idx=%d rom_size=0x%X hw=0x%08X off=0x%X len=0x%X\n",
            (const char *)bgname, index,
            (unsigned)resource_lookup_data_array[index].rom_size,
            (unsigned)(u32)fileentry->hw_address, (unsigned)offset, (unsigned)len);
#endif

  if (resource_lookup_data_array[index].rom_size != 0)
  {
    //if the size of offset data would exceed file size, loop forever
    if ((resource_lookup_data_array[index].rom_size + 0xF) < (offset + len))
    {
      while (1){};
    }
    romCopy(target, &fileentry->hw_address[offset], len, fileentry);
  }

}
#endif

#if defined(LEFTOVERDEBUG)
/* no VERSION_EU */
void *_fileIndexLoadToBank(s32 index, FILELOADMETHOD param_2, s32 size, u8 bank)
{
    return fileIndexLoadToBank(index, param_2, size, bank);
}
#endif

#if defined(LEFTOVERDEBUG)
/* no VERSION_EU */
void *_fileIndexLoadToAddr(int index, FILELOADMETHOD param_2, u8 *ptrdata, int size)
{
    return fileIndexLoadToAddr(index, param_2, ptrdata, size);
}
#endif

void *_fileNameLoadToBank(char *filename, FILELOADMETHOD loadMethod, s32 size, u8 bank)
{
#if defined(PORT) && defined(ASC_SETUP_ENABLE_HOT_RELOAD)
    const void *override_bytes;
    size_t override_size = 0;
    uint64_t generation = 0;

    /*
     * Reloads are deliberately consumed here rather than by mutating
     * g_ptrStageSetupFile later. This function is called at the normal stage
     * resource-load boundary, before StageSetup pointers and live props/AI are
     * constructed. A malformed candidate never reaches this point because the
     * hot-reload module validates and normalizes it transactionally first.
     */
    asc_setup_hotreload_refresh_environment(filename);
    override_bytes = asc_setup_hotreload_acquire(filename, &override_size, &generation);
    if (override_bytes != NULL && override_size <= 0xffffffffu) {
        u32 reserve = size > 0 ? (u32)size : 0u;
        if (override_size <= 0xffffffffu - reserve) {
            u8 *dst = mempAllocBytesInBank((u32)override_size + reserve, bank);
            if (dst != NULL) {
                bcopy(override_bytes, dst, (u32)override_size);
                asc_setup_hotreload_consumed(generation);
                return dst;
            }
        }
    }
#endif
    return fileIndexLoadToBank(fileGetIndex(filename), loadMethod, size, bank);
}

void * _fileNameLoadToAddr(char *filename, FILELOADMETHOD loadMethod, u8 *ptrdata, s32 size)
{
    return fileIndexLoadToAddr(fileGetIndex(filename), loadMethod, ptrdata, size);
}

#if defined(LEFTOVERDEBUG)
/* no VERSION_EU */
/**
 * 0F18AC 7F0BCD7C
 * loads data stored at an offset of a bg file
 */
void obLoadBGFileBytesAtOffset(u8 *bgname, u8 *target, s32 offset, s32 len)
{
  s32 index;
   fileentry *fileentry;

  index = fileGetIndex(bgname);
  fileentry = &file_resource_table[index];

  if (resource_lookup_data_array[index].rom_size != 0)
  {
    if ((resource_lookup_data_array[index].rom_size + 0xF) < (offset + len))
    {
      while (1){};
    }
    romCopy(target, &fileentry->hw_address[offset], len, fileentry);
  }
}
#endif
