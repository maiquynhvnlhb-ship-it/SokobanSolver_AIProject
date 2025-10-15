import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Any, Optional

# ===== Matplotlib embedding =====
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from algorithms import get_names, get
from sokoban.level import Level, State

CELL = 70            # Kích thước mỗi ô (pixel)
ANIM_STEP_MS = 300   # Tổng thời gian cho mỗi bước (ms)
ANIM_FRAMES = 8      # Số frame animation trong 1 bước (~37.5ms/frame)


# ============================================================
# Hàm tải ảnh
# ============================================================
def try_load_image(path: str, size: Tuple[int, int]) -> Optional[tk.PhotoImage]:
    """Tải ảnh và resize theo 'size' về PhotoImage."""
    try:
        from PIL import Image, ImageTk
        img = Image.open(path).convert("RGBA").resize(size, Image.NEAREST)
        return ImageTk.PhotoImage(img)
    except Exception:
        try:
            return tk.PhotoImage(file=path)
        except Exception:
            return None

# ============================================================
# Lớp SokobanCanvas: Canvas hiển thị bản đồ và animation
# ============================================================
class SokobanCanvas(tk.Canvas):
    def __init__(self, master, cell_size=CELL, *args, **kwargs):
        super().__init__(master, width=cell_size*20, height=cell_size*15,
                         highlightthickness=0, *args, **kwargs)
        self.cell = cell_size
        self.level: Optional[Level] = None
        self.state: Optional[State] = None

        # Ảnh sprite
        self.img_space = self.img_wall = self.img_box = None
        self.img_target = self.img_player = None

        # Animation
        self._anim_after = None
        self._anim_idx = 0
        self._anim_frames = ANIM_FRAMES
        self._anim_from: Optional[State] = None
        self._anim_to: Optional[State] = None

    # ----- Nạp assets -----
    def load_assets(self, assets_dir: str):
        size = (self.cell, self.cell)
        self.img_space  = try_load_image(f"{assets_dir}/space.png", size)
        self.img_wall   = try_load_image(f"{assets_dir}/wall.png", size)
        self.img_box    = try_load_image(f"{assets_dir}/box.png", size)
        self.img_target = try_load_image(f"{assets_dir}/point.png", size)
        self.img_player = try_load_image(f"{assets_dir}/player.png", size)

    # ----- Thiết lập level -----
    def set_level(self, level: Level):
        self.level = level
        self.config(width=level.width*self.cell, height=level.height*self.cell)
        self.draw_all(level.initial_state())

    # ----- Vẽ toàn bộ bản đồ -----
    def draw_all(self, state: Optional[State]):
        self.delete("all")
        if not self.level:
            return

        cs = self.cell
        # Vẽ nền
        for r in range(self.level.height):
            for c in range(self.level.width):
                x, y = c*cs, r*cs
                if self.img_space:
                    self.create_image(x, y, anchor="nw", image=self.img_space)
                else:
                    color = "#CAE9FF" if (r+c)%2==0 else "#1B4965"
                    self.create_rectangle(x, y, x+cs, y+cs, fill=color, width=0)

        # Vẽ tường
        for (r, c) in self.level.walls:
            x, y = c*cs, r*cs
            if self.img_wall:
                self.create_image(x, y, anchor="nw", image=self.img_wall)
            else:
                self.create_rectangle(x, y, x+cs, y+cs, fill="#2B2D42", width=0)

        # Vẽ ô đích
        for (r, c) in self.level.targets:
            x, y = c*cs, r*cs
            if self.img_target:
                self.create_image(x, y, anchor="nw", image=self.img_target)
            else:
                rad = cs*0.25
                self.create_oval(x+cs/2-rad, y+cs/2-rad,
                                 x+cs/2+rad, y+cs/2+rad,
                                 fill="#FFB703", outline="")

        # Vẽ thùng và người chơi
        if state:
            for (r, c) in state.boxes:
                x, y = c*cs, r*cs
                if self.img_box:
                    self.create_image(x, y, anchor="nw", image=self.img_box)
                else:
                    sz, ox = cs*0.8, cs*0.1
                    self.create_rectangle(x+ox, y+ox, x+ox+sz, y+ox+sz,
                                          fill="#E76F51", outline="#00000055", width=2)

            pr, pc = state.player
            x, y = pc*cs, pr*cs
            if self.img_player:
                self.create_image(x, y, anchor="nw", image=self.img_player)
            else:
                self.create_text(x+cs/2, y+cs/2, text="🙂",
                                 font=("Segoe UI Black", int(cs*0.4)), fill="#264653")

    # ============================================================
    # Animation từng bước chuyển (player / box)
    # ============================================================
    def animate_step(self, s_from: State, s_to: State):
        """Animation cho bước di chuyển từ s_from → s_to."""
        self._anim_from, self._anim_to = s_from, s_to
        self._anim_idx = 0
        self._anim_tick()

    def _anim_tick(self):
        if not self._anim_from or not self._anim_to:
            return

        f = self._anim_idx
        total = max(1, self._anim_frames)
        t = f / total  # giá trị nội suy 0..1

        a, b = self._anim_from, self._anim_to
        pr0, pc0 = a.player
        pr1, pc1 = b.player
        xr = (pc0 + (pc1 - pc0)*t) * self.cell
        yr = (pr0 + (pr1 - pr0)*t) * self.cell

        # Xác định thùng bị đẩy
        delta = (pr1 - pr0, pc1 - pc0)
        box_a, box_b = set(a.boxes), set(b.boxes)
        pushed_from = pushed_to = None
        if (pr0+delta[0], pc0+delta[1]) in box_a:
            start_box = (pr0+delta[0], pc0+delta[1])
            end_box = (start_box[0]+delta[0], start_box[1]+delta[1])
            if start_box in box_a and end_box in box_b and start_box not in box_b:
                pushed_from, pushed_to = start_box, end_box

        # Vẽ lại tất cả
        self.delete("all")
        if self.level:
            cs = self.cell
            # Nền + tường + đích
            for r in range(self.level.height):
                for c in range(self.level.width):
                    x, y = c*cs, r*cs
                    if self.img_space:
                        self.create_image(x, y, anchor="nw", image=self.img_space)
                    else:
                        color = "#CAE9FF" if (r+c)%2==0 else "#1B4965"
                        self.create_rectangle(x, y, x+cs, y+cs, fill=color, width=0)
            for (r, c) in self.level.walls:
                x, y = c*cs, r*cs
                if self.img_wall:
                    self.create_image(x, y, anchor="nw", image=self.img_wall)
                else:
                    self.create_rectangle(x, y, x+cs, y+cs, fill="#2B2D42", width=0)
            for (r, c) in self.level.targets:
                x, y = c*cs, r*cs
                if self.img_target:
                    self.create_image(x, y, anchor="nw", image=self.img_target)
                else:
                    rad = cs*0.25
                    self.create_oval(x+cs/2-rad, y+cs/2-rad,
                                     x+cs/2+rad, y+cs/2+rad,
                                     fill="#FFB703", outline="")

            # Thùng tĩnh (trừ thùng đang di chuyển)
            for (r, c) in box_b:
                if pushed_to and (r, c) == pushed_to:
                    continue
                x, y = c*cs, r*cs
                if self.img_box:
                    self.create_image(x, y, anchor="nw", image=self.img_box)
                else:
                    sz, ox = cs*0.8, cs*0.1
                    self.create_rectangle(x+ox, y+ox, x+ox+sz, y+ox+sz,
                                          fill="#E76F51", outline="#00000055", width=2)

            # Thùng đang di chuyển
            if pushed_from and pushed_to:
                br0, bc0 = pushed_from
                br1, bc1 = pushed_to
                xb = (bc0 + (bc1 - bc0)*t) * cs
                yb = (br0 + (br1 - br0)*t) * cs
                if self.img_box:
                    self.create_image(xb, yb, anchor="nw", image=self.img_box)
                else:
                    sz, ox = cs*0.8, cs*0.1
                    self.create_rectangle(xb+ox, yb+ox, xb+ox+sz, yb+ox+sz,
                                          fill="#E76F51", outline="#00000055", width=2)

            # Người chơi
            if self.img_player:
                self.create_image(xr, yr, anchor="nw", image=self.img_player)
            else:
                self.create_text(xr+cs/2, yr+cs/2, text="🙂",
                                 font=("Segoe UI Black", int(cs*0.4)), fill="#264653")

        self._anim_idx += 1
        if self._anim_idx <= total:
            self._anim_after = self.after(int(ANIM_STEP_MS/ANIM_FRAMES), self._anim_tick)
        else:
            self.draw_all(self._anim_to)
            self._anim_from = self._anim_to = self._anim_after = None


# ============================================================
# Lớp chính App — giao diện, logic và thống kê
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧱 Sokoban — Runtime & Steps Visualization")

        try: self.state("zoomed")
        except Exception: self.geometry("1200x820")

        self.configure(bg="#F6F9FC")

        # Dữ liệu logic & runtime
        self.level: Optional[Level] = None
        self.steps: List[Any] = []
        self.stats = {}
        self.solution = None
        self.anim_idx = 0
        self.anim_running = False
        self.anim_after = None
        self.runtime_data = {}
        self.generated_data = {}

        # Xây dựng giao diện
        self._build_ui()
        self._load_default_level()
        self._render_all()

    # ============================================================
    # ------------------------- UI -------------------------------
    # ============================================================
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#F6F9FC")
        style.configure("TLabel", background="#F6F9FC", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 12, "bold"), foreground="#1D3557")
        style.configure("Accent.TButton",
                        background="#457B9D", foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=6)
        style.map("Accent.TButton",
                  background=[("active", "#2A9D8F"), ("!active", "#457B9D")])

        # ----- Khung bên trái -----
        left = ttk.Frame(self, width=360)
        left.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        left.grid_propagate(False)
        left.grid_columnconfigure(1, weight=1)

        ttk.Label(left, text="Thuật toán", style="Header.TLabel").grid(
            row=0, column=0, padx=8, pady=8, sticky="w"
        )

        self.combo_algo = ttk.Combobox(left, state="readonly", font=("Segoe UI", 10))
        self.combo_algo.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self._refresh_algos()
        self.combo_algo.bind("<<ComboboxSelected>>", self._on_algo_changed)

        # ----- Chọn level -----
        ttk.Label(left, text="Màn chơi (level)", style="Header.TLabel").grid(
            row=1, column=0, padx=8, pady=8, sticky="w"
        )
        import pathlib

        levels_dir = pathlib.Path(__file__).parent / "levels"
        level_files = [p.stem for p in levels_dir.glob("*.txt")]
        self.combo_level = ttk.Combobox(left, state="readonly", values=level_files, font=("Segoe UI", 10))
        self.combo_level.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        self.combo_level.bind("<<ComboboxSelected>>", self._on_level_changed)
        if level_files:
            self.combo_level.current(0)

        # ----- Nhóm nút điều khiển -----
        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")

        def make_btn(parent, text, command, color, row, col):
            btn = tk.Button(
                parent, text=text, command=command,
                font=("Segoe UI", 10, "bold"), bg=color, fg="white",
                activebackground="#264653", activeforeground="white",
                relief="flat", bd=0, padx=10, pady=8, cursor="hand2"
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        for r in range(2):
            btn_frame.grid_rowconfigure(r, weight=1)
        for c in range(2):
            btn_frame.grid_columnconfigure(c, weight=1)

        make_btn(btn_frame, "▶ Chạy", self.on_run, "#2ECC71", 0, 0)
        make_btn(btn_frame, "⏸ Dừng", self.on_pause, "#F4A261", 0, 1)
        make_btn(btn_frame, "🔁 Bắt đầu lại", self.on_restart, "#A8A8A8", 1, 0)
        make_btn(btn_frame, "💡 Hiện lời giải", self.on_show_solution, "#9B5DE5", 1, 1)
        make_btn(btn_frame, "⏭ Bước kế", self.on_step, "#118AB2", 2, 0)

        # ----- Thông tin thuật toán -----
        ttk.Label(left, text="Thông tin thuật toán", style="Header.TLabel").grid(
            row=4, column=0, columnspan=2, padx=8, pady=(16, 4), sticky="w"
        )
        self.lbl_group = ttk.Label(left, text="Nhóm: -")
        self.lbl_attr = ttk.Label(left, text="Thuộc tính: -")
        self.lbl_group.grid(row=5, column=0, columnspan=2, padx=8, pady=2, sticky="w")
        self.lbl_attr.grid(row=6, column=0, columnspan=2, padx=8, pady=2, sticky="w")

        # ----- Thống kê -----
        ttk.Label(left, text="Thống kê", style="Header.TLabel").grid(
            row=7, column=0, columnspan=2, padx=8, pady=(16, 4), sticky="w"
        )
        self.lbl_generated = ttk.Label(left, text="Số nút sinh ra: 0")
        self.lbl_expanded = ttk.Label(left, text="Số nút mở rộng: 0")
        self.lbl_depth = ttk.Label(left, text="Độ sâu lời giải: -")
        self.lbl_steps = ttk.Label(left, text="Số bước đi: 0")
        self.lbl_runtime = ttk.Label(left, text="Thời gian thực thi: 0 ms")

        for i, w in enumerate([self.lbl_generated, self.lbl_expanded,
                               self.lbl_depth, self.lbl_steps, self.lbl_runtime],
                              start=8):
            w.grid(row=i, column=0, columnspan=2, padx=8, pady=2, sticky="w")

        # ----- Khung chính -----
        main = ttk.Frame(self)
        main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)  # Biểu đồ
        main.grid_columnconfigure(1, weight=3)  # Canvas chính
        main.grid_columnconfigure(2, weight=1)  # Canvas tĩnh
        main.grid_rowconfigure(1, weight=1)

        ttk.Label(main, text="📊 Biểu đồ thời gian / số state sinh ra", style="Header.TLabel").grid(row=0, column=0)
        ttk.Label(main, text="🧱 Sokoban", style="Header.TLabel").grid(row=0, column=1)
        ttk.Label(main, text="🏁 Bản đồ (tĩnh)", style="Header.TLabel").grid(row=0, column=2)

        # ----- Biểu đồ -----
        self.chart_frame = ttk.Frame(main, borderwidth=2, relief="ridge")
        self.chart_frame.config(width=420, height=500)
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.chart_frame.grid_propagate(True)

        # ----- Bảng hiển thị bản đồ -----
        self.board_exec = SokobanCanvas(main, cell_size=CELL)
        self.board_goal = SokobanCanvas(main, cell_size=30)
        self.board_exec.grid(row=1, column=1, padx=(20, 8), pady=8)
        self.board_goal.grid(row=1, column=2, padx=(60, 8), pady=10)

        # ----- Danh sách bước -----
        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 8))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(1, weight=1)

        ttk.Label(bottom, text="📜 Steps (danh sách trạng thái)", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        text_frame = ttk.Frame(bottom)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.steps_list = tk.Text(
            text_frame, height=13, width=200, wrap="none", bg="#FFFFFF",
            font=("Consolas", 10), relief="solid", borderwidth=1
        )
        self.steps_list.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        scroll_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.steps_list.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.steps_list.config(yscrollcommand=scroll_y.set)

    # ============================================================
    # ------------------------- DATA -----------------------------
    # ============================================================
    def _refresh_algos(self):
        """Cập nhật danh sách thuật toán trong combobox."""
        try:
            names = sorted(get_names())
            self.combo_algo["values"] = names
            if names:
                self.combo_algo.current(0)
        except Exception:
            pass

    def _on_algo_changed(self, *_):
        """Khi người dùng chọn thuật toán mới."""
        try:
            mod = get(self.combo_algo.get())
            meta = getattr(mod, "META", None)
            group = (meta or {}).get("group", "-")
            attrs = (meta or {}).get("attributes", "-")
            self.lbl_group.config(text=f"Nhóm thuật toán: {group}")
            self.lbl_attr.config(text=f"Thuộc tính: {attrs}")
        except Exception:
            self.lbl_group.config(text="Nhóm thuật toán: -")
            self.lbl_attr.config(text="Thuộc tính: -")

    def _on_level_changed(self, *_):
        """Khi đổi level trong combobox: tải level và làm mới giao diện."""
        import pathlib

        # Ngừng animation nếu đang chạy
        self.on_pause()
        self.anim_idx = 0

        level_name = self.combo_level.get().strip()
        if not level_name:
            messagebox.showwarning("Thiếu level", "Hãy chọn level trong danh sách.")
            return

        p = pathlib.Path(__file__).parent / "levels" / f"{level_name}.txt"
        if not p.exists():
            messagebox.showerror("Không tìm thấy file", f"Không có file: {p}")
            return

        txt = p.read_text(encoding="utf-8")
        self.level = Level.parse(txt)

        # Nạp assets (an toàn nếu gọi nhiều lần)
        assets = pathlib.Path(__file__).parent / "Assets"
        self.board_goal.load_assets(str(assets))
        self.board_exec.load_assets(str(assets))

        # Cập nhật canvas
        self.board_goal.set_level(self.level)
        self.board_exec.set_level(self.level)
        self.board_exec.draw_all(self.level.initial_state())

        # Reset kết quả
        self.steps = []
        self.stats = {}
        self.solution = None
        self._update_metrics_display()

        self.steps_list.config(state="normal")
        self.steps_list.delete("1.0", "end")
        self.steps_list.config(state="disabled")

        # Reset biểu đồ và dữ liệu thống kê
        for child in self.chart_frame.winfo_children():
            child.destroy()

        import matplotlib.pyplot as plt
        for fig_attr in ("fig1", "fig2", "fig3"):
            if hasattr(self, fig_attr) and getattr(self, fig_attr) is not None:
                try:
                    plt.close(getattr(self, fig_attr))
                except Exception:
                    pass
                setattr(self, fig_attr, None)

        if hasattr(self, "runtime_data"): self.runtime_data.clear()
        if hasattr(self, "generated_data"): self.generated_data.clear()
        if hasattr(self, "expanded_data"): self.expanded_data.clear()
        if hasattr(self, "steps_data"): self.steps_data.clear()

    def _load_default_level(self):
        """Tải level mặc định khi khởi động ứng dụng."""
        import pathlib
        level_name = self.combo_level.get().strip()
        if not level_name:
            messagebox.showwarning("Thiếu level", "Chưa chọn level nào.")
            return

        p = pathlib.Path(__file__).parent / "levels" / f"{level_name}.txt"
        if not p.exists():
            messagebox.showerror("Không tìm thấy file", f"Không có file: {p}")
            return

        txt = p.read_text(encoding="utf-8")
        self.level = Level.parse(txt)

        assets = pathlib.Path(__file__).parent / "Assets"
        self.board_goal.load_assets(str(assets))
        self.board_exec.load_assets(str(assets))

    def _render_all(self):
        """Hiển thị lại toàn bộ bản đồ và thông tin."""
        self._on_algo_changed()
        if self.level:
            self.board_goal.set_level(self.level)
            self.board_exec.set_level(self.level)
            self.board_exec.draw_all(self.level.initial_state())
        self._update_metrics_display()

    def _update_metrics_display(self):
        """Cập nhật các chỉ số thống kê hiển thị."""
        g = self.stats.get("generated", 0)
        e = self.stats.get("expanded", 0)
        d = self.stats.get("depth", 0) or "-"
        s = self.stats.get("steps_count", 0)
        t = round(float(self.stats.get("runtime_ms", 0.0)), 3)

        self.lbl_generated.config(text=f"Số nút sinh ra: {g}")
        self.lbl_expanded.config(text=f"Số nút mở rộng: {e}")
        self.lbl_depth.config(text=f"Độ sâu lời giải: {d}")
        self.lbl_steps.config(text=f"Số bước đi: {s}")
        self.lbl_runtime.config(text=f"Thời gian thực thi: {t} ms")

    def _populate_steps_text(self):
        """Điền danh sách trạng thái vào vùng văn bản."""
        self.steps_list.config(state="normal")
        self.steps_list.delete("1.0", "end")

        for i, st in enumerate(self.steps, 1):
            if hasattr(st, "player"):
                player, boxes = st.player, st.boxes
            elif isinstance(st, tuple) and len(st) == 2:
                player, boxes = st
            else:
                self.steps_list.insert("end", f"Bước {i}: (unknown state)\n")
                continue

            msg = f"player={player}, boxes={sorted(list(boxes))}"
            self.steps_list.insert("end", f"Bước {i}: {msg}\n")

        self.steps_list.config(state="disabled")

    # ============================================================
    # ------------------------ CONTROLS ---------------------------
    # ============================================================

    def on_confirm(self):
        """Xác nhận chạy thuật toán được chọn và cập nhật thống kê."""
        algo_name = self.combo_algo.get()
        if not algo_name:
            messagebox.showwarning("Thiếu thuật toán", "Hãy chọn thuật toán trước.")
            return
        if not self.level:
            messagebox.showwarning("Thiếu level", "Chưa tải level.")
            return

        self._on_algo_changed()
        mod = get(algo_name)
        self.steps, self.stats, self.solution = mod.solve(self.level)
        self.anim_idx = 0

        if self.level:
            self.board_exec.draw_all(self.level.initial_state())

        runtime = round(float(self.stats.get("runtime_ms", 0.000)), 3)
        generated = int(self.stats.get("generated", 0))

        self.runtime_data[algo_name] = runtime
        self.generated_data[algo_name] = generated

    def on_run(self):
        """Khi nhấn 'Chạy': tự động tải level đang chọn rồi thực thi thuật toán."""
        import pathlib

        # 🧩 Tải level từ combobox
        level_name = self.combo_level.get().strip()
        if not level_name:
            messagebox.showwarning("Thiếu level", "Hãy chọn level trong danh sách.")
            return

        p = pathlib.Path(__file__).parent / "levels" / f"{level_name}.txt"
        if not p.exists():
            messagebox.showerror("Không tìm thấy file", f"Không có file: {p}")
            return

        txt = p.read_text(encoding="utf-8")
        self.level = Level.parse(txt)

        # Nạp assets (nếu chưa có)
        assets = pathlib.Path(__file__).parent / "Assets"
        self.board_goal.load_assets(str(assets))
        self.board_exec.load_assets(str(assets))

        # Hiển thị lại bản đồ
        self.board_goal.set_level(self.level)
        self.board_exec.set_level(self.level)
        self.board_exec.draw_all(self.level.initial_state())

        # Lấy thuật toán
        algo_name = self.combo_algo.get()
        if not algo_name:
            messagebox.showwarning("Thiếu thuật toán", "Hãy chọn thuật toán trước.")
            return

        # 🧮 Thực thi thuật toán
        self._on_algo_changed()
        mod = get(algo_name)
        self.steps, self.stats, self.solution = mod.solve(self.level)

        # Cập nhật thống kê
        self.anim_idx = 0
        runtime = round(float(self.stats.get("runtime_ms", 0.000)), 3)
        generated = int(self.stats.get("generated", 0))
        self.runtime_data[algo_name] = runtime
        self.generated_data[algo_name] = generated

        self._update_metrics_display()
        self._populate_steps_text()
        self._update_charts()

        # ▶ Bắt đầu animation
        if self.anim_running:
            return
        self.anim_running = True
        self._tick()

    def on_pause(self):
        """Tạm dừng animation."""
        self.anim_running = False
        if self.anim_after:
            self.after_cancel(self.anim_after)
            self.anim_after = None

    def on_restart(self):
        """Khởi động lại trạng thái ban đầu."""
        self.on_pause()
        self.anim_idx = 0
        if self.level:
            self.board_exec.draw_all(self.level.initial_state())

    def _normalize_state(self, st):
        """Chuyển đổi dữ liệu về dạng State chuẩn."""
        if hasattr(st, "player"):
            return st
        ps, boxes = st
        from sokoban.level import State
        return State(ps, frozenset(boxes))

    def on_step(self):
        """Chạy từng bước (step-by-step), không tự động phát."""
        self.on_pause()  # Dừng nếu đang chạy tự động

        if not self.level:
            messagebox.showwarning("Thiếu level", "Chưa tải level.")
            return

        # Nếu chưa có dữ liệu tìm kiếm thì giải trước
        if not self.steps:
            algo_name = self.combo_algo.get()
            if not algo_name:
                messagebox.showwarning("Thiếu thuật toán", "Hãy chọn thuật toán trước.")
                return
            self._on_algo_changed()
            mod = get(algo_name)
            self.steps, self.stats, self.solution = mod.solve(self.level)
            self.anim_idx = 0
            self._update_metrics_display()
            self._populate_steps_text()
            self._update_charts()
            if self.level:
                self.board_exec.draw_all(self.level.initial_state())

        # Không có dữ liệu step
        if len(self.steps) < 2:
            messagebox.showinfo("Thông báo", "Không có bước chuyển nào để chạy.")
            return

        # Đã tới trạng thái cuối
        if self.anim_idx >= len(self.steps) - 1:
            messagebox.showinfo("Hoàn tất", "Đã tới trạng thái cuối cùng.")
            return

        # Tránh chồng animation
        if getattr(self.board_exec, "_anim_after", None) is not None:
            return

        # Animate đúng 1 bước
        s_from = self._normalize_state(self.steps[self.anim_idx])
        s_to = self._normalize_state(self.steps[self.anim_idx + 1])
        self.board_exec.animate_step(s_from, s_to)
        self.anim_idx += 1

    def on_show_solution(self):
        """Hiển thị trạng thái lời giải cuối cùng."""
        if not self.solution:
            if not self.steps:
                messagebox.showwarning("Chưa có dữ liệu", "Hãy chạy 'Xác nhận' trước.")
                return
            self.solution = self.steps[-1]

        self.on_pause()
        if self.level:
            if hasattr(self.solution, "player"):
                self.board_exec.draw_all(self.solution)
            else:
                ps, boxes = self.solution
                from sokoban.level import State
                self.board_exec.draw_all(State(ps, frozenset(boxes)))

    def _tick(self):
        """Animation tự động theo từng bước."""
        if not self.anim_running:
            return
        if self.anim_idx >= len(self.steps) - 1:
            self.anim_running = False
            return

        s_from = self.steps[self.anim_idx]
        s_to = self.steps[self.anim_idx + 1]

        # Chuẩn hoá state
        if not hasattr(s_from, "player"):
            ps, boxes = s_from
            from sokoban.level import State
            s_from = State(ps, frozenset(boxes))
        if not hasattr(s_to, "player"):
            ps, boxes = s_to
            from sokoban.level import State
            s_to = State(ps, frozenset(boxes))

        self.board_exec.animate_step(s_from, s_to)
        self.anim_idx += 1
        self.anim_after = self.after(ANIM_STEP_MS, self._tick)

    # ============================================================
    # ------------------------- CHARTS ----------------------------
    # ============================================================

    def _update_charts(self):
        """Vẽ biểu đồ thời gian thực thi và số nút sinh ra."""
        for child in self.chart_frame.winfo_children():
            child.destroy()

        if not self.runtime_data:
            return

        # --- Biểu đồ 1: Thời gian thực thi ---
        fig1, ax1 = plt.subplots(figsize=(5, 3), dpi=100)
        sorted_runtime = dict(sorted(self.runtime_data.items(), key=lambda x: x[1]))
        names_rt = list(sorted_runtime.keys())
        times = [sorted_runtime[k] for k in names_rt]

        bars1 = ax1.bar(names_rt, times, color="#F77F00", edgecolor="#6A040F")
        ax1.set_ylabel("Thời gian (ms)")
        ax1.set_title("Thời gian thực thi")
        ax1.grid(axis="y", linestyle="--", alpha=0.6)

        # Giới hạn trục Y an toàn
        if times:
            ymax = max(times)
            ax1.set_ylim(0, ymax * 1.2)
            pad = ymax * 0.001 + 0.5
        else:
            ax1.set_ylim(0, 1.0)
            pad = 2

        # Hiển thị giá trị trên cột
        for rect, val in zip(bars1, times):
            x = rect.get_x() + rect.get_width() / 2
            y = rect.get_height()
            ax1.text(x, y + pad * 0.02, f"{val:.2f}", ha="center", va="bottom", fontsize=9)

        ax1.set_xticklabels(names_rt, rotation=45)
        fig1.tight_layout()

        chart1 = FigureCanvasTkAgg(fig1, master=self.chart_frame)
        chart1.draw()
        chart1.get_tk_widget().pack(fill="x", expand=True, pady=(5, 10))

        # --- Biểu đồ 2: Số nút sinh ra ---
        fig2, ax2 = plt.subplots(figsize=(5, 3), dpi=100)
        sorted_gen = dict(sorted(self.generated_data.items(), key=lambda x: x[1]))
        names_gn = list(sorted_gen.keys())
        gens = [int(sorted_gen[k]) for k in names_gn]

        bars = ax2.bar(range(len(names_gn)), gens)
        ax2.set_ylabel("Số trạng thái")
        ax2.set_title("Số trạng thái sinh ra")
        ax2.grid(axis="y", linestyle="--", alpha=0.6)
        ax2.set_ylim(0, (max(gens) * 1.2) if gens else 1.0)

        for x_pos, rect, val in zip(range(len(names_gn)), bars, gens):
            y = rect.get_height()
            ax2.text(x_pos, y, f"{int(val)}", ha="center", va="bottom", fontsize=9)

        ax2.set_xticks(range(len(names_gn)))
        ax2.set_xticklabels(names_gn, rotation=45, ha="right")

        fig2.tight_layout()
        chart2 = FigureCanvasTkAgg(fig2, master=self.chart_frame)
        chart2.draw()
        chart2.get_tk_widget().pack(fill="x", expand=True, pady=(5, 5))

    # ============================================================
    # ---------------------- LEVEL LOADER -------------------------
    # ============================================================

    def on_open_level(self):
        """Mở file level theo tên được chọn trong combobox."""
        import pathlib

        level_name = self.combo_level.get().strip()
        if not level_name:
            messagebox.showwarning("Thiếu level", "Hãy chọn level trong danh sách.")
            return

        p = pathlib.Path(__file__).parent / "levels" / f"{self.combo_level.get()}.txt"
        if not p.exists():
            messagebox.showerror("Lỗi", f"Không tìm thấy file: {p}")
            return

        txt = p.read_text(encoding="utf-8")
        self.level = Level.parse(txt)

        # Nạp lại assets
        assets = pathlib.Path(__file__).parent / "Assets"
        self.board_goal.load_assets(str(assets))
        self.board_exec.load_assets(str(assets))

        # Cập nhật bản đồ
        self.board_goal.set_level(self.level)
        self.board_exec.set_level(self.level)
        self.board_exec.draw_all(self.level.initial_state())

        # Reset dữ liệu thống kê
        self.steps = []
        self.stats = {}
        self.solution = None
        self.anim_idx = 0
        self._update_metrics_display()
        self.steps_list.config(state="normal")
        self.steps_list.delete("1.0", "end")
        self.steps_list.config(state="disabled")

if __name__ == "__main__":
    App().mainloop()
