cmake_minimum_required(VERSION 3.16)
project(ascension_setup_compat C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(ascension_setup_compat STATIC
    asc_setup.c
)

target_include_directories(ascension_setup_compat PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

if(MSVC)
    target_compile_options(ascension_setup_compat PRIVATE /W4)
else()
    target_compile_options(ascension_setup_compat PRIVATE -Wall -Wextra -Wpedantic)
endif()

option(ASC_SETUP_BUILD_TESTS "Build Ascension setup compatibility tests" ON)
if(ASC_SETUP_BUILD_TESTS)
    enable_testing()
    add_executable(ascension_setup_compat_test asc_setup_test.c)
    target_link_libraries(ascension_setup_compat_test PRIVATE ascension_setup_compat)
    add_test(NAME ascension_setup_compat_roundtrip COMMAND ascension_setup_compat_test)
endif()
