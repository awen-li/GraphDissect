cmake_minimum_required(VERSION 3.12)

project(mfuzz
    VERSION 0.1.0
    LANGUAGES CXX
)

# C++17, GCC/Clang
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra -Wpedantic)

# Sources
set(MFUZZ_SOURCES
    src/main.cpp
    src/mfuzz.cpp
    src/scheduler.cpp
    src/driver.cpp
    src/fcov.cpp
    src/fuzzer.cpp
    src/util.cpp
)

add_executable(mfuzz ${MFUZZ_SOURCES})

target_include_directories(mfuzz
    PRIVATE
        ${PROJECT_SOURCE_DIR}/include
)

# Where to search for your .so files
set(MFUZZ_LIB_DIRS
    ${PROJECT_SOURCE_DIR}/lib
    /usr/local/lib
    /usr/lib
)

find_library(CG_MARKER_LIB
    NAMES cgmarker
    PATHS ${MFUZZ_LIB_DIRS}
)

find_library(COM_GRAPH_LIB
    NAMES comgraph
    PATHS ${MFUZZ_LIB_DIRS}
)

if (NOT CG_MARKER_LIB)
    message(FATAL_ERROR "Could not find libcgmarker.so (library 'cgmarker')")
endif()

if (NOT COM_GRAPH_LIB)
    message(FATAL_ERROR "Could not find libcomgraph.so (library 'comgraph')")
endif()

# Threads
find_package(Threads REQUIRED)

target_link_libraries(mfuzz
    PRIVATE
        Threads::Threads
        ${CG_MARKER_LIB}
        ${COM_GRAPH_LIB}
)

# std::filesystem: uncomment if linker errors appear on older GCC
# if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
#     target_link_libraries(mfuzz PRIVATE stdc++fs)
# endif()
