"""Correctness tests for src/algorithms.py.  Run:  python -m unittest discover tests"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from algorithms import (INF, all_pairs, bellman_ford, build_graph, components, dijkstra, expand_tour,  # noqa: E402
                        path_to, plan_routes, tour_length, tsp_brute_force, tsp_held_karp, tsp_heuristic)


def random_points(n, seed):
    rng = random.Random(seed)
    return [(48.85 + rng.uniform(-.05, .05), 2.35 + rng.uniform(-.07, .07)) for _ in range(n)]


def floyd_warshall(graph):
    n = len(graph)
    D = [[0 if i == j else graph[i].get(j, INF) for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if D[i][k] + D[k][j] < D[i][j]:
                    D[i][j] = D[i][k] + D[k][j]
    return D


class TestGraph(unittest.TestCase):
    def test_graph_is_connected_and_symmetric(self):
        for seed in range(20):
            g = build_graph(random_points(15, seed), k=2)
            self.assertEqual(len(components(g)), 1)
            for u in g:
                for v, w in g[u].items():
                    self.assertAlmostEqual(g[v][u], w)


class TestShortestPaths(unittest.TestCase):
    def test_dijkstra_and_bellman_ford_match_floyd_warshall(self):
        for seed in range(30):
            g = build_graph(random_points(12, seed), k=2)
            ref = floyd_warshall(g)
            for s in range(len(g)):
                d, _, _ = dijkstra(g, s)
                b, _, st = bellman_ford(g, s)
                self.assertFalse(st["negative_cycle"])
                for v in g:
                    self.assertAlmostEqual(d[v], ref[s][v], places=9)
                    self.assertAlmostEqual(b[v], ref[s][v], places=9)

    def test_paths_are_valid_and_sum_to_distance(self):
        g = build_graph(random_points(14, 7), k=2)
        dist, prev, _ = dijkstra(g, 0)
        for t in g:
            p = path_to(prev, t)
            self.assertEqual(p[0], 0)
            self.assertEqual(p[-1], t)
            self.assertAlmostEqual(sum(g[a][b] for a, b in zip(p, p[1:])), dist[t])

    def test_hand_worked_example(self):
        # A-B 4, A-C 1, C-B 2, B-D 1, C-D 5  ->  A to D = A-C-B-D = 4
        g = {0: {1: 4, 2: 1}, 1: {0: 4, 2: 2, 3: 1}, 2: {0: 1, 1: 2, 3: 5}, 3: {1: 1, 2: 5}}
        for algo in (dijkstra, bellman_ford):
            dist, prev, _ = algo(g, 0)
            self.assertEqual(dist[3], 4)
            self.assertEqual(path_to(prev, 3), [0, 2, 1, 3])

    def test_bellman_ford_handles_negative_edges_and_detects_cycles(self):
        g = {0: {1: 4, 2: 5}, 1: {}, 2: {1: -3}}
        dist, _, st = bellman_ford(g, 0)
        self.assertEqual(dist[1], 2)
        self.assertFalse(st["negative_cycle"])
        cyc = {0: {1: 1}, 1: {2: -2}, 2: {1: 1}}
        self.assertTrue(bellman_ford(cyc, 0)[2]["negative_cycle"])


class TestTSP(unittest.TestCase):
    def test_held_karp_matches_brute_force(self):
        for seed in range(15):
            n = 3 + seed % 6  # 3..8 nodes
            D, _ = all_pairs(build_graph(random_points(n, seed), k=2))
            _, hk = tsp_held_karp(D, 0)[:2]
            _, bf = tsp_brute_force(D, 0)
            self.assertAlmostEqual(hk, bf, places=9)

    def test_tours_visit_every_node_once(self):
        D, _ = all_pairs(build_graph(random_points(10, 3), k=3))
        for tour, km in [tsp_held_karp(D, 2)[:2], tsp_heuristic(D, 2)[:2]]:
            self.assertEqual(tour[0], 2)
            self.assertEqual(tour[-1], 2)
            self.assertEqual(sorted(tour[:-1]), list(range(10)))
            self.assertAlmostEqual(tour_length(tour, D), km)

    def test_heuristic_never_beats_exact(self):
        for seed in range(15):
            D, _ = all_pairs(build_graph(random_points(9, seed), k=2))
            exact = tsp_held_karp(D, 0)[1]
            heur = tsp_heuristic(D, 0)[1]
            self.assertGreaterEqual(heur + 1e-9, exact)

    def test_expanded_walk_uses_graph_edges(self):
        g = build_graph(random_points(10, 11), k=2)
        D, prevs = all_pairs(g)
        tour = tsp_held_karp(D, 0)[0]
        walk = expand_tour(tour, prevs)
        for a, b in zip(walk, walk[1:]):
            self.assertIn(b, g[a])
        self.assertAlmostEqual(sum(g[a][b] for a, b in zip(walk, walk[1:])), tour_length(tour, D))


class TestPlanner(unittest.TestCase):
    def test_plan_routes_summary(self):
        out = plan_routes(random_points(8, 5), start=0, target=7, k=3)
        self.assertTrue(out["agree"])
        self.assertEqual(out["dijkstra"]["distance"], out["bellman_ford"]["distance"])
        self.assertLessEqual(out["tsp_exact"]["km"], out["tsp_heuristic"]["km"] + 1e-6)

    def test_exact_tsp_skipped_for_large_inputs(self):
        out = plan_routes(random_points(15, 1), start=0, k=3)
        self.assertIsNone(out["tsp_exact"])
        self.assertEqual(len(out["tsp_heuristic"]["tour"]), 16)


if __name__ == "__main__":
    unittest.main()
