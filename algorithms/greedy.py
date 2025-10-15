# ==========================================
#  Thuật toán Greedy Best-First Search
#  Ứng dụng: Bài toán Sokoban
#  (Bản có log minh họa chạy tay + hiển thị hàng đợi chi tiết)
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
    "attributes": "Dựa vào heuristic (ước lượng h)",
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
    """Giải bài toán Sokoban bằng Greedy Best-First Search (in log + hàng đợi chi tiết)."""
    start = level.initial_state()

    with timer_ms() as t:
        counter = itertools.count()
        frontier = [(level.heuristic(start), next(counter), start)]
        heapq.heapify(frontier)

        par: Dict[State, Tuple[State, str]] = {}
        seen = {start}
        generated = 1
        expanded = 0

        # In tiêu đề bảng
        print("\n========== BẢNG MÔ PHỎNG THUẬT TOÁN GREEDY BEST-FIRST SEARCH ==========")
        print(f"{'Bước':<6} | {'Trạng thái đang xét (player, boxes)':<40} | {'h(n)':<6} | {'Kế cận sinh ra (h)':<30} | {'Hàng đợi sau bước này':<70}")
        print("-" * 170)

        step_id = 0

        # ---------- Vòng lặp chính ----------
        while frontier:
            h, _, s = heapq.heappop(frontier)
            expanded += 1
            step_id += 1

            # In thông tin node đang mở rộng
            box_str = sorted(list(s.boxes))
            print(f"{step_id:<6} | {str((s.player, box_str)):<40} | {h:<6.1f} | ", end="")

            # --- Kiểm tra trạng thái đích ---
            if level.is_goal(s):
                print("→ ĐẠT MỤC TIÊU ✅")
                steps = reconstruct(par, s)
                stats = {
                    "generated": generated,
                    "expanded": expanded,
                    "depth": len(steps) - 1,
                    "steps_count": len(steps) - 1,
                    "runtime_ms": t()
                }
                print("\nHoàn tất tìm kiếm!")
                print(f"Tổng trạng thái sinh: {generated}, Mở rộng: {expanded}, Độ sâu: {len(steps)-1}")
                return steps, stats, s

            # --- Mở rộng trạng thái kế cận ---
            neighbors_list = []
            for a, ns in level.neighbors(s):
                if ns not in seen:
                    seen.add(ns)
                    par[ns] = (s, a)
                    hn = level.heuristic(ns)
                    heapq.heappush(frontier, (hn, next(counter), ns))
                    generated += 1
                    neighbors_list.append(f"{a}:{hn:.1f}")

            # In danh sách kế cận sinh ra
            if neighbors_list:
                print(", ".join(neighbors_list), end=" | ")
            else:
                print("(Không có kế cận hợp lệ)", end=" | ")

            # --- In hàng đợi hiện tại (chi tiết) ---
            if frontier:
                queue_sorted = sorted(frontier, key=lambda x: x[0])
                queue_snapshot = []
                for qh, _, qs in queue_sorted[:6]:  # in tối đa 6 phần tử để dễ nhìn
                    queue_snapshot.append(
                        f"[h={qh:.1f} | player={qs.player} | boxes={sorted(list(qs.boxes))}]"
                    )
                print(" ".join(queue_snapshot))
            else:
                print("(Trống)")

        # ---------- Không tìm thấy lời giải ----------
        print("\n⚠️  Không tìm thấy lời giải.")
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": 0,
            "steps_count": 0,
            "runtime_ms": t()
        }
        return [start], stats, start
