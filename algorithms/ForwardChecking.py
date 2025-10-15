# ==========================================
#  Thuật toán CSP với Forward Checking
#  Ứng dụng: Bài toán Sokoban
# ==========================================

from typing import Dict, List, Tuple, Any, Set
from collections import deque
from sokoban.level import Level, State, Coord
from time import perf_counter
from contextlib import contextmanager
import copy


# ---------- Bộ đếm thời gian thực thi ----------
@contextmanager
def timer_ms():
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000.0  # tính thời gian (ms)


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm ràng buộc",
    "attributes": "Bài toán ràng buộc, có Forward Checking để thu miền giá trị",
}


# ---------- Hàm hỗ trợ ----------
def _reconstruct(par: Dict[State, Tuple[State, str]], goal: State) -> List[State]:
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


def _bfs_path_to_boxes(level: Level, start: State, goal_boxes: Tuple[Coord, ...]) -> List[State] | None:
    """Tìm chuỗi bước từ trạng thái start đến trạng thái có vị trí hộp = goal_boxes."""
    q = deque([start])
    seen: Set[State] = {start}
    par: Dict[State, Tuple[State, str]] = {}

    while q:
        s = q.popleft()
        if set(s.boxes) == set(goal_boxes):
            return _reconstruct(par, s)
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
    CSP Backtracking + Forward Checking cho Sokoban:
      • Mỗi biến (variable) là một vị trí cần gán (người chơi hoặc hộp).
      • FC: Khi gán giá trị, cắt tỉa miền của các biến còn lại, loại bỏ giá trị mâu thuẫn.
      • Nếu có nghiệm CSP → dùng BFS dựng đường đi cụ thể.
    """
    with timer_ms() as t:
        walls = set(level.walls)
        targets = set(level.targets)
        start = level.initial_state()
        num_boxes = len(start.boxes)

        # --- Khởi tạo biến và miền giá trị ---
        variables = ["player"] + [f"box{i}" for i in range(num_boxes)]
        free_cells = [
            (r, c)
            for r in range(level.height)
            for c in range(level.width)
            if (r, c) not in walls
        ]
        domains = {v: free_cells[:] for v in variables}

        # ---------- Ràng buộc nhất quán ----------
        def is_consistent(var: str, val: Coord, assignment: Dict[str, Coord]) -> bool:
            """Kiểm tra giá trị val có hợp lệ với các biến đã gán không."""
            # Không trùng vị trí
            if val in assignment.values():
                return False
            # Không được vào tường
            if val in walls:
                return False
            # Nếu là hộp → không nằm ở góc chết (dead corner)
            if var.startswith("box"):
                r, c = val
                up = (r - 1, c) in walls
                down = (r + 1, c) in walls
                left = (r, c - 1) in walls
                right = (r, c + 1) in walls
                # Nếu là góc và không phải mục tiêu → loại bỏ
                if (up and left) or (up and right) or (down and left) or (down and right):
                    if (r, c) not in targets:
                        return False
            return True

        # ---------- Forward Checking ----------
        def forward_check(
            var: str,
            val: Coord,
            domains: Dict[str, List[Coord]],
            assignment: Dict[str, Coord]
        ) -> Dict[str, List[Coord]] | None:
            """Sau khi gán var=val, cắt tỉa miền giá trị của các biến chưa gán."""
            new_domains = copy.deepcopy(domains)
            for other in variables:
                if other not in assignment and other != var:
                    new_domains[other] = [
                        v for v in new_domains[other]
                        if v != val and is_consistent(other, v, {**assignment, var: val})
                    ]
                    if not new_domains[other]:  # nếu miền trống → dead end
                        return None
            return new_domains

        # ---------- Backtracking + Forward Checking ----------
        assignment: Dict[str, Coord] = {}
        generated = 0
        expanded = 0
        solution: Dict[str, Coord] | None = None

        def backtrack(domains_now: Dict[str, List[Coord]]) -> bool:
            """Đệ quy tìm nghiệm CSP với heuristic MRV (Minimum Remaining Values)."""
            nonlocal generated, expanded, solution

            # --- Nếu đã gán hết biến ---
            if len(assignment) == len(variables):
                boxes = tuple(assignment[f"box{i}"] for i in range(num_boxes))
                if set(boxes) == targets:
                    solution = assignment.copy()
                    return True
                return False

            # --- Chọn biến có miền nhỏ nhất (MRV) ---
            unassigned = [v for v in variables if v not in assignment]
            var = min(unassigned, key=lambda v: len(domains_now[v]))

            # --- Duyệt từng giá trị trong miền ---
            for val in domains_now[var]:
                if not is_consistent(var, val, assignment):
                    continue
                assignment[var] = val
                generated += 1

                new_domains = forward_check(var, val, domains_now, assignment)
                if new_domains is not None:
                    expanded += 1
                    if backtrack(new_domains):
                        return True

                del assignment[var]  # quay lui
            return False

        # ---------- Gọi giải CSP ----------
        found = backtrack(domains)

        # ---------- Xử lý kết quả ----------
        runtime = t()
        if not found or solution is None:
            stats = {
                "generated": generated,
                "expanded": expanded,
                "depth": 0,
                "steps_count": 0,
                "runtime_ms": runtime
            }
            return [start], stats, start

        # Có nghiệm CSP → tìm đường đi cụ thể bằng BFS
        goal_boxes = tuple(solution[f"box{i}"] for i in range(num_boxes))
        path = _bfs_path_to_boxes(level, start, goal_boxes)

        if path is None:
            player = solution["player"]
            boxes = tuple(solution[f"box{i}"] for i in range(num_boxes))
            goal_state = State(player, boxes)
            return [start, goal_state], {
                "generated": generated,
                "expanded": expanded,
                "depth": 1,
                "steps_count": 1,
                "runtime_ms": runtime
            }, goal_state

        # --- Kết quả thành công ---
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": len(path) - 1,
            "steps_count": len(path) - 1,
            "runtime_ms": runtime
        }
        return path, stats, path[-1]
