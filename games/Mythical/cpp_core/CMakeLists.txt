add_library(mythical_core STATIC
    src/campaign.cpp
    src/combat.cpp
    src/enemies.cpp
    src/fixed.cpp
    src/inventory.cpp
    src/items.cpp
    src/maps.cpp
    src/player.cpp
    src/quests.cpp
    src/save.cpp
    src/tilemap.cpp
    src/world.cpp
)
target_include_directories(mythical_core PUBLIC include)
target_compile_features(mythical_core PUBLIC cxx_std_17)

add_executable(test_campaign tests/test_campaign.cpp)
target_link_libraries(test_campaign PRIVATE mythical_core)
add_test(NAME test_campaign COMMAND test_campaign)

add_executable(test_inventory tests/test_inventory.cpp)
target_link_libraries(test_inventory PRIVATE mythical_core)
add_test(NAME test_inventory COMMAND test_inventory)

add_executable(test_world_save tests/test_world_save.cpp)
target_link_libraries(test_world_save PRIVATE mythical_core)
add_test(NAME test_world_save COMMAND test_world_save)

add_executable(test_combat tests/test_combat.cpp)
target_link_libraries(test_combat PRIVATE mythical_core)
add_test(NAME test_combat COMMAND test_combat)

add_executable(test_world tests/test_world.cpp)
target_link_libraries(test_world PRIVATE mythical_core)
add_test(NAME test_world COMMAND test_world)

add_executable(test_fixed tests/test_fixed.cpp)
target_link_libraries(test_fixed PRIVATE mythical_core)
add_test(NAME test_fixed COMMAND test_fixed)

add_executable(test_quests tests/test_quests.cpp)
target_link_libraries(test_quests PRIVATE mythical_core)
add_test(NAME test_quests COMMAND test_quests)

add_executable(test_tilemap tests/test_tilemap.cpp)
target_link_libraries(test_tilemap PRIVATE mythical_core)
add_test(NAME test_tilemap COMMAND test_tilemap)
