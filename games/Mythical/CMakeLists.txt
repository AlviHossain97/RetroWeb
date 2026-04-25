cmake_minimum_required(VERSION 3.20)

project(MythicalCppPort LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

add_subdirectory(cpp_core)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/cpp_port/CMakeLists.txt")
    add_subdirectory(cpp_port)
endif()

# gba_port is built with devkitARM (separate Makefile) and is not part of this
# host CMake tree. See gba_port/Makefile.
