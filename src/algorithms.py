"""Graph algorithms for the Route Planner (Design and Analysis of Algorithms module).

Everything here is implemented from scratch in plain Python (only heapq and
itertools from the standard library):

* build_graph       - k-nearest-neighbour road network over the chosen listings
* dijkstra          - single-source shortest paths, binary heap, O((V + E) log V)
* bellman_ford      - single-source shortest paths by edge relaxation, O(V * E)
* tsp_held_karp     - exact Travelling Salesman by dynamic programming, O(n^2 * 2^n)
* tsp_nearest_neighbour + two_opt - greedy tour improved by 2-opt local search, O(n^2) per pass
* tsp_brute_force   - exhaustive search, O(n!), used only to verify the others in tests

Distances are great-circle (haversine) kilometres between listings. The graph
links each listing to its k nearest neighbours, so the shortest path between two
listings may go through other listings instead of a direct edge.
"""
import heapq
import math
import time
from itertools import permutations

INF = float("inf")


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- graph
def build_graph(points, k=3):
    """Undirected weighted graph {node: {neighbour: km}} linking every point to its
    k nearest neighbours. Disconnected components are then joined by their
    closest pair of points, so every listing is reachable."""
    n = len(points)
    graph = {i: {} for i in range(n)}

    def connect(i, j):
        w = haversine_km(points[i], points[j])
        graph[i][j] = graph[j][i] = w

    for i in range(n):
        nearest = sorted((haversine_km(points[i], points[j]), j) for j in range(n) if j != i)
        for _, j in nearest[:k]:
            connect(i, j)

    while True:
        comps = components(graph)
        if len(comps) <= 1:
            break
        a = comps[0]
        rest = [v for c in comps[1:] for v in c]
        _, i, j = min((haversine_km(points[i], points[j]), i, j) for i in a for j in rest)
        connect(i, j)
    return graph


def components(graph):
    """Connected components by iterative depth-first search."""
    seen, comps = set(), []
    for s in graph:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in graph[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comps.append(comp)
    return comps


def edge_list(graph):
    return [(u, v, w) for u in graph for v, w in graph[u].items() if u < v]


def path_to(prev, target):
    """Rebuild the path source -> target from a predecessor map."""
    path = []
    while target is not None:
        path.append(target)
        target = prev[target]
    return path[::-1]


# ---------------------------------------------------------------- shortest paths
def dijkstra(graph, source):
    """Dijkstra's algorithm with a binary min-heap and lazy deletion."""
    t = time.perf_counter()
    dist = {v: INF for v in graph}
    prev = {v: None for v in graph}
    dist[source] = 0.0
    heap = [(0.0, source)]
    done = set()
    order, relaxations, pushes = [], 0, 1
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:  # stale heap entry
            continue
        done.add(u)
        order.append(u)
        for v, w in graph[u].items():
            relaxations += 1
            if d + w < dist[v]:
                dist[v] = d + w
                prev[v] = u
                heapq.heappush(heap, (dist[v], v))
                pushes += 1
    return dist, prev, {"visit_order": order, "relaxations": relaxations, "heap_pushes": pushes,
                        "ms": (time.perf_counter() - t) * 1000}


def bellman_ford(graph, source):
    """Bellman-Ford: relax every directed edge up to V-1 times, stopping early once a
    full pass changes nothing, then run one more pass to detect negative cycles."""
    t = time.perf_counter()
    edges = [(u, v, w) for u in graph for v, w in graph[u].items()]  # both directions
    dist = {v: INF for v in graph}
    prev = {v: None for v in graph}
    dist[source] = 0.0
    passes, relaxations = 0, 0
    for _ in range(len(graph) - 1):
        passes += 1
        changed = False
        for u, v, w in edges:
            relaxations += 1
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                changed = True
        if not changed:
            break
    negative_cycle = any(dist[u] + w < dist[v] for u, v, w in edges)
    return dist, prev, {"passes": passes, "max_passes": len(graph) - 1, "relaxations": relaxations,
                        "directed_edges": len(edges), "negative_cycle": negative_cycle,
                        "ms": (time.perf_counter() - t) * 1000}


def all_pairs(graph):
    """Shortest-path distance matrix and predecessor maps (Dijkstra from every node)."""
    n = len(graph)
    D, prevs = [[0.0] * n for _ in range(n)], []
    for s in range(n):
        dist, prev, _ = dijkstra(graph, s)
        for j in range(n):
            D[s][j] = dist[j]
        prevs.append(prev)
    return D, prevs


# ---------------------------------------------------------------- travelling salesman
def tour_length(tour, D):
    return sum(D[tour[i]][tour[i + 1]] for i in range(len(tour) - 1))


def tsp_held_karp(D, start=0):
    """Exact TSP by Held-Karp dynamic programming over subsets (bitmasks).
    C[mask][j] = shortest path that starts at `start`, visits exactly the nodes in
    mask and ends at j. Returns a closed tour start -> ... -> start."""
    t = time.perf_counter()
    n = len(D)
    if n == 1:
        return [start, start], 0.0, {"states": 1, "ms": 0.0}
    others = [v for v in range(n) if v != start]
    m = len(others)
    full = (1 << m) - 1
    C = [[INF] * m for _ in range(1 << m)]
    parent = [[-1] * m for _ in range(1 << m)]
    for j in range(m):
        C[1 << j][j] = D[start][others[j]]
    states = 0
    for mask in range(1, full + 1):
        for j in range(m):
            if not mask & (1 << j) or C[mask][j] == INF:
                continue
            for k in range(m):
                if mask & (1 << k):
                    continue
                states += 1
                nm = mask | (1 << k)
                cand = C[mask][j] + D[others[j]][others[k]]
                if cand < C[nm][k]:
                    C[nm][k] = cand
                    parent[nm][k] = j
    best, last = min((C[full][j] + D[others[j]][start], j) for j in range(m))
    order, mask = [], full
    while last != -1:
        order.append(others[last])
        last, mask = parent[mask][last], mask & ~(1 << last)
    tour = [start] + order[::-1] + [start]
    return tour, best, {"states": states, "subsets": 1 << m, "ms": (time.perf_counter() - t) * 1000}


def tsp_nearest_neighbour(D, start=0):
    """Greedy tour: always walk to the closest unvisited listing."""
    n = len(D)
    tour, left = [start], set(range(n)) - {start}
    while left:
        nxt = min(left, key=lambda v: D[tour[-1]][v])
        tour.append(nxt)
        left.remove(nxt)
    return tour + [start]


def two_opt(tour, D):
    """2-opt local search: reverse any segment that shortens the tour, until no
    improving move is left."""
    tour = tour[:]
    improved, passes, swaps = True, 0, 0
    while improved:
        improved = False
        passes += 1
        for i in range(1, len(tour) - 2):
            for j in range(i + 1, len(tour) - 1):
                a, b, c, d = tour[i - 1], tour[i], tour[j], tour[j + 1]
                if D[a][c] + D[b][d] < D[a][b] + D[c][d] - 1e-12:
                    tour[i:j + 1] = reversed(tour[i:j + 1])
                    improved = True
                    swaps += 1
    return tour, {"passes": passes, "swaps": swaps}


def tsp_heuristic(D, start=0):
    t = time.perf_counter()
    greedy = tsp_nearest_neighbour(D, start)
    tour, st = two_opt(greedy, D)
    return tour, tour_length(tour, D), {"greedy_tour": greedy, "greedy_km": tour_length(greedy, D), **st,
                                        "ms": (time.perf_counter() - t) * 1000}


def tsp_brute_force(D, start=0):
    """O(n!) exhaustive search - only for verifying the other TSP solvers on tiny inputs."""
    others = [v for v in range(len(D)) if v != start]
    best = min(permutations(others), key=lambda p: tour_length([start, *p, start], D))
    tour = [start, *best, start]
    return tour, tour_length(tour, D)


def expand_tour(tour, prevs):
    """Turn a tour over the shortest-path distance matrix into the actual sequence of
    graph nodes walked (each leg follows its Dijkstra shortest path)."""
    walk = [tour[0]]
    for a, b in zip(tour, tour[1:]):
        walk += path_to(prevs[a], b)[1:]
    return walk


# ---------------------------------------------------------------- route planner
EXACT_TSP_LIMIT = 12


def plan_routes(points, start=0, target=None, k=3):
    """Run every algorithm on the selected listings and return a JSON-ready summary."""
    n = len(points)
    target = n - 1 if target is None else target
    graph = build_graph(points, k=k)
    edges = edge_list(graph)

    d_dist, d_prev, d_stats = dijkstra(graph, start)
    b_dist, b_prev, b_stats = bellman_ford(graph, start)
    D, prevs = all_pairs(graph)

    heur_tour, heur_km, heur_stats = tsp_heuristic(D, start)
    exact = None
    if n <= EXACT_TSP_LIMIT:
        ex_tour, ex_km, ex_stats = tsp_held_karp(D, start)
        exact = {"tour": ex_tour, "km": round(ex_km, 3), "walk": expand_tour(ex_tour, prevs),
                 "states": ex_stats["states"], "subsets": ex_stats["subsets"], "ms": round(ex_stats["ms"], 3)}

    r = lambda x: round(x, 3)
    return {
        "n": n, "k": k, "start": start, "target": target,
        "graph": {"edges": [[u, v, r(w)] for u, v, w in edges], "num_edges": len(edges),
                  "total_km": r(sum(w for *_, w in edges))},
        "dijkstra": {"distance": r(d_dist[target]), "path": path_to(d_prev, target),
                     "all_distances": [r(d_dist[v]) for v in range(n)],
                     "tree": [[d_prev[v], v] for v in range(n) if d_prev[v] is not None],
                     "visit_order": d_stats["visit_order"], "relaxations": d_stats["relaxations"],
                     "heap_pushes": d_stats["heap_pushes"], "ms": r(d_stats["ms"])},
        "bellman_ford": {"distance": r(b_dist[target]), "path": path_to(b_prev, target),
                         "all_distances": [r(b_dist[v]) for v in range(n)], "passes": b_stats["passes"],
                         "max_passes": b_stats["max_passes"], "relaxations": b_stats["relaxations"],
                         "directed_edges": b_stats["directed_edges"],
                         "negative_cycle": b_stats["negative_cycle"], "ms": r(b_stats["ms"])},
        "agree": all(abs(d_dist[v] - b_dist[v]) < 1e-9 for v in range(n)),
        "tsp_exact": exact,
        "tsp_heuristic": {"tour": heur_tour, "km": r(heur_km), "walk": expand_tour(heur_tour, prevs),
                          "greedy_tour": heur_stats["greedy_tour"], "greedy_km": r(heur_stats["greedy_km"]),
                          "two_opt_swaps": heur_stats["swaps"], "two_opt_passes": heur_stats["passes"],
                          "ms": r(heur_stats["ms"])},
        "matrix": [[r(x) for x in row] for row in D],
    }
