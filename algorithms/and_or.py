# ==========================================
#  Thuật toán AND–OR Search
#  Ứng dụng: Bài toán Sokoban (môi trường xác định)
# ==========================================

from __future__ import annotations
from typing import Dict, Tuple, List, Any, Optional, Iterable
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
    "group": "Tìm kiếm có điều kiện",
    "attributes":  "Gồm nút OR và nút AND ",
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
    """Giải Sokoban bằng thuật toán AND–OR Search."""
    start = level.initial_state()

    with timer_ms() as t:
        # --- Trường hợp đặc biệt ---
        if level.is_goal(start):
            steps = [start]
            stats = {
                "generated": 1, "expanded": 0,
                "depth": 0, "steps_count": 0,
                "runtime_ms": t(), "seen_count": 1
            }
            return steps, stats, start

        # --- Biến thống kê ---
        generated = 0
        expanded = 0

        # par dùng để tuyến tính hoá kế hoạch sau khi tìm thấy
        par: Dict[State, Tuple[State, str]] = {}

        # memo: ghi nhớ kết quả OR-node
        # None = thất bại; (action, subplan) = kế hoạch con thành công
        memo: Dict[State, Optional[Tuple[str, Any]]] = {}

        # ---------- OR-SEARCH ----------
        def or_search(s: State, path: Tuple[State, ...]) -> Optional[Tuple[str, Any]]:
            nonlocal expanded, generated, memo

            # --- Kiểm tra ghi nhớ ---
            if s in memo:
                return memo[s]

            expanded += 1

            # --- Đạt đích ---
            if level.is_goal(s):
                memo[s] = ("__EMPTY__", None)
                return memo[s]

            # --- Kiểm tra vòng lặp ---
            if s in path:
                memo[s] = None
                return None

            # --- Duyệt các hành động theo thứ tự cố định ---
            for a, s_next in level.neighbors(s):
                generated += 1
                # Trong Sokoban xác định → mỗi hành động có đúng 1 kết quả
                res = and_search([s_next], path + (s,))
                if res is not None:
                    memo[s] = (a, res)
                    return memo[s]

            # --- Không tìm thấy nhánh thành công ---
            memo[s] = None
            return None

        # ---------- AND-SEARCH ----------
        def and_search(states: Iterable[State], path: Tuple[State, ...]) -> Optional[Any]:
            """Mọi kết quả của hành động đều phải thành công (ở đây chỉ có 1 kết quả)."""
            (s_next,) = tuple(states)
            return or_search(s_next, path)

        # ---------- Gọi hàm gốc ----------
        plan = or_search(start, tuple())

        # --- Nếu thất bại ---
        if plan is None:
            steps = [start]
            stats = {
                "generated": max(generated, 1),
                "expanded": expanded,
                "depth": 0,
                "steps_count": 0,
                "runtime_ms": t()
            }
            return steps, stats, start

        # ---------- Tuyến tính hoá kế hoạch ----------
        steps_states: List[State] = [start]
        cur = start
        cur_plan = plan

        while isinstance(cur_plan, tuple) and cur_plan[0] != "__EMPTY__":
            action = cur_plan[0]
            found = False
            # tìm next state tương ứng action
            for a2, ns in level.neighbors(cur):
                if a2 == action:
                    par[ns] = (cur, a2)
                    steps_states.append(ns)
                    cur = ns
                    found = True
                    break
            if not found:
                break
            cur_plan = cur_plan[1]

        goal_state = steps_states[-1]
        stats = {
            "generated": max(generated, len(steps_states)),
            "expanded": expanded,
            "depth": len(steps_states) - 1,
            "steps_count": len(steps_states) - 1,
            "runtime_ms": t()
        }
        return steps_states, stats, goal_state
