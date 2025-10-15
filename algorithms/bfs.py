# ==========================================
#  Thuật toán Tìm kiếm Theo Chiều Rộng (BFS)
#  Ứng dụng: Bài toán Sokoban
# ==========================================

from collections import deque
from typing import Dict, Tuple, List, Any
from sokoban.level import Level, State
from time import perf_counter
from contextlib import contextmanager


# ---------- Bộ đếm thời gian thực thi ----------
@contextmanager
def timer_ms():
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000.0  # thời gian tính bằng ms


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm không thông tin",
    "attributes": "Hàng đợi (FIFO),duyệt theo từng lớp độ sâu",
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
    """Giải bài toán Sokoban bằng thuật toán BFS (duyệt theo lớp)."""
    start = level.initial_state()

    with timer_ms() as t:
        # Khởi tạo
        q = deque([start])                     # hàng đợi FIFO
        par: Dict[State, Tuple[State, str]] = {}  # lưu cha để truy vết
        seen = {start}                         # tập trạng thái đã thăm
        generated = 1                          # số nút sinh ra
        expanded = 0                           # số nút mở rộng

        # ---------- Vòng lặp chính ----------
        while q:
            s = q.popleft()                    # lấy phần tử đầu hàng đợi
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

            # --- Sinh và mở rộng các trạng thái kế cận ---
            for a, ns in level.neighbors(s):
                if ns not in seen:
                    seen.add(ns)
                    par[ns] = (s, a)
                    q.append(ns)
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
