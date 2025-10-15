# ==========================================
#  Thuật toán Beam Search (Tìm kiếm chùm tia)
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
    yield lambda: (perf_counter() - start) * 1000.0  # thời gian (ms)


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm có thông tin ",
    "attributes": "Giữ lại K trạng thái tốt nhất(theo heuristic)",
}


# ---------- Tham số điều chỉnh ----------
BEAM_WIDTH = 100  # có thể thử 10 / 25 / 50 / 100 tùy độ khó bản đồ


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
    """Giải bài toán Sokoban bằng thuật toán Beam Search."""
    start = level.initial_state()

    with timer_ms() as t:
        # --- Khởi tạo ---
        beam: List[State] = [start]                   # tập trạng thái hiện tại (1 lớp)
        par: Dict[State, Tuple[State, str]] = {}      # lưu cha để truy vết
        seen = {start}                                # tập trạng thái đã thăm
        generated = 1
        expanded = 0
        counter = itertools.count()                   # tie-break khi heuristic bằng nhau

        # --- Trường hợp đặc biệt: start là goal ---
        if level.is_goal(start):
            steps = [start]
            stats = {"generated": 1, "expanded": 0, "depth": 0,
                     "steps_count": 0, "runtime_ms": t()}
            return steps, stats, start

        # ---------- Vòng lặp chính ----------
        while beam:
            expanded += len(beam)
            candidates: List[Tuple[int, int, State, Tuple[State, str]]] = []
            found_goal: State | None = None

            # --- Mở rộng từng trạng thái trong beam hiện tại ---
            for s in beam:
                for a, ns in level.neighbors(s):
                    if ns in seen:
                        continue
                    seen.add(ns)
                    par[ns] = (s, a)
                    generated += 1

                    # Gặp goal → dừng sớm
                    if level.is_goal(ns):
                        found_goal = ns
                        break

                    # Tính giá trị heuristic
                    h = level.heuristic(ns)
                    # Lưu vào danh sách ứng viên (để chọn top-K)
                    candidates.append((h, next(counter), ns, (s, a)))
                if found_goal is not None:
                    break

            # --- Nếu tìm thấy goal ---
            if found_goal is not None:
                steps = reconstruct(par, found_goal)
                stats = {
                    "generated": generated,
                    "expanded": expanded,
                    "depth": len(steps) - 1,
                    "steps_count": len(steps) - 1,
                    "runtime_ms": t()
                }
                return steps, stats, found_goal

            # --- Nếu không còn ứng viên ---
            if not candidates:
                break

            # --- Chọn K trạng thái tốt nhất theo heuristic ---
            topk = heapq.nsmallest(min(BEAM_WIDTH, len(candidates)), candidates)

            # Lớp tiếp theo chỉ gồm các trạng thái được chọn
            beam = [ns for (_, __, ns, ___) in topk]

        # ---------- Không tìm thấy lời giải ----------
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": 0,
            "steps_count": 0,
            "runtime_ms": t()
        }
        return [start], stats, start
