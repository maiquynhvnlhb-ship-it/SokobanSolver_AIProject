# ==========================================
#  Sokoban Environment Definition
#  (State & Level Class)
#  Tác giả: Nhóm AI - Sokoban Project
# ==========================================

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Set, FrozenSet, Iterable, Optional

# ----------------- Kiểu dữ liệu cơ bản -----------------
Coord = Tuple[int, int]  # (row, col)


# ----------------- Mô tả trạng thái -----------------
@dataclass(frozen=True)
class State:
    """Trạng thái Sokoban gồm vị trí người chơi và vị trí các hộp."""
    player: Coord
    boxes: FrozenSet[Coord]


# ----------------- Mô tả bản đồ (Level) -----------------
@dataclass
class Level:
    """Mô tả một màn chơi Sokoban."""
    width: int
    height: int
    walls: Set[Coord]
    targets: Set[Coord]
    start_player: Coord
    start_boxes: Set[Coord]

    # Chi phí di chuyển và đẩy hộp
    MOVE_COST = 1
    PUSH_COST = 2

    # ---------- Đọc bản đồ từ chuỗi ----------
    @staticmethod
    def parse(text: str) -> "Level":
        """
        Chuyển đổi chuỗi mô tả bản đồ thành đối tượng Level.
        Ký hiệu:
          #: tường
          .: mục tiêu
          $: hộp
          *: hộp trên mục tiêu
          @: người chơi
          +: người chơi trên mục tiêu
        """
        lines = [list(row.rstrip("\n")) for row in text.splitlines() if row.strip() != ""]
        h = len(lines)
        w = max(len(r) for r in lines) if lines else 0

        walls, targets, boxes = set(), set(), set()
        player = (0, 0)

        for r, row in enumerate(lines):
            for c, ch in enumerate(row):
                if ch == '#':
                    walls.add((r, c))
                elif ch == '.':
                    targets.add((r, c))
                elif ch == '$':
                    boxes.add((r, c))
                elif ch == '*':  # hộp trên mục tiêu
                    boxes.add((r, c))
                    targets.add((r, c))
                elif ch == '@':
                    player = (r, c)
                elif ch == '+':  # người chơi trên mục tiêu
                    player = (r, c)
                    targets.add((r, c))

        return Level(
            width=w, height=h,
            walls=walls, targets=targets,
            start_player=player, start_boxes=boxes
        )

    # ---------- Trạng thái ban đầu ----------
    def initial_state(self) -> State:
        """Trả về trạng thái khởi đầu của màn chơi."""
        return State(self.start_player, frozenset(self.start_boxes))

    # ---------- Kiểm tra trạng thái đích ----------
    def is_goal(self, s: State) -> bool:
        """Trả True nếu tất cả hộp đã nằm đúng vị trí mục tiêu."""
        return set(s.boxes) == set(self.targets)

    # ---------- Kiểm tra ô trống ----------
    def is_free(self, pos: Coord, boxes: Iterable[Coord]) -> bool:
        """Ô pos có thể đi vào nếu không phải tường và không bị hộp chiếm."""
        return pos not in self.walls and pos not in boxes

    # ---------- Sinh các trạng thái kế cận ----------
    def neighbors(self, s: State) -> Iterable[Tuple[str, State]]:
        """
        Trả về các trạng thái kế cận có thể đạt được từ trạng thái s.
        Mỗi phần tử là (action, new_state), với action ∈ {'U','D','L','R'}.
        """
        DIRECTIONS = [(-1, 0, 'U'), (1, 0, 'D'), (0, -1, 'L'), (0, 1, 'R')]
        boxes = set(s.boxes)

        for dr, dc, a in DIRECTIONS:
            r, c = s.player
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)

            # Nếu hướng đi có hộp → thử đẩy
            if nxt in boxes:
                push_to = (nr + dr, nc + dc)
                # Không thể đẩy nếu đằng sau là tường hoặc hộp khác
                if push_to in boxes or push_to in self.walls:
                    continue
                if self.is_free(push_to, boxes):
                    new_boxes = set(boxes)
                    new_boxes.remove(nxt)
                    new_boxes.add(push_to)
                    yield a, State(nxt, frozenset(new_boxes))

            # Nếu ô trống → chỉ di chuyển
            else:
                if self.is_free(nxt, boxes):
                    yield a, State(nxt, s.boxes)

    # ---------- Hàm heuristic ----------
    def heuristic(self, s: State) -> int:
        """
        Hàm heuristic đơn giản (admissible):
        Tổng khoảng cách Manhattan nhỏ nhất từ mỗi hộp đến một mục tiêu.
        """
        def manhattan(a: Coord, b: Coord) -> int:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        total = 0
        for b in s.boxes:
            if self.targets:
                total += min(manhattan(b, t) for t in self.targets)
        return total

    # ---------- Hàm chi phí cạnh ----------
    def step_cost(self, s: State, a: str, ns: State) -> int:
        """
        Tính chi phí di chuyển từ s --a--> ns cho các thuật toán A*, UCS:
          • Nếu hộp bị đẩy (tập boxes thay đổi) → PUSH_COST
          • Nếu chỉ di chuyển người chơi → MOVE_COST
        """
        if ns == s:
            return 0  # không hợp lệ (không có thay đổi trạng thái)

        pushed = (ns.boxes != s.boxes)
        return self.PUSH_COST if pushed else self.MOVE_COST
