# ==========================================
#  Thuật toán CSP thuần (Pure Backtracking)
#  Ứng dụng: Bài toán Sokoban
# ==========================================

from typing import Dict, List, Tuple, Any, Set
from collections import deque
from sokoban.level import Level, State, Coord
from time import perf_counter
from contextlib import contextmanager

# ---------- Bộ đếm thời gian thực thi ----------
@contextmanager
def timer_ms():
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000.0  # thời gian thực thi (ms)


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm ràng buộc",
    "attributes": "Bài toán ràng buộc CSP thuần"
}


# ---------- Hàm hỗ trợ ----------
def reconstruct(par: Dict[State, Tuple[State, str]], goal: State) -> List[Any]:
    """Truy vết ngược từ trạng thái đích về trạng thái khởi đầu."""
    states = []
    s = goal
    while s in par:
        ps, a = par[s]
        states.append(s)
        s = ps
    states.append(s)
    states.reverse()
    return states


def _bfs_path_to_boxes(level: Level, start: State, goal_boxes: Tuple[Coord, ...]) -> List[State] | None:
    """Tìm chuỗi bước từ start đến trạng thái có cùng bộ hộp (player ở đâu cũng được)."""
    q = deque([start])
    seen: Set[State] = {start}
    par: Dict[State, Tuple[State, str]] = {}

    while q:
        s = q.popleft()
        # Đạt đích khi vị trí hộp trùng nhau
        if set(s.boxes) == set(goal_boxes):
            return reconstruct(par, s)
        for a, ns in level.neighbors(s):
            if ns in seen:
                continue
            seen.add(ns)
            par[ns] = (s, a)
            q.append(ns)
    return None


# ---------- Thuật toán chính ----------
def solve(level: Level):
    """
    Backtracking
    """
    with timer_ms() as t:
        # --- Khởi tạo dữ liệu ---
        walls = set(level.walls)
        targets = set(level.targets)
        start = level.initial_state()
        num_boxes = len(start.boxes)

        # Các biến: người chơi + từng hộp
        variables = ["player"] + [f"box{i}" for i in range(num_boxes)]

        # Miền giá trị của mỗi biến: tất cả ô không phải tường
        free_cells: List[Coord] = [
            (r, c)
            for r in range(level.height)
            for c in range(level.width)
            if (r, c) not in walls
        ]
        domains: Dict[str, List[Coord]] = {v: free_cells[:] for v in variables}

        # ---------- Hàm kiểm tra ràng buộc ----------
        def _valid(assignment: Dict[str, Coord]) -> bool:
            """Kiểm tra tính hợp lệ của phép gán hiện tại."""
            vals = list(assignment.values())

            # Không được trùng vị trí
            if len(set(vals)) < len(vals):
                return False

            # Không được ở trong tường
            if any(v in walls for v in vals):
                return False

            # Các hộp không được nằm ở góc chết (trừ khi là mục tiêu)
            for k, (r, c) in assignment.items():
                if not k.startswith("box"):
                    continue
                up = (r - 1, c) in walls
                down = (r + 1, c) in walls
                left = (r, c - 1) in walls
                right = (r, c + 1) in walls
                if (up and left) or (up and right) or (down and left) or (down and right):
                    if (r, c) not in targets:
                        return False

            # Người chơi không được đứng chồng lên hộp
            if "player" in assignment:
                if assignment["player"] in [
                    assignment[v] for v in assignment if v.startswith("box")
                ]:
                    return False

            return True

        # ---------- Backtracking  ----------
        assignment: Dict[str, Coord] = {}
        generated = 0
        expanded = 0
        csp_solution: Dict[str, Coord] | None = None

        def _bt() -> bool:
            """Giải CSP bằng quay lui (Backtracking)."""
            nonlocal generated, expanded, csp_solution

            # Đã gán hết biến
            if len(assignment) == len(variables):
                expanded += 1
                boxes = tuple(assignment[f"box{i}"] for i in range(num_boxes))
                if set(boxes) == targets:
                    csp_solution = assignment.copy()
                    return True
                return False

            # Chọn biến kế tiếp (theo thứ tự)
            for var in variables:
                if var not in assignment:
                    break

            # Duyệt giá trị trong miền
            for val in domains[var]:
                assignment[var] = val
                generated += 1
                if _valid(assignment) and _bt():
                    return True
                del assignment[var]
            return False

        # ---------- Gọi giải CSP ----------
        found = _bt()

        # Nếu không tìm thấy nghiệm
        if not found or csp_solution is None:
            stats = {
                "generated": generated,
                "expanded": expanded,
                "depth": 0,
                "steps_count": 0,
                "runtime_ms": t()
            }
            return [start], stats, start

        # ---------- Có nghiệm CSP → dựng đường đi cụ thể bằng BFS ----------
        goal_boxes = tuple(csp_solution[f"box{i}"] for i in range(num_boxes))
        path = _bfs_path_to_boxes(level, start, goal_boxes)

        # Nếu nghiệm không khả thi (không reach được), fallback tới target bất kỳ
        if path is None:
            path = _bfs_path_to_boxes(level, start, tuple(targets))

        if path is None:
            # Trường hợp xấu: không tìm thấy đường đi, vẫn trả về trạng thái cuối để tránh crash
            player = csp_solution["player"]
            boxes = tuple(csp_solution[f"box{i}"] for i in range(num_boxes))
            goal_state = State(player, boxes)
            stats = {
                "generated": generated,
                "expanded": expanded,
                "depth": 0,
                "steps_count": 1,
                "runtime_ms": t()
            }
            return [start, goal_state], stats, goal_state

        # ---------- Kết quả thành công ----------
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": len(path) - 1,
            "steps_count": len(path) - 1,
            "runtime_ms": t()
        }
        return path, stats, path[-1]
