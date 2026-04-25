cmake_minimum_required(VERSION 3.16)
project(BastionTD LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BASTION_BUILD_TESTS "Build BastionTD test executables" ON)
option(BASTION_DEBUG "Enable debug compile definitions" ON)

find_package(SDL2 CONFIG QUIET)
if(NOT SDL2_FOUND)
    find_package(SDL2 REQUIRED)
endif()

add_library(bastion_core STATIC
    src/core/grid.cpp
    src/core/pathfinding.cpp
    src/core/economy.cpp
    src/core/enemy.cpp
    src/core/tower.cpp
    src/core/projectile.cpp
    src/core/wave_manager.cpp
    src/core/map_generator.cpp
    src/core/effects.cpp
    src/core/game.cpp
    src/core/save_manager.cpp
)
target_include_directories(bastion_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_features(bastion_core PUBLIC cxx_std_17)

find_package(Python3 COMPONENTS Interpreter QUIET)
if(NOT Python3_FOUND)
    find_program(Python3_EXECUTABLE NAMES python3 python REQUIRED)
endif()

set(BASTION_BAKED_SPRITES "${CMAKE_BINARY_DIR}/generated/baked_sprites.h")
set(BASTION_BAKE_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/bake_sprites.py")

file(GLOB_RECURSE BASTION_EXTRACTED_PNGS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/assets/extracted/*.png")

add_custom_command(
    OUTPUT "${BASTION_BAKED_SPRITES}"
    COMMAND ${Python3_EXECUTABLE} "${BASTION_BAKE_SCRIPT}" "${BASTION_BAKED_SPRITES}"
    DEPENDS "${BASTION_BAKE_SCRIPT}" ${BASTION_EXTRACTED_PNGS}
    COMMENT "Baking sprites -> ${BASTION_BAKED_SPRITES}"
    VERBATIM
)
add_custom_target(bastion_baked_sprites DEPENDS "${BASTION_BAKED_SPRITES}")

add_executable(BastionTD
    src/main.cpp
    src/hal/sdl2_renderer.cpp
    src/hal/sdl2_input.cpp
    src/hal/sdl2_audio.cpp
    src/hal/sdl2_assets.cpp
    src/states/title_state.cpp
    src/states/gameplay_state.cpp
    src/states/pause_state.cpp
    src/states/game_over_state.cpp
    src/states/victory_state.cpp
    src/states/instructions_state.cpp
    src/states/settings_state.cpp
)
add_dependencies(BastionTD bastion_baked_sprites)
target_include_directories(BastionTD PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_BINARY_DIR}/generated)

if(MINGW)
    target_link_options(BastionTD PRIVATE
        -static-libgcc
        -static-libstdc++
        -Wl,-Bstatic -lstdc++ -lpthread -Wl,-Bdynamic
    )
endif()

set(BASTION_SDL_LINK_LIBS)
if(TARGET SDL2::SDL2main)
    list(APPEND BASTION_SDL_LINK_LIBS SDL2::SDL2main)
elseif(DEFINED SDL2MAIN_LIBRARY AND SDL2MAIN_LIBRARY)
    list(APPEND BASTION_SDL_LINK_LIBS ${SDL2MAIN_LIBRARY})
endif()

if(TARGET SDL2::SDL2)
    list(APPEND BASTION_SDL_LINK_LIBS SDL2::SDL2)
elseif(TARGET SDL2::SDL2-static)
    list(APPEND BASTION_SDL_LINK_LIBS SDL2::SDL2-static)
else()
    target_include_directories(BastionTD PRIVATE ${SDL2_INCLUDE_DIRS})
    list(APPEND BASTION_SDL_LINK_LIBS ${SDL2_LIBRARIES})
endif()

target_link_libraries(BastionTD PRIVATE bastion_core ${BASTION_SDL_LINK_LIBS})

if(WIN32 AND TARGET SDL2::SDL2)
    add_custom_command(TARGET BastionTD POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:SDL2::SDL2>
            $<TARGET_FILE_DIR:BastionTD>
        COMMENT "Copying SDL2 runtime next to BastionTD.exe"
    )
endif()

if(WIN32)
    get_filename_component(BASTION_TOOLCHAIN_BIN_DIR "${CMAKE_CXX_COMPILER}" DIRECTORY)
    set(BASTION_RUNTIME_DLLS
        "${BASTION_TOOLCHAIN_BIN_DIR}/libstdc++-6.dll"
        "${BASTION_TOOLCHAIN_BIN_DIR}/libgcc_s_seh-1.dll"
        "${BASTION_TOOLCHAIN_BIN_DIR}/libwinpthread-1.dll"
    )

    foreach(BASTION_RUNTIME_DLL IN LISTS BASTION_RUNTIME_DLLS)
        if(EXISTS "${BASTION_RUNTIME_DLL}")
            add_custom_command(TARGET BastionTD POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${BASTION_RUNTIME_DLL}"
                    $<TARGET_FILE_DIR:BastionTD>
                COMMENT "Copying runtime dependency ${BASTION_RUNTIME_DLL}"
            )
        endif()
    endforeach()
endif()

if(BASTION_DEBUG)
    target_compile_definitions(bastion_core PUBLIC BASTION_DEBUG)
    target_compile_definitions(BastionTD PRIVATE BASTION_DEBUG)
endif()

if(BASTION_BUILD_TESTS)
    enable_testing()

    add_executable(test_pathfinding tests/test_pathfinding.cpp)
    target_link_libraries(test_pathfinding PRIVATE bastion_core)
    target_include_directories(test_pathfinding PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

    add_executable(test_economy tests/test_economy.cpp)
    target_link_libraries(test_economy PRIVATE bastion_core)
    target_include_directories(test_economy PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

    add_executable(test_combat tests/test_combat.cpp)
    target_link_libraries(test_combat PRIVATE bastion_core)
    target_include_directories(test_combat PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

    add_executable(test_wave tests/test_wave.cpp)
    target_link_libraries(test_wave PRIVATE bastion_core)
    target_include_directories(test_wave PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

    add_test(NAME pathfinding COMMAND test_pathfinding)
    add_test(NAME economy COMMAND test_economy)
    add_test(NAME combat COMMAND test_combat)
    add_test(NAME wave COMMAND test_wave)
endif()
