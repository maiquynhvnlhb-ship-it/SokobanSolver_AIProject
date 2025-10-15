# ==========================================
#  Thuật toán A* (A-star Search)
#  Ứng dụng: Bài toán Sokoban
# ==========================================

import heapq
import itertools
from typing import Dict, Tuple, List, Any
from sokoban.level import Level, State
from time import perf_counter
from contextlib import contextmanager


# ---------- Bộ đếm thời gian thực thi ----------
@contextmanager
def timer_ms():
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000.0  # tính thời gian (ms)


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm có thông tin",
    "attributes": "f(n)=g(n)+h(n); mở rộng nút có f nhỏ nhất",
}


# ---------- Hàm truy vết đường đi ----------
def reconstruct(par: Dict[State, Tuple[State, str]], goal: State) -> List[Any]:
    """Truy ngược đường đi từ trạng thái đích về trạng thái ban đầu."""
    path: List[State] = []
    s = goal
    while s in par:
        ps, _ = par[s]
        path.append(s)
        s = ps
    path.append(s)
    path.reverse()
    return path


# ---------- Thuật toán chính ----------
def solve(level: Level):
    """Giải bài toán Sokoban bằng thuật toán A*."""
    start = level.initial_state()

    with timer_ms() as t:
        # --- Trường hợp đặc biệt: đã ở đích ---
        if level.is_goal(start):
            steps = [start]
            stats = {
                "generated": 1,
                "expanded": 0,
                "depth": 0,
                "steps_count": 0,
                "runtime_ms": t()
            }
            return steps, stats, start

        # ---------- Khởi tạo ----------
        counter = itertools.count()                    # tie-break ổn định
        h0 = level.heuristic(start)                    # h(n)
        open_heap: List[Tuple[int, int, int, State]] = []
        heapq.heappush(open_heap, (h0, 0, next(counter), start))

        g: Dict[State, int] = {start: 0}               # chi phí nhỏ nhất từ start → s
        par: Dict[State, Tuple[State, str]] = {}       # lưu cha để truy vết
        best_f: Dict[State, int] = {start: h0}         # lưu f tốt nhất đã biết

        generated = 1
        expanded = 0

        # ---------- Vòng lặp chính ----------
        while open_heap:
            f, neg_g, _, s = heapq.heappop(open_heap)

            # Bỏ qua entry lỗi thời (đã có f tốt hơn)
            if best_f.get(s, float("inf")) < f:
                continue

            expanded += 1

            # --- Kiểm tra trạng thái đích ---
            if level.is_goal(s):
                steps = reconstruct(par, s)
                stats = {
                    "generated": generated,
                    "expanded": expanded,
                    "depth": len(steps) - 1,
                    "steps_count": len(steps) - 1,
                    "runtime_ms": t()
                }
                return steps, stats, s

            # --- Mở rộng các trạng thái kế cận ---
            for a, ns in level.neighbors(s):
                c = level.step_cost(s, a, ns)           # chi phí cạnh
                tentative_g = g[s] + c

                if ns not in g or tentative_g < g[ns]:
                    g[ns] = tentative_g
                    par[ns] = (s, a)
                    hn = level.heuristic(ns)
                    fn = tentative_g + hn
                    best_f[ns] = fn

                    # tie-break: ưu tiên nút sâu hơn khi f bằng nhau
                    heapq.heappush(open_heap, (fn, -tentative_g, next(counter), ns))
                    generated += 1

        # ---------- Không tìm thấy lời giải ----------
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": 0,
            "steps_count": 0,
            "runtime_ms": t()
        }
        return [start], stats, start
