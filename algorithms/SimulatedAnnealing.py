# ==========================================
#  Thuật toán Simulated Annealing (SA)
#  Ứng dụng: Bài toán Sokoban
# ==========================================

import math
import random
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
    "group": "Tìm kiếm cục bộ",
    "attributes": "Xác suất chấp nhận trạng thái xấu tạm thời ",
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


# ---------- Láng giềng chưa thăm ----------
def _unvisited_neighbors(level: Level, s: State, seen: set[State]) -> List[Tuple[str, State]]:
    """Trả về danh sách láng giềng của s chưa có trong tập seen."""
    return [(a, ns) for a, ns in level.neighbors(s) if ns not in seen]


# ---------- Chọn pivot (điểm khởi động lại) ----------
def _pick_pivot(level: Level, seen: Iterable[State], seen_set: set[State]) -> Optional[State]:
    """
    Chọn một trạng thái trong seen vẫn còn láng giềng chưa thăm.
    Ưu tiên random sample để giảm chi phí duyệt.
    """
    seen_list = list(seen)
    if not seen_list:
        return None

    # Lấy mẫu ngẫu nhiên
    sample = seen_list if len(seen_list) <= 2000 else random.sample(seen_list, 2000)
    for s in sample:
        if _unvisited_neighbors(level, s, seen_set):
            return s

    # Nếu không có, quét toàn bộ
    for s in seen_list:
        if _unvisited_neighbors(level, s, seen_set):
            return s
    return None


# ---------- Thuật toán chính ----------
def solve(level: Level,
          base_T: float = 120.0,
          alpha: float = 0.95,
          T_min: float = 1.0,
          max_iters: int = 1_000_000,
          k: int = 12):
    """
    Simulated Annealing với chiến lược:
      - Duyệt theo kiểu DFS nhưng có nhớ (seen toàn cục).
      - Nhiệt T giảm dần theo công thức T = T * α.
      - Khi bị kẹt hoặc T quá thấp:
          + “Reheat” nhiệt về base_T.
          + Chọn pivot trong tập seen còn láng giềng chưa thăm để tiếp tục (internal rescue).
      - Lặp lại đến khi đạt goal hoặc không còn pivot khả thi.
    """
    start = level.initial_state()

    with timer_ms() as t:
        # --- Trường hợp đặc biệt: đã ở đích ---
        if level.is_goal(start):
            return [start], {"generated": 1, "expanded": 0,
                             "depth": 0, "steps_count": 0, "runtime_ms": t()}, start

        # --- Khởi tạo ---
        seen: set[State] = {start}
        par: Dict[State, Tuple[State, str]] = {}
        current = start
        h_cur = level.heuristic(current)
        T = base_T

        total_gen = total_exp = 0

        # ---------- Vòng lặp chính ----------
        while True:
            # Một pha “làm nguội” (annealing phase)
            for _ in range(max_iters):
                if T < T_min:
                    break
                total_exp += 1

                # Tìm láng giềng chưa thăm
                nbrs = _unvisited_neighbors(level, current, seen)
                if not nbrs:
                    # Bị kẹt – chuyển sang rescue phase
                    break

                # Giới hạn số láng giềng được xét
                if len(nbrs) > k:
                    nbrs = random.sample(nbrs, k)

                # Chọn ngẫu nhiên 1 láng giềng
                a, nxt = random.choice(nbrs)
                seen.add(nxt)
                par[nxt] = (current, a)
                total_gen += 1

                h_next = level.heuristic(nxt)

                # --- Kiểm tra đích ---
                if level.is_goal(nxt):
                    steps = reconstruct(par, nxt)
                    stats = {
                        "generated": total_gen,
                        "expanded": total_exp,
                        "depth": len(steps) - 1,
                        "steps_count": len(steps) - 1,
                        "runtime_ms": t()
                    }
                    return steps, stats, nxt

                # --- Quy tắc chấp nhận SA ---
                delta = h_next - h_cur
                if delta < 0 or random.random() < math.exp(-delta / max(T, 1e-12)):
                    current = nxt
                    h_cur = h_next

                # Làm nguội
                T *= alpha

            # ---------- Rescue phase ----------
            pivot = _pick_pivot(level, seen, seen)
            if pivot is None:
                # Không còn điểm khả thi nào để tiếp tục
                steps = [start]
                stats = {"generated": total_gen, "expanded": total_exp,
                         "depth": 0, "steps_count": 0, "runtime_ms": t()}
                return steps, stats, start

            # “Hồi nhiệt” và bắt đầu pha mới
            current = pivot
            h_cur = level.heuristic(current)
            T = base_T
