add_executable(mythical_cpp
    src/main.cpp
    src/render.cpp
    src/terminal.cpp
    src/save_io.cpp
)
target_link_libraries(mythical_cpp PRIVATE mythical_core)
target_include_directories(mythical_cpp PRIVATE src)
target_compile_features(mythical_cpp PRIVATE cxx_std_17)

add_executable(test_save_io
    tests/test_save_io.cpp
    src/save_io.cpp
)
target_link_libraries(test_save_io PRIVATE mythical_core)
target_include_directories(test_save_io PRIVATE src)
add_test(NAME test_save_io COMMAND test_save_io)
