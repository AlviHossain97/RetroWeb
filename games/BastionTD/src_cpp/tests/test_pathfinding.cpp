#include "core/grid.h"
#include "core/pathfinding.h"

#include <cassert>
#include <cstdio>

void test_bfs_simple_path() {
    Grid g;
    g.init();
    g.set(0, 0, Terrain::Spawn);
    g.set(4, 4, Terrain::Base);

    const Path p = bfs(g, {0.0f, 0.0f}, {4.0f, 4.0f});
    assert(p.valid);
    assert(p.length == 9);
    assert(p.points[0].x == 0.0f && p.points[0].y == 0.0f);
    assert(p.points[p.length - 1].x == 4.0f && p.points[p.length - 1].y == 4.0f);
    std::printf("PASS: test_bfs_simple_path\n");
}

void test_bfs_no_path() {
    Grid g;
    g.init();
    for (int y = 0; y < cfg::GRID_H; ++y) {
        g.set(2, y, Terrain::Rock);
    }
    g.set(0, 0, Terrain::Spawn);
    g.set(4, 0, Terrain::Base);

    const Path p = bfs(g, {0.0f, 0.0f}, {4.0f, 0.0f});
    assert(!p.valid);
    std::printf("PASS: test_bfs_no_path\n");
}

void test_bfs_avoids_blocked() {
    Grid g;
    g.init();
    g.set(1, 0, Terrain::Rock);
    g.set(0, 0, Terrain::Spawn);
    g.set(2, 0, Terrain::Base);

    const Path p = bfs(g, {0.0f, 0.0f}, {2.0f, 0.0f});
    assert(p.valid);
    for (int i = 0; i < p.length; ++i) {
        assert(!(p.points[i].x == 1.0f && p.points[i].y == 0.0f));
    }
    std::printf("PASS: test_bfs_avoids_blocked\n");
}

int main() {
    test_bfs_simple_path();
    test_bfs_no_path();
    test_bfs_avoids_blocked();
    std::printf("All pathfinding tests passed.\n");
    return 0;
}
