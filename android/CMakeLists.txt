cmake_minimum_required(VERSION 3.22)
project(goldeneye_ascension_android C CXX ASM)

set(ASCENSION_ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(ASCENSION_SDL2_SOURCE_DIR "" CACHE PATH "Path to SDL2 source tree")
if(NOT ASCENSION_SDL2_SOURCE_DIR OR NOT EXISTS "${ASCENSION_SDL2_SOURCE_DIR}/CMakeLists.txt")
  message(FATAL_ERROR "ASCENSION_SDL2_SOURCE_DIR must point to a pinned SDL2 source tree")
endif()

if(NOT ANDROID)
  message(FATAL_ERROR "android/CMakeLists.txt is Android-only")
endif()
if(NOT ANDROID_ABI STREQUAL "arm64-v8a")
  message(FATAL_ERROR "Ascension Android V1 supports arm64-v8a only")
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# V1 is deliberately NTSC-U first: it is the primary tested Ascension target.
set(ROMID "ntsc-final")
set(VERSION_IS_PAL 0)
set(ASSET_REGION "u")
set(TARGET_PLATFORM "arm64-android")
execute_process(
  COMMAND git rev-parse --short HEAD
  WORKING_DIRECTORY "${ASCENSION_ROOT}"
  OUTPUT_VARIABLE VERSION_HASH
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET)
if(NOT VERSION_HASH)
  set(VERSION_HASH "android")
endif()
configure_file(
  "${ASCENSION_ROOT}/port/include/versioninfo.h.in"
  "${CMAKE_CURRENT_BINARY_DIR}/generated/versioninfo.h" @ONLY)

# SDL owns the Android Activity/JNI surface. Build it from the pinned source
# rather than relying on a device/vendor SDL package.
set(SDL_SHARED ON CACHE BOOL "" FORCE)
set(SDL_STATIC OFF CACHE BOOL "" FORCE)
set(SDL_TEST OFF CACHE BOOL "" FORCE)
add_subdirectory("${ASCENSION_SDL2_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/sdl2")

add_compile_definitions(
  PORT=1
  _LANGUAGE_C=1
  AVOID_UB=1
  PAL=0
  VERSION_US
  LANG_US
  REFRESH_NTSC
  LEFTOVERDEBUG
  LEFTOVERSPECTRUM
  BUGFIX_R0
  BYTEMATCH
  PLATFORM_64BIT=1
)

# Clang supports Microsoft's anonymous tagged struct extension, which preserves
# direct field access for the decomp's `inherits struct` idiom. Any remaining
# Plan-9-only pointer conversions are fixed explicitly instead of depending on
# a GCC-only frontend extension.
add_compile_options(
  -fms-extensions
  -fno-strict-aliasing
  -funsigned-char
  -fwrapv
  -fno-stack-protector
  -fno-omit-frame-pointer
  -Wall
  -Wno-address
  -Wno-deprecated-non-prototype
  -Wno-incompatible-pointer-types
  -Wno-int-conversion
  -Wno-implicit-function-declaration
  -Wno-missing-braces
  -Wno-multichar
  -Wno-pointer-sign
  -Wno-tautological-compare
  -Wno-unused-but-set-variable
  -Wno-unused-function
  -Wno-unused-value
  -Wno-unused-variable
)

include_directories(
  "${ASCENSION_ROOT}/port/shim"
  "${ASCENSION_ROOT}"
  "${ASCENSION_ROOT}/include"
  "${ASCENSION_ROOT}/include/PR"
  "${ASCENSION_ROOT}/src"
  "${ASCENSION_ROOT}/src/game"
  "${ASCENSION_ROOT}/src/libultra"
  "${ASCENSION_ROOT}/src/libultra/audio"
  "${ASCENSION_ROOT}/port/include"
  "${ASCENSION_ROOT}/android/include"
  "${CMAKE_CURRENT_BINARY_DIR}/generated"
  "${ASCENSION_SDL2_SOURCE_DIR}/include"
)

# Port layer and software RSP.
file(GLOB_RECURSE SRC_PORT "${ASCENSION_ROOT}/port/src/*.c")
file(GLOB_RECURSE SRC_PORT_CXX "${ASCENSION_ROOT}/port/src/*.cpp")
file(GLOB_RECURSE SRC_FAST3D
  "${ASCENSION_ROOT}/port/fast3d/*.cpp"
  "${ASCENSION_ROOT}/port/fast3d/glad/*.c")

# Android supplies platform replacements for process/crash/DRAM handling and
# an SDL_main bridge. Desktop versions must not be linked into the APK.
list(REMOVE_ITEM SRC_PORT
  "${ASCENSION_ROOT}/port/src/main.c"
  "${ASCENSION_ROOT}/port/src/system.c"
  "${ASCENSION_ROOT}/port/src/crash.c"
  "${ASCENSION_ROOT}/port/src/dram.c")

set(SRC_ANDROID
  "${ASCENSION_ROOT}/android/src/android_main.c"
  "${ASCENSION_ROOT}/android/src/system_android.c"
  "${ASCENSION_ROOT}/android/src/crash_android.c"
  "${ASCENSION_ROOT}/android/src/dram_android.c"
  "${ASCENSION_ROOT}/android/src/mobile_input.c"
  "${ASCENSION_ROOT}/android/src/mobile_input_merge.c")

set(SRC_ROMASSETS "${ASCENSION_ROOT}/port/src/romassets_${ASSET_REGION}.s")
set(SRC_DRAM_SYMS "${ASCENSION_ROOT}/port/src/dram_syms.s")

file(GLOB_RECURSE SRC_GAME "${ASCENSION_ROOT}/src/game/*.c")
list(REMOVE_ITEM SRC_GAME
  "${ASCENSION_ROOT}/src/game/decompress.c"
  "${ASCENSION_ROOT}/src/game/zlib.c")

# Build-time Android compatibility rewrites. They are exact and fail closed:
# if the upstream source changes, configuration aborts instead of silently
# applying a stale patch. Shared PC/N64 source remains byte-for-byte untouched.
function(ascension_android_replace_required var needle replacement label)
  string(FIND "${${var}}" "${needle}" _ascension_android_match)
  if(_ascension_android_match EQUAL -1)
    message(FATAL_ERROR "Android compatibility rewrite drifted: missing ${label}")
  endif()
  string(REPLACE "${needle}" "${replacement}" _ascension_android_rewritten "${${var}}")
  set(${var} "${_ascension_android_rewritten}" PARENT_SCOPE)
endfunction()

# Clang currently has an open frontend bug for references to names declared
# through `#pragma weak alias = target` in the same C translation unit (LLVM
# #56760): it can report a spurious "reference ... is ambiguous" error. lv.c
# uses these aliases only as alternate names for the exact variables below.
set(LV_SOURCE "${ASCENSION_ROOT}/src/game/lv.c")
set(LV_ANDROID_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/generated/lv_android.c")
file(READ "${LV_SOURCE}" LV_ANDROID_TEXT)
ascension_android_replace_required(
  LV_ANDROID_TEXT
  "g_DebugPortalsInputBuffer = g_DebugPortalsInputBufferSource1;"
  "g_DebugPortalsInputBuffer = g_DebugPortalsInputBuffer1;"
  "lv portal source alias 1")
ascension_android_replace_required(
  LV_ANDROID_TEXT
  "g_DebugPortalsInputBuffer1 = g_DebugPortalsInputBufferSource2;"
  "g_DebugPortalsInputBuffer1 = g_DebugPortalsInputBuffer2;"
  "lv portal source alias 2")
ascension_android_replace_required(
  LV_ANDROID_TEXT
  "temp_v1 = g_DebugPortalsInputBufferSource4;"
  "temp_v1 = g_DebugPortalsInputBuffer4;"
  "lv portal source alias 4")
ascension_android_replace_required(
  LV_ANDROID_TEXT
  "g_DebugPortalsInputBuffer2 = g_DebugPortalsInputBufferSource3;"
  "g_DebugPortalsInputBuffer2 = g_DebugPortalsInputBuffer3;"
  "lv portal source alias 3")
file(WRITE "${LV_ANDROID_SOURCE}" "${LV_ANDROID_TEXT}")
list(REMOVE_ITEM SRC_GAME "${LV_SOURCE}")
list(APPEND SRC_GAME "${LV_ANDROID_SOURCE}")

# Localized text here is data, never a printf format. Use an explicit "%s"
# in the Android-derived translation units so Clang's format-security checks
# remain fully enabled and user-controlled '%' sequences cannot be interpreted.
set(GUNFIRE_SOURCE "${ASCENSION_ROOT}/src/game/gunfire.c")
set(GUNFIRE_ANDROID_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/generated/gunfire_android.c")
file(READ "${GUNFIRE_SOURCE}" GUNFIRE_ANDROID_TEXT)
ascension_android_replace_required(
  GUNFIRE_ANDROID_TEXT
  "sprintf(buffer, langGet(getStringID(LGUN, GUN_STR_DB_DIEDONCE_LF)));"
  "sprintf(buffer, \"%s\", langGet(getStringID(LGUN, GUN_STR_DB_DIEDONCE_LF)));"
  "gunfire localized death text format")
file(WRITE "${GUNFIRE_ANDROID_SOURCE}" "${GUNFIRE_ANDROID_TEXT}")
list(REMOVE_ITEM SRC_GAME "${GUNFIRE_SOURCE}")
list(APPEND SRC_GAME "${GUNFIRE_ANDROID_SOURCE}")

set(MPMENU_SOURCE "${ASCENSION_ROOT}/src/game/mpmenu.c")
set(MPMENU_ANDROID_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/generated/mpmenu_android.c")
file(READ "${MPMENU_SOURCE}" MPMENU_ANDROID_TEXT)
ascension_android_replace_required(
  MPMENU_ANDROID_TEXT
  "sprintf(buffer, langGet(getStringID(LMPMENU, MPMENU_STR_11_RANK1ST)));"
  "sprintf(buffer, \"%s\", langGet(getStringID(LMPMENU, MPMENU_STR_11_RANK1ST)));"
  "mpmenu rank 1 text format")
ascension_android_replace_required(
  MPMENU_ANDROID_TEXT
  "sprintf(buffer, langGet(getStringID(LMPMENU, MPMENU_STR_12_RANK2ND)));"
  "sprintf(buffer, \"%s\", langGet(getStringID(LMPMENU, MPMENU_STR_12_RANK2ND)));"
  "mpmenu rank 2 text format")
ascension_android_replace_required(
  MPMENU_ANDROID_TEXT
  "sprintf(buffer, langGet(getStringID(LMPMENU, MPMENU_STR_13_RANK3RD)));"
  "sprintf(buffer, \"%s\", langGet(getStringID(LMPMENU, MPMENU_STR_13_RANK3RD)));"
  "mpmenu rank 3 text format")
ascension_android_replace_required(
  MPMENU_ANDROID_TEXT
  "sprintf(buffer, langGet(getStringID(LMPMENU, MPMENU_STR_14_RANK4TH)));"
  "sprintf(buffer, \"%s\", langGet(getStringID(LMPMENU, MPMENU_STR_14_RANK4TH)));"
  "mpmenu rank 4 text format")
file(WRITE "${MPMENU_ANDROID_SOURCE}" "${MPMENU_ANDROID_TEXT}")
list(REMOVE_ITEM SRC_GAME "${MPMENU_SOURCE}")
list(APPEND SRC_GAME "${MPMENU_ANDROID_SOURCE}")

set(OPTIONS_SOURCE "${ASCENSION_ROOT}/src/game/options.c")
set(OPTIONS_ANDROID_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/generated/options_android.c")
file(READ "${OPTIONS_SOURCE}" OPTIONS_ANDROID_TEXT)
ascension_android_replace_required(
  OPTIONS_ANDROID_TEXT
  "sprintf(pageTitle, langGet(0xac38));"
  "sprintf(pageTitle, \"%s\", langGet(0xac38));"
  "options background title format")
ascension_android_replace_required(
  OPTIONS_ANDROID_TEXT
  "sprintf(pageTitle, langGet(0xac39));"
  "sprintf(pageTitle, \"%s\", langGet(0xac39));"
  "options M title format")
ascension_android_replace_required(
  OPTIONS_ANDROID_TEXT
  "sprintf(pageTitle, langGet(0xac3a));"
  "sprintf(pageTitle, \"%s\", langGet(0xac3a));"
  "options Q title format")
ascension_android_replace_required(
  OPTIONS_ANDROID_TEXT
  "sprintf(pageTitle, langGet(0xac3b));"
  "sprintf(pageTitle, \"%s\", langGet(0xac3b));"
  "options Moneypenny title format")
ascension_android_replace_required(
  OPTIONS_ANDROID_TEXT
  "sprintf(pageTitle, langGet(0xac3c));"
  "sprintf(pageTitle, \"%s\", langGet(0xac3c));"
  "options objectives title format")
file(WRITE "${OPTIONS_ANDROID_SOURCE}" "${OPTIONS_ANDROID_TEXT}")
list(REMOVE_ITEM SRC_GAME "${OPTIONS_SOURCE}")
list(APPEND SRC_GAME "${OPTIONS_ANDROID_SOURCE}")

file(GLOB SRC_LIBAUDIO "${ASCENSION_ROOT}/src/libultra/audio/*.c")
file(GLOB SRC_LIBULTRARE_AUDIO "${ASCENSION_ROOT}/src/libultrare/audio/*.c")
file(GLOB SRC_GU "${ASCENSION_ROOT}/src/libultra/gu/*.c")

set(SRC_LIBULTRARE_DATA "${ASCENSION_ROOT}/src/libultrare/io/vitbl.c")
set(SRC_LIBULTRARE_LIBC
  "${ASCENSION_ROOT}/src/libultrare/libc/xprintf.c"
  "${ASCENSION_ROOT}/src/libultra/libc/xlitob.c"
  "${ASCENSION_ROOT}/src/libultra/libc/xldtob.c")
set(SRC_ASSETS
  "${ASCENSION_ROOT}/assets/font_chardatae.c"
  "${ASCENSION_ROOT}/assets/font_chardataj.c"
  "${ASCENSION_ROOT}/assets/font_dl.c"
  "${ASCENSION_ROOT}/assets/oddtextures.c"
  "${ASCENSION_ROOT}/assets/rarewarelogo.c")
set(SRC_ENGINE
  "${ASCENSION_ROOT}/src/init.c"
  "${ASCENSION_ROOT}/src/sched.c"
  "${ASCENSION_ROOT}/src/audi.c"
  "${ASCENSION_ROOT}/src/snd.c"
  "${ASCENSION_ROOT}/src/music.c"
  "${ASCENSION_ROOT}/src/joy.c"
  "${ASCENSION_ROOT}/src/fr.c"
  "${ASCENSION_ROOT}/src/stacks.c"
  "${ASCENSION_ROOT}/src/boss.c"
  "${ASCENSION_ROOT}/src/mema.c"
  "${ASCENSION_ROOT}/src/memp.c"
  "${ASCENSION_ROOT}/src/deb.c"
  "${ASCENSION_ROOT}/src/debugmenu.c"
  "${ASCENSION_ROOT}/src/speed_graph.c"
  "${ASCENSION_ROOT}/src/token.c"
  "${ASCENSION_ROOT}/src/str.c"
  "${ASCENSION_ROOT}/src/sprintf.c"
  "${ASCENSION_ROOT}/src/ramrom.c")

set(SRC
  ${SRC_GAME}
  ${SRC_PORT}
  ${SRC_PORT_CXX}
  ${SRC_FAST3D}
  ${SRC_ANDROID}
  ${SRC_ROMASSETS}
  ${SRC_DRAM_SYMS}
  ${SRC_LIBAUDIO}
  ${SRC_LIBULTRARE_AUDIO}
  ${SRC_LIBULTRARE_DATA}
  ${SRC_LIBULTRARE_LIBC}
  ${SRC_ASSETS}
  ${SRC_GU}
  ${SRC_ENGINE})

add_library(ascension SHARED ${SRC})
set_target_properties(ascension PROPERTIES OUTPUT_NAME "ascension")

target_link_libraries(ascension PRIVATE
  SDL2
  android
  log
  GLESv3
  z
  dl
  m)

# Android 15+ / Play 16 KiB-page compatibility. Modern NDK linkers honor this
# alignment while remaining valid on 4 KiB devices. The input wrapper keeps
# touch/gyro Android-only without modifying the shared desktop input source.
target_link_options(ascension PRIVATE
  "-Wl,-z,max-page-size=16384"
  "-Wl,--wrap=inputComputePad")

# Export only the JNI/SDL entry surface by default; game internals stay local.
set_target_properties(ascension PROPERTIES
  C_VISIBILITY_PRESET hidden
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN YES)

message(STATUS "Ascension Android: ${ANDROID_ABI}, core=${VERSION_HASH}, ROM=${ROMID}")
