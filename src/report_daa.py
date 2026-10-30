"""Design and Analysis of Algorithms report: reports/Altitude_DAA_Report.pdf (target 15-20 pages)."""
import heapq
import math

from algorithms import EXACT_TSP_LIMIT, bellman_ford, dijkstra, path_to, tsp_held_karp
from pdf_common import *  # noqa: F403  (layout helpers, styles, data)

DOC.update(title="Altitude - Design and Analysis of Algorithms Report",
           header="Altitude - Route Planning over Airbnb Listings", subject="DAA Report")

RX = json.loads((REPORTS_DIR / "route_example.json").read_text(encoding="utf-8"))
BM = json.loads((REPORTS_DIR / "algo_benchmark.json").read_text())

# small hand-worked inputs (the same 4-node graph is used in tests/test_algorithms.py)
L4 = "ABCD"
G4 = {0: {1: 4, 2: 1}, 1: {0: 4, 2: 2, 3: 1}, 2: {0: 1, 1: 2, 3: 5}, 3: {1: 1, 2: 5}}
D4 = [[0, 2, 9, 10], [2, 0, 6, 4], [9, 6, 0, 8], [10, 4, 8, 0]]
fmt = lambda v: "∞" if v == math.inf else f"{v:g}"


def dijkstra_trace(g, s):
    dist = {v: math.inf for v in g}; dist[s] = 0
    heap, done, rows = [(0, s)], set(), []
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            rows.append(["-", f"({d}, {L4[u]}) stale, skipped"] + [""] * 4 + [""])
            continue
        done.add(u)
        for v, w in g[u].items():
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (dist[v], v))
        rows.append([len(done), f"settle {L4[u]} (d = {d})"] + [fmt(dist[v]) for v in g] +
                    [", ".join(f"({x},{L4[y]})" for x, y in sorted(heap)) or "empty"])
    return rows


def bellman_ford_trace(g, s):
    edges = [(u, v, w) for u in g for v, w in g[u].items()]
    dist = {v: math.inf for v in g}; dist[s] = 0
    rows = [["0 (init)"] + [fmt(dist[v]) for v in g] + ["-"]]
    for p in range(1, len(g)):
        changes = []
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changes.append(f"{L4[u]}→{L4[v]}")
        rows.append([str(p)] + [fmt(dist[v]) for v in g] + [", ".join(changes) or "no change: stop"])
        if not changes:
            break
    return rows, edges


def held_karp_trace(D, start=0):
    others = [v for v in range(len(D)) if v != start]
    C, rows = {}, []
    for j in others:
        C[(frozenset([j]), j)] = (D[start][j], start)
    for size in range(1, len(others) + 1):
        for (S_, j), (c, p) in sorted(((k, v) for k, v in C.items() if len(k[0]) == size),
                                      key=lambda kv: (sorted(kv[0][0]), kv[0][1])):
            rows.append(["{" + ",".join(str(x) for x in sorted(S_)) + "}", j, f"{c:g}", p])
        for (S_, j), (c, _) in [(k, v) for k, v in C.items() if len(k[0]) == size]:
            for k in others:
                if k in S_:
                    continue
                key = (S_ | {k}, k)
                if key not in C or c + D[j][k] < C[key][0]:
                    C[key] = (c + D[j][k], j)
    full = frozenset(others)
    best = min((C[(full, j)][0] + D[j][start], j) for j in others)
    return rows, best


def build():
    cover("DESIGN AND ANALYSIS OF ALGORITHMS REPORT", "Altitude: Route Planning over Airbnb Listings",
          "Shortest paths with Dijkstra and Bellman-Ford, and the Travelling Salesman Problem with Held-Karp "
          "dynamic programming and the 2-opt heuristic, implemented from scratch in Python",
          [["Subject", "Design and Analysis of Algorithms"],
           ["Algorithms", "Dijkstra, Bellman-Ford, Held-Karp, nearest neighbour + 2-opt, DFS, brute force"],
           ["Verification", "11 unit tests against Floyd-Warshall and brute force, all passing"]],
          shot="20_route_map.png")

    # ---------------------------------------------------------------- 1
    chapter("1. Introduction")
    P("Altitude is a web application about Airbnb listings in ten European cities. Its Route Planner answers "
      "two classic algorithmic questions for a traveller who wants to visit several listings, for example to "
      "view apartments before booking:")
    bullets(["<b>Shortest path:</b> what is the shortest way from my starting listing to each other listing, "
             "moving along a network that connects nearby listings?",
             "<b>Travelling Salesman Problem (TSP):</b> in which order should I visit all the chosen listings, "
             "and return to the start, to travel the least distance?"])
    P("The first is solved in polynomial time by two different paradigms, greedy (Dijkstra) and dynamic "
      "programming (Bellman-Ford). The second is NP-hard. It is solved exactly by exponential-time dynamic "
      "programming (Held-Karp) and approximately by a fast greedy-plus-local-search heuristic "
      "(nearest neighbour + 2-opt). Every algorithm is implemented from scratch in "
      "<font face='Mono'>src/algorithms.py</font>, using only the standard library's "
      "<font face='Mono'>heapq</font> for the priority queue, and served to the browser through "
      "<font face='Mono'>POST /api/route</font>.")
    H2("1.1 Objectives")
    bullets(["Model the trip-planning problem as a weighted graph.",
             "Implement Dijkstra, Bellman-Ford, Held-Karp and 2-opt, and state and justify their complexity.",
             "Prove or argue correctness, and verify it with tests against independent reference algorithms.",
             "Measure run times empirically and compare them with the theoretical growth rates.",
             "Make the algorithms interactive in a web interface on real listing locations."])
    H2("1.2 Algorithm design paradigms covered")
    table([["Paradigm", "Algorithm in this project", "Problem"],
           ["Greedy", "Dijkstra; nearest-neighbour tour", "Shortest path; TSP construction"],
           ["Dynamic programming", "Bellman-Ford; Held-Karp", "Shortest path; exact TSP"],
           ["Graph traversal", "Depth-first search", "Connected components"],
           ["Local search", "2-opt", "TSP improvement"],
           ["Brute force", "All permutations (used in tests)", "Exact TSP reference"],
           ["Priority queue", "Binary min-heap (heapq)", "Dijkstra's frontier"]],
          col_w=[4 * cm, 6.5 * cm, CONTENT_W - 10.5 * cm])

    # ---------------------------------------------------------------- 2
    H1("2. Problem Modelling")
    H2("2.1 Graph definition")
    P("Let the n listings selected by the user be the vertex set V. The weight of an edge (u, v) is the "
      "great-circle distance between the two listings, from the haversine formula:")
    story.append(Preformatted("d(u, v) = 2R · asin( sqrt( sin²(Δφ/2) + cos φu · cos φv · sin²(Δλ/2) ) ),   R = 6371 km",
                              S["code"]))
    P("A complete graph would make every shortest path a single direct edge, which is uninteresting. Instead "
      "each vertex is joined to its <b>k nearest neighbours</b> (default k = 3), which imitates a sparse street "
      "network. The graph is undirected and |E| ≤ k·n. Because a k-nearest-neighbour graph can be "
      "disconnected, <b>depth-first search</b> finds the connected components, and the closest pair of vertices "
      "between the first component and the rest is joined until only one component remains.")
    code("src/algorithms.py", "build_graph", 24, "Listing 2.1 - Building the k-nearest-neighbour graph "
         "(adjacency dictionary {u: {v: km}}).")
    P("<b>Complexity.</b> For each of the n vertices the other n − 1 distances are sorted: O(n² log n). Each "
      "DFS is O(V + E), and joining components takes at most O(n²) per join. The adjacency dictionary uses "
      "O(V + E) space. With n ≤ 20 in the app, construction is negligible.")
    H2("2.2 Representation")
    P("The graph is a dictionary of dictionaries: <font face='Mono'>graph[u][v] = weight</font>. This gives O(1) "
      "average edge lookup, iterates neighbours in O(deg u), and stores each undirected edge in both "
      "directions. For the TSP, an n × n matrix of shortest-path distances is computed by running Dijkstra "
      "from every vertex. This is the <i>metric closure</i>, so every leg of a tour follows a real path in the "
      "graph.")

    # ---------------------------------------------------------------- 3
    H1("3. Dijkstra's Algorithm")
    H2("3.1 Idea and pseudocode")
    P("Dijkstra's algorithm grows a set of <i>settled</i> vertices whose shortest distance from the source s is "
      "final. It repeatedly settles the unsettled vertex with the smallest tentative distance, then "
      "<i>relaxes</i> its outgoing edges: if going through u gives v a shorter distance, the distance is "
      "updated. A binary min-heap holds the frontier. Instead of a decrease-key operation, a new entry is "
      "pushed and stale entries are skipped when popped (lazy deletion).")
    story.append(Preformatted(
        "Dijkstra(G, s):\n"
        "    dist[v] = INF for all v;  dist[s] = 0;  heap = [(0, s)]\n"
        "    while heap not empty:\n"
        "        (d, u) = pop_min(heap)\n"
        "        if u is settled: continue                 # stale entry\n"
        "        settle u\n"
        "        for each edge (u, v, w):\n"
        "            if d + w < dist[v]:\n"
        "                dist[v] = d + w;  prev[v] = u;  push(heap, (dist[v], v))", S["code"]))
    H2("3.2 Correctness")
    P("<b>Claim:</b> when a vertex u is settled, dist[u] equals the true shortest distance δ(s, u). "
      "<b>Argument (exchange):</b> suppose u is the first vertex settled with dist[u] > δ(s, u). Take a "
      "shortest path from s to u, and let y be its first vertex that is not yet settled, with x settled just "
      "before it. Since x was settled correctly and the edge (x, y) was relaxed, "
      "dist[y] ≤ δ(s, x) + w(x, y) = δ(s, y) ≤ δ(s, u) < dist[u]. With non-negative weights, the heap would "
      "therefore pop y before u, a contradiction. The argument needs non-negative weights, which holds for "
      "distances.")
    H2("3.3 Complexity")
    P("Each vertex is settled once. Each edge is relaxed at most once per direction and pushes at most one "
      "heap entry, so the heap holds O(E) entries and every push and pop costs O(log E) = O(log V). The total is "
      "<b>O((V + E) log V)</b> time and O(V + E) space. With a Fibonacci heap this would improve to "
      "O(E + V log V), but the binary heap is simpler and faster in practice for small graphs.")
    H2("3.4 Trace on a 4-vertex graph")
    P("Edges: A-B 4, A-C 1, B-C 2, B-D 1, C-D 5; source A. The direct edge A-B (4) is beaten by A-C-B (3), and "
      "A-D comes out as A-C-B-D (4).")
    table([["Step", "Action", "A", "B", "C", "D", "Heap after step"]] + dijkstra_trace(G4, 0),
          col_w=[1.2 * cm, 4.2 * cm, 1 * cm, 1 * cm, 1 * cm, 1 * cm, CONTENT_W - 9.4 * cm], font=9)
    dist, prev, _ = dijkstra(G4, 0)
    P(f"Final distances: " + ", ".join(f"{L4[v]} = {dist[v]:g}" for v in G4) + ". Shortest path to D: "
      + " → ".join(L4[v] for v in path_to(prev, 3)) + ". The entries (4, B) and (6, D) went stale when B and D "
      "found shorter distances; they are skipped when popped, which is lazy deletion at work.")
    H2("3.5 Implementation")
    code("src/algorithms.py", "dijkstra", 24, "Listing 3.1 - Dijkstra with heapq and lazy deletion; it also counts "
         "relaxations and heap pushes for the analysis.")

    # ---------------------------------------------------------------- 4
    H1("4. Bellman-Ford Algorithm")
    H2("4.1 Idea and pseudocode")
    P("Bellman-Ford relaxes <i>every</i> edge, in a fixed order, in repeated passes. After pass i, every "
      "shortest path that uses at most i edges has been found. A shortest path in a graph without negative "
      "cycles has at most V − 1 edges, so V − 1 passes suffice. One extra pass detects a negative cycle: if any "
      "edge can still be relaxed, distances can decrease forever. This implementation also stops early when "
      "a pass changes nothing.")
    story.append(Preformatted(
        "Bellman-Ford(G, s):\n"
        "    dist[v] = INF for all v;  dist[s] = 0\n"
        "    repeat V - 1 times:\n"
        "        changed = false\n"
        "        for each directed edge (u, v, w):\n"
        "            if dist[u] + w < dist[v]:  dist[v] = dist[u] + w;  prev[v] = u;  changed = true\n"
        "        if not changed: break                        # early exit\n"
        "    negative_cycle = exists (u, v, w) with dist[u] + w < dist[v]", S["code"]))
    H2("4.2 Correctness and complexity")
    P("<b>Path-relaxation property:</b> if v0 = s, v1, ..., vk is a shortest path and its edges are relaxed in "
      "that order (with any other relaxations in between), then dist[vk] = δ(s, vk). Pass i relaxes all edges, "
      "so it relaxes the i-th edge of every shortest path, and by induction all shortest paths of at most i "
      "edges are correct after pass i. Each pass costs O(E), and there are at most V − 1 passes plus one check, "
      "so the total is <b>O(V · E)</b> time and O(V) extra space. Unlike Dijkstra, the algorithm is correct with "
      "negative edge weights, which is why it is the basis of distance-vector routing.")
    H2("4.3 Trace on the same graph")
    bf_rows, edges = bellman_ford_trace(G4, 0)
    P("Edge order per pass: " + ", ".join(f"{L4[u]}→{L4[v]}" for u, v, _ in edges) + ".")
    table([["Pass", "A", "B", "C", "D", "Edges that improved a distance"]] + bf_rows,
          col_w=[1.8 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, CONTENT_W - 6.6 * cm], font=9)
    bdist, _, bst = bellman_ford(G4, 0)
    P(f"In pass 1, B→D sets D to 5 using B's old distance of 4; C→B then lowers B to 3, but only after B→D has "
      f"already been relaxed. D therefore reaches its true distance of 4 (route A-C-B-D, three edges) in pass 2. "
      f"Pass 3 changes nothing, so the loop stops after "
      f"{bst['passes']} of {bst['max_passes']} allowed passes, with the same distances as Dijkstra. The "
      f"unit tests also check a graph with a negative edge (Bellman-Ford returns the correct distance) and "
      f"a negative cycle (detected).")
    code("src/algorithms.py", "bellman_ford", 26, "Listing 4.1 - Bellman-Ford with early exit and negative-cycle detection.")

    # ---------------------------------------------------------------- 5
    H1("5. The Travelling Salesman Problem")
    P("Given n locations and the distance between every pair, the TSP asks for the shortest closed tour that "
      "visits each location exactly once. Its decision version is NP-complete, so no polynomial-time algorithm "
      "is known. The number of distinct tours of n locations is (n − 1)!/2, which makes brute force hopeless "
      "beyond about 12 locations:")
    rows = [["n", "Tours (n−1)!/2", "Brute force ~n!", "Held-Karp ~n²·2ⁿ"]]
    for n in [5, 8, 10, 12, 15, 20]:
        rows.append([n, f"{math.factorial(n - 1) // 2:,}", f"{math.factorial(n):.2e}", f"{n * n * 2 ** n:,}"])
    table(rows, col_w=[1.5 * cm] + [(CONTENT_W - 1.5 * cm) / 3] * 3, font=9)
    H2("5.1 Held-Karp dynamic programming")
    P("Held-Karp avoids enumerating every order by noticing that the best way to finish a tour depends only "
      "on <i>which</i> locations have been visited and <i>where</i> you are now, not on the order so far. "
      "Let C(S, j) be the length of the shortest path that starts at the start vertex, visits exactly the set "
      "S, and ends at j ∈ S. Then:")
    story.append(Preformatted(
        "C({j}, j)    = D[start][j]\n"
        "C(S + k, k)  = min over j in S of  C(S, j) + D[j][k]          for k not in S\n"
        "optimum      = min over j of  C(all, j) + D[j][start]", S["code"]))
    P("<b>Optimal substructure:</b> the last edge of an optimal path ending at k comes from some j, and the "
      "part before it must itself be optimal for (S, j); otherwise it could be replaced by a shorter one. "
      "<b>Complexity:</b> there are 2ⁿ⁻¹ subsets and n end vertices, so O(n · 2ⁿ) states, and each state "
      "takes a minimum over n predecessors: <b>O(n² · 2ⁿ) time and O(n · 2ⁿ) space</b>. The subsets are "
      "stored as integer bitmasks, so set membership and union are single bit operations.")
    hk_rows, (best, _) = held_karp_trace(D4)
    tour, km, _ = tsp_held_karp(D4, 0)
    P("<b>Trace</b> on four cities 0-3 with distances 0-1 = 2, 0-2 = 9, 0-3 = 10, 1-2 = 6, 1-3 = 4, 2-3 = 8 "
      "(start 0). Each row is one DP state, with the predecessor that achieved it:")
    table([["Subset S", "End j", "C(S, j)", "Came from"]] + hk_rows, col_w=[3.5 * cm] + [(CONTENT_W - 3.5 * cm) / 3] * 3,
          font=9)
    P(f"Closing the tour: min over j of C({{1,2,3}}, j) + D[j][0] = {best:g}. The optimal tour is "
      + " → ".join(map(str, tour)) + f" with length {km:g}, the same as brute force.")
    code("src/algorithms.py", "tsp_held_karp", 36, "Listing 5.1 - Held-Karp over bitmask subsets with parent pointers "
         "to rebuild the tour.")
    H2("5.2 Nearest neighbour + 2-opt heuristic")
    P("<b>Nearest neighbour</b> (greedy) always moves to the closest unvisited location: O(n²), but it often "
      "leaves long edges and crossings near the end. <b>2-opt</b> (local search) then looks at every pair of "
      "edges (a, b) and (c, d). If D[a][c] + D[b][d] < D[a][b] + D[c][d], it reverses the segment between "
      "them, which removes a crossing. It repeats until no improving move exists. Each pass checks O(n²) pairs. "
      "The result is a <i>local</i> optimum: no single 2-opt move helps, but the tour is not guaranteed to be "
      "globally optimal.")
    code("src/algorithms.py", "two_opt", 16, "Listing 5.2 - 2-opt local search.")

    # ---------------------------------------------------------------- 6
    H1("6. Implementation in the Application")
    P(f"In the Route Planner page the user picks a city and clicks up to 20 listings on the map. The browser sends "
      f"their coordinates, the start, the target and k to <font face='Mono'>POST /api/route</font>. "
      f"<font face='Mono'>plan_routes()</font> builds the graph and runs Dijkstra and Bellman-Ford from the start, "
      f"Dijkstra from every vertex for the distance matrix, the heuristic, and Held-Karp when n ≤ "
      f"{EXACT_TSP_LIMIT}. It returns paths, tours, distances, operation counts and timings as JSON.")
    H2("6.1 Worked example: nine Paris landmarks")
    P(f"The example uses the Paris listing closest to each of nine landmarks, starting at the Eiffel Tower, "
      f"with Bastille as the shortest-path target (k = {RX['k']}: {RX['n']} vertices, "
      f"{RX['graph']['num_edges']} edges).")
    img(SHOTS / "20_route_map.png", "Screenshot 6.1 - Exact TSP tour (red), Dijkstra path to Bastille (blue), graph "
        "edges (dashed) and numbered stops.", max_h=CONTENT_H * .4)
    names = RX["landmarks"]
    parent = {v: p for p, v in RX["dijkstra"]["tree"]}
    rows = [["Stop", "Near", "Dijkstra km", "Bellman-Ford km", "Shortest path"]]
    for i, nm in enumerate(names):
        pth, v = [i], i
        while v in parent:
            v = parent[v]; pth.insert(0, v)
        rows.append([i + 1, nm, f"{RX['dijkstra']['all_distances'][i]:.3f}", f"{RX['bellman_ford']['all_distances'][i]:.3f}",
                     " → ".join(str(p + 1) for p in pth)])
    table(rows, font=9)
    d, b, x, h = RX["dijkstra"], RX["bellman_ford"], RX["tsp_exact"], RX["tsp_heuristic"]
    table([["Algorithm", "Result", "Route", "Work done"],
           ["Dijkstra", f"{d['distance']:.2f} km", " → ".join(str(p + 1) for p in d["path"]),
            f"{d['relaxations']} relaxations, {d['heap_pushes']} heap pushes"],
           ["Bellman-Ford", f"{b['distance']:.2f} km", " → ".join(str(p + 1) for p in b["path"]),
            f"{b['passes']} of {b['max_passes']} passes, {b['relaxations']} relaxations"],
           ["Held-Karp", f"{x['km']:.2f} km", " → ".join(str(p + 1) for p in x["tour"]),
            f"{x['subsets']} subsets, {x['states']:,} transitions"],
           ["NN + 2-opt", f"{h['km']:.2f} km", " → ".join(str(p + 1) for p in h["tour"]),
            f"greedy {h['greedy_km']:.2f} km, {h['two_opt_swaps']} swap(s)"]],
          col_w=[2.6 * cm, 2.2 * cm, 6 * cm, CONTENT_W - 10.8 * cm], font=9)
    P(f"Both shortest-path algorithms agree on every stop. The route to Bastille goes through the Louvre "
      f"listing ({d['distance']:.2f} km) because the two have no direct edge. The greedy tour "
      + " → ".join(str(p + 1) for p in h["greedy_tour"]) +
      f" was {h['greedy_km']:.2f} km, {(h['greedy_km'] / x['km'] - 1) * 100:.0f}% longer than optimal; one 2-opt "
      f"swap removed its crossing and reached the {x['km']:.2f} km optimum found by Held-Karp.")
    pair(["20_route_map.png", "21_route_map_heuristic.png"], ["Held-Karp exact tour", "Nearest neighbour + 2-opt tour"],
         "Screenshot 6.2 - The two TSP tours drawn on the map.", CONTENT_H * .3)
    img(SHOTS / "22_route_algorithms.png", "Screenshot 6.3 - Result cards: complexity, route, operation counts and "
        "run time for each algorithm.", max_h=CONTENT_H * .38)
    img(SHOTS / "23_route_tables.png", "Screenshot 6.4 - Cross-check of the two shortest-path algorithms, and the "
        "all-pairs distance matrix used by the TSP.", max_h=CONTENT_H * .38)

    # ---------------------------------------------------------------- 7
    H1("7. Testing and Verification")
    P("<font face='Mono'>tests/test_algorithms.py</font> has 11 <font face='Mono'>unittest</font> tests, all "
      "passing. The key idea is to compare each algorithm with an independent reference that is simple enough "
      "to be obviously correct:")
    table([["Test", "Reference", "Inputs"],
           ["Dijkstra and Bellman-Ford distances", "Floyd-Warshall O(V³)", "30 random graphs, every source"],
           ["Paths are valid and sum to the distance", "Edge-by-edge check", "random graph"],
           ["Hand-worked example (Chapter 3)", "Known answer A-C-B-D = 4", "4 vertices"],
           ["Negative edge, negative cycle", "Known answers", "small directed graphs"],
           ["Held-Karp is optimal", "Brute force O(n!)", "15 instances, 3-8 stops"],
           ["2-opt never beats the optimum", "Held-Karp", "15 instances, 9 stops"],
           ["Tours visit every stop once", "Sorted-set check", "both TSP solvers"],
           ["Walks use real edges; graph connected and symmetric", "DFS, adjacency check", "random graphs"],
           ["Planner summary; exact TSP skipped above the limit", "plan_routes()", "8 and 15 stops"]],
          col_w=[6.2 * cm, 4.8 * cm, CONTENT_W - 11 * cm], font=9)
    code("tests/test_algorithms.py", "test_held_karp_matches_brute_force", 8, "Listing 7.1 - Exact TSP checked "
         "against brute force.")

    # ---------------------------------------------------------------- 8
    H1("8. Empirical Analysis")
    sp, ts = BM["shortest_path"], BM["tsp"]
    img(RFIG / "algo_benchmark.png", "Figure 8.1 - Measured run times (log scale) and the 2-opt optimality gap on random "
        "Paris-sized instances.", max_h=CONTENT_H * .28)
    rows = [["Stops V", "Edges E", "Dijkstra ms", "Bellman-Ford ms", "Ratio"]]
    for i, n in enumerate(sp["n"]):
        rows.append([n, sp["edges"][i], f"{sp['dijkstra'][i]:.3f}", f"{sp['bellman_ford'][i]:.3f}",
                     f"{sp['bellman_ford'][i] / sp['dijkstra'][i]:.1f}×"])
    table(rows, font=9)
    P(f"<b>Shortest paths.</b> With k = 3, E ≈ 2V, so Dijkstra's O((V + E) log V) is close to linear, and the "
      f"measurements grow almost in proportion to V. Bellman-Ford is {sp['bellman_ford'][-1] / sp['dijkstra'][-1]:.0f}× "
      f"slower at {sp['n'][-1]} stops and the gap widens as V grows. Thanks to the early exit it needs far fewer "
      f"than V − 1 passes on these geometric graphs, so it stays well below its O(V · E) worst case, but every "
      f"pass still scans every edge.")
    rows = [["Stops n"] + [str(n) for n in ts["n"]],
            ["Held-Karp ms"] + [f"{v:.2f}" for v in ts["held_karp"]],
            ["NN + 2-opt ms"] + [f"{v:.2f}" for v in ts["heuristic"]],
            ["Mean gap %"] + [f"{v:.2f}" for v in ts["gap_mean"]],
            ["Worst gap %"] + [f"{v:.1f}" for v in ts["gap_max"]],
            ["Optimal in %"] + [f"{v:.0f}" for v in ts["optimal_pct"]]]
    table(rows, font=8.5)
    growth = [ts["held_karp"][i + 1] / ts["held_karp"][i] for i in range(len(ts["n"]) - 1) if ts["n"][i] >= 8]
    g = sum(growth) / len(growth)
    P(f"<b>TSP.</b> Theory predicts that Held-Karp's time grows by 2·((n+1)/n)² per extra stop, about 2.3-2.5 "
      f"for these sizes. The measured factor is {g:.1f}×, reaching {ts['held_karp'][-1]:.0f} ms at "
      f"{ts['n'][-1]} stops. Extrapolating, 20 stops would take about "
      f"{ts['held_karp'][-1] * g ** (20 - ts['n'][-1]) / 1000:.0f} seconds in pure Python and need "
      f"{19 * 2 ** 19 / 1e6:.0f} million DP entries in memory, and every extra stop doubles that again. This is "
      f"why the app switches to the heuristic above {EXACT_TSP_LIMIT} stops, so every request stays instant. Nearest neighbour + 2-opt stays below 0.1 ms. Across 25 random instances per size it "
      f"found the exact optimum in {min(ts['optimal_pct']):.0f}-{max(ts['optimal_pct']):.0f}% of cases, with a mean "
      f"gap below {max(ts['gap_mean']) + .5:.0f}%. Its worst case, {max(ts['gap_max']):.0f}% longer than optimal, "
      f"shows the price of giving up the optimality guarantee.")

    # ---------------------------------------------------------------- 9
    H1("9. Comparison and Conclusion")
    table([["Algorithm", "Paradigm", "Time", "Space", "Optimal?", "Negative weights"],
           ["Dijkstra", "Greedy", "O((V+E) log V)", "O(V+E)", "Yes", "No"],
           ["Bellman-Ford", "Dynamic programming", "O(V·E)", "O(V)", "Yes", "Yes, detects cycles"],
           ["Held-Karp", "Dynamic programming", "O(n²·2ⁿ)", "O(n·2ⁿ)", "Yes", "n/a"],
           ["NN + 2-opt", "Greedy + local search", "O(n²) per pass", "O(n)", "No (local optimum)", "n/a"],
           ["Brute force", "Exhaustive", "O(n!)", "O(n)", "Yes", "n/a"]],
          col_w=[2.6 * cm, 3.6 * cm, 2.8 * cm, 1.9 * cm, 2.9 * cm, CONTENT_W - 13.8 * cm], font=9)
    P("The project shows the central trade-offs of algorithm design on a real problem. For shortest paths, the "
      "greedy algorithm wins whenever its precondition, non-negative weights, holds. The more general "
      "dynamic-programming algorithm pays for its generality with an extra factor of roughly V. For the TSP, "
      "exact dynamic programming turns an O(n!) search into O(n²·2ⁿ). That is a huge saving, yet still "
      "exponential, so a polynomial heuristic is essential beyond a dozen stops. In practice the heuristic was "
      "optimal most of the time, but not always. Each claim was checked twice: the unit tests confirm "
      "correctness against independent references, and the benchmark confirms the predicted growth rates.")
    H2("Limitations and future work")
    bullets(["Edge weights are straight-line distances; a real street graph (e.g. OpenStreetMap) would give walking "
             "or driving distances.",
             "Further algorithms that fit the same application: Prim/Kruskal minimum spanning trees with union-find, "
             "0/1 knapsack for choosing listings within a budget, branch and bound for the TSP, and A* search for "
             "point-to-point paths."])
    H2("References")
    for r in ["Cormen, T. H., Leiserson, C. E., Rivest, R. L. and Stein, C. (2022). <i>Introduction to Algorithms</i>, "
              "4th ed. MIT Press.",
              "Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. <i>Numerische Mathematik</i>, 1, 269-271.",
              "Bellman, R. (1958). On a routing problem. <i>Quarterly of Applied Mathematics</i>, 16(1), 87-90.",
              "Held, M. and Karp, R. M. (1962). A dynamic programming approach to sequencing problems. <i>Journal of the "
              "SIAM</i>, 10(1), 196-210.",
              "Croes, G. A. (1958). A method for solving traveling-salesman problems. <i>Operations Research</i>, 6(6), 791-812.",
              "Kleinberg, J. and Tardos, É. (2005). <i>Algorithm Design</i>. Pearson."]:
        story.append(Paragraph(r, S["bullet"], bulletText="•"))


if __name__ == "__main__":
    build()
    save("Altitude_DAA_Report.pdf")
