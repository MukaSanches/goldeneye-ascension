cmake_minimum_required(VERSION 3.16)

# This directory can be built by itself for tooling work, or embedded from the
# main Ascension build later without creating a second project.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(ascension_setup_compat C)
    set(CMAKE_C_STANDARD 11)
    set(CMAKE_C_STANDARD_REQUIRED ON)
endif()

add_library(ascension_setup_compat STATIC
    asc_setup.c
    asc_setup_native.c
    asc_setup_semantic.c
)

target_include_directories(ascension_setup_compat PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

if(MSVC)
    target_compile_options(ascension_setup_compat PRIVATE /W4)
else()
    target_compile_options(ascension_setup_compat PRIVATE -Wall -Wextra -Wpedantic)
endif()

option(ASC_SETUP_BUILD_CLI "Build Ascension setup compatibility CLI" ON)
if(ASC_SETUP_BUILD_CLI)
    add_executable(asc-setup asc_setup_cli.c)
    target_link_libraries(asc-setup PRIVATE ascension_setup_compat)
endif()

option(ASC_SETUP_BUILD_TESTS "Build Ascension setup compatibility tests" ON)
if(ASC_SETUP_BUILD_TESTS)
    enable_testing()
    add_executable(ascension_setup_compat_test asc_setup_test.c)
    target_link_libraries(ascension_setup_compat_test PRIVATE ascension_setup_compat)
    add_test(NAME ascension_setup_compat_roundtrip COMMAND ascension_setup_compat_test)
endif()
