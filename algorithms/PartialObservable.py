# ==========================================
#  Thuật toán Exploration-Based BFS
#  (Môi trường quan sát một phần - Partial Observable)
#  Ứng dụng: Bài toán Sokoban
# ==========================================

from contextlib import contextmanager
from typing import Dict, List, Tuple, Set
from collections import deque
from sokoban.level import Level, State, Coord
from time import perf_counter


# ---------- Bộ đếm thời gian thực thi ----------
@contextmanager
def timer_ms():
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000.0  # tính thời gian (ms)


# ---------- Thông tin mô tả thuật toán ----------
META = {
    "group": "Tìm kiếm trong môi trường không quan sát đầy đủ (Exploration / Partial Observable)",
    "attributes":"Quan sát cục bộ (tầm nhìn giới hạn)" ,
}


# ---------- Tham số cấu hình ----------
VISION_RADIUS = 2  # bán kính tầm nhìn của người chơi


# ---------- Hàm quan sát ----------
def _observe(level: Level, pos: Coord, boxes: Set[Coord], radius: int = VISION_RADIUS) -> Dict[Coord, str]:
    """Quan sát vùng trong bán kính nhất định quanh người chơi (partial observable)."""
    visible = {}
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            r, c = pos[0] + dr, pos[1] + dc
            if 0 <= r < level.height and 0 <= c < level.width:
                if (r, c) in level.walls:
                    visible[(r, c)] = "wall"
                elif (r, c) in level.targets:
                    visible[(r, c)] = "target"
                elif (r, c) in boxes:
                    visible[(r, c)] = "box"
                else:
                    visible[(r, c)] = "floor"
    return visible


# ---------- Xác định biên khám phá (frontier) ----------
def _find_frontiers(known_map: Dict[Coord, str]) -> List[Coord]:
    """Tìm các ô nằm ở rìa vùng đã biết – điểm có thể mở rộng khám phá."""
    out = []
    for (r, c), t in known_map.items():
        if t != "wall":
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (r + dr, c + dc) not in known_map:
                    out.append((r, c))
                    break
    return out


def _choose_best_frontier(frontiers: List[Coord], player: Coord) -> Coord | None:
    """Chọn frontier gần người chơi nhất (Manhattan distance)."""
    return min(frontiers, key=lambda f: abs(f[0] - player[0]) + abs(f[1] - player[1])) if frontiers else None


# ---------- BFS di chuyển trong vùng đã biết ----------
def _bfs_path_in_known(known_map: Dict[Coord, str], start: Coord, goal: Coord) -> List[Coord] | None:
    """Tìm đường đi ngắn nhất trong vùng bản đồ đã quan sát được."""
    q = deque([(start, [start])])
    seen = {start}
    while q:
        pos, path = q.popleft()
        if pos == goal:
            return path
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            np = (pos[0] + dr, pos[1] + dc)
            if known_map.get(np) in ("floor", "target") and np not in seen:
                seen.add(np)
                q.append((np, path + [np]))
    return None


# ---------- BFS đẩy hộp cục bộ (local solving) ----------
def _local_push(level: Level, start_state: State) -> List[State] | None:
    """Khi đã quan sát được hộp và mục tiêu, thử giải nhanh trên vùng hiện tại."""
    q = deque([start_state])
    seen = {start_state}
    par: Dict[State, Tuple[State, str]] = {}

    while q:
        s = q.popleft()
        if level.is_goal(s):
            # tái tạo đường đi khi đạt goal
            path: List[State] = []
            while s in par:
                ps, _ = par[s]
                path.append(s)
                s = ps
            path.append(s)
            path.reverse()
            return path

        for a, ns in level.neighbors(s):
            if ns not in seen:
                seen.add(ns)
                par[ns] = (s, a)
                q.append(ns)
    return None


# ---------- Thuật toán chính ----------
def solve(level: Level):
    """Thuật toán BFS khám phá từng phần trong Sokoban."""
    start = level.initial_state()
    player = start.player
    boxes: Set[Coord] = set(start.boxes)
    known_map = _observe(level, player, boxes)

    steps: List[State] = [start]
    generated = 1
    expanded = 0

    with timer_ms() as t:
        while True:
            expanded += 1

            # --- Cập nhật tầm nhìn ---
            known_map.update(_observe(level, player, boxes))

            # --- Nếu đã nhìn thấy cả hộp và mục tiêu ---
            seen_targets = any(v == "target" for v in known_map.values())
            seen_boxes = any(v == "box" for v in known_map.values())
            if seen_boxes and seen_targets:
                current = State(player, tuple(boxes))
                local_path = _local_push(level, current)
                if local_path:
                    steps.extend(local_path[1:])  # nối thêm vào hành trình tổng
                    generated += len(local_path) - 1
                    break
                # nếu chưa giải được → tiếp tục khám phá

            # --- Tìm và di chuyển tới frontier gần nhất ---
            frontiers = _find_frontiers(known_map)
            if not frontiers:
                break

            goal = _choose_best_frontier(frontiers, player)
            path = _bfs_path_in_known(known_map, player, goal)
            if not path or len(path) < 2:
                break

            # --- Di chuyển một bước ---
            player = path[1]
            generated += 1
            steps.append(State(player, tuple(boxes)))

        # --- Ghi thống kê ---
        stats = {
            "generated": generated,
            "expanded": expanded,
            "depth": len(steps) - 1,
            "steps_count": len(steps) - 1,
            "runtime_ms": t()
        }

    return steps, stats, steps[-1]
