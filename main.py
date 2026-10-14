"""Pedido de namoro interativo: o "Não" foge do mouse e o "Sim" só cresce."""

import math
import random
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont

WINDOW_TITLE = "Acelitas1"
QUESTION = "Quer namorar comigo?"
ANSWER = "Eu te amo, meu amor!\nLanchinho mais tarde?"

BG = "#ffc8dd"
TEXT = "#590d22"
BUTTON = "#ffb3c1"
BUTTON_ACTIVE = "#ff8fab"
HEART_COLORS = ("#ffafcc", "#ff8fab", "#fb6f92", "#ffb3c6", "#c9184a")
PREFERRED_FONTS = ("Montserrat", "Poppins", "Ubuntu", "DejaVu Sans", "Helvetica")

NO_LABELS = ("Não", "Tem certeza?", "Pensa bem...", "Sério?", "Última chance!", "Nem vem", "Erro 404")
HINTS = (
    "",
    "Ops, escorregou...",
    "Esse botão é tímido",
    "Ele não quer ser clicado",
    "O outro botão parece ótimo, hein?",
    "Desiste, vai ♥",
)

FRAME_MS = 16
DODGE_RADIUS = 45  # distância (px) do cursor que faz o "Não" fugir
DODGE_COOLDOWN = 0.35  # segundos entre fugas contadas para a "escalada"
HEART = "♥"


@dataclass
class Heart:
    item: int
    x: float
    y: float
    vx: float
    vy: float
    gravity: float
    phase: float


def pick_font(root: tk.Tk) -> str:
    available = set(tkfont.families(root))
    return next((f for f in PREFERRED_FONTS if f in available), "Helvetica")


def boxes_overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class ProposalApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.family = pick_font(root)
        self.hearts: list[Heart] = []
        self.dodges = 0
        self.last_dodge = 0.0
        self.no_target: tuple[float, float] | None = None
        self.accepted = False
        self.big_heart: int | None = None

        root.title(WINDOW_TITLE)
        root.geometry("600x600")
        root.minsize(420, 420)
        root.configure(bg=BG)

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.title = self.canvas.create_text(
            0, 0, text=QUESTION, fill=TEXT, justify="center", font=(self.family, 26, "bold")
        )
        self.hint = self.canvas.create_text(0, 0, fill=TEXT, font=(self.family, 12, "italic"))

        self.yes_btn = self._make_button("Sim", self.on_yes, size=16)
        self.no_btn = self._make_button("Não", self.on_no, size=12)
        self.no_btn.configure(takefocus=0)  # nada de escapar pelo teclado
        self.yes_win = self.canvas.create_window(0, 0, window=self.yes_btn)
        self.no_win = self.canvas.create_window(0, 0, window=self.no_btn)

        self.canvas.bind("<Configure>", self._layout)
        # bind_all + coordenadas do ponteiro: funciona mesmo com o mouse sobre outros widgets
        root.bind_all("<Motion>", self._on_motion)
        root.bind("<Escape>", lambda _: root.destroy())

        self._tick()

    # ---------- construção / layout ----------

    def _make_button(self, text, command, size):
        return tk.Button(
            self.canvas,
            text=text,
            command=command,
            font=(self.family, size, "bold"),
            bg=BUTTON,
            fg=TEXT,
            activebackground=BUTTON_ACTIVE,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
            highlightthickness=0,
        )

    def _size(self) -> tuple[int, int]:
        return self.canvas.winfo_width(), self.canvas.winfo_height()

    def _layout(self, _event=None):
        w, h = self._size()
        if self.accepted:
            self.canvas.coords(self.title, w / 2, h * 0.32)
            self.canvas.coords(self.big_heart, w / 2, h * 0.62)
            return

        self.canvas.coords(self.title, w / 2, h * 0.3)
        self.canvas.coords(self.hint, w / 2, h * 0.3 + 40)
        if self.dodges == 0:
            self.canvas.coords(self.yes_win, w / 2 - 80, h * 0.55)
            self.canvas.coords(self.no_win, w / 2 + 80, h * 0.55)
        else:
            self.canvas.coords(self.yes_win, w / 2, h * 0.55)
            x, y = self.canvas.coords(self.no_win)
            self.canvas.coords(self.no_win, *self._clamp(x, y))

    def _clamp(self, x, y):
        w, h = self._size()
        bw, bh = self.no_btn.winfo_reqwidth() / 2 + 10, self.no_btn.winfo_reqheight() / 2 + 10
        return min(max(x, bw), w - bw), min(max(y, bh), h - bh)

    # ---------- botão fujão ----------

    def _pointer(self) -> tuple[int, int]:
        return (
            self.root.winfo_pointerx() - self.canvas.winfo_rootx(),
            self.root.winfo_pointery() - self.canvas.winfo_rooty(),
        )

    def _on_motion(self, _event):
        if self.accepted:
            return
        px, py = self._pointer()
        x, y = self.canvas.coords(self.no_win)
        dx = max(abs(px - x) - self.no_btn.winfo_width() / 2, 0)
        dy = max(abs(py - y) - self.no_btn.winfo_height() / 2, 0)
        if math.hypot(dx, dy) < DODGE_RADIUS:
            self._dodge(px, py)

    def _dodge(self, px, py):
        now = time.monotonic()
        if now - self.last_dodge > DODGE_COOLDOWN:
            self.last_dodge = now
            self._escalate()
        self.no_target = self._escape_point(px, py)

    def _escalate(self):
        self.dodges += 1
        self.no_btn.configure(text=NO_LABELS[self.dodges % len(NO_LABELS)])
        self.yes_btn.configure(font=(self.family, min(16 + self.dodges * 3, 44), "bold"))
        self.canvas.itemconfigure(self.hint, text=HINTS[min(self.dodges, len(HINTS) - 1)])
        self._layout()

    def _escape_point(self, px, py):
        w, h = self._size()
        bw, bh = self.no_btn.winfo_reqwidth() / 2, self.no_btn.winfo_reqheight() / 2
        avoid = [self.canvas.bbox(self.yes_win), self.canvas.bbox(self.title)]
        best, best_dist = self.canvas.coords(self.no_win), -1.0
        for _ in range(60):
            x = random.uniform(bw + 10, w - bw - 10)
            y = random.uniform(bh + 10, h - bh - 10)
            box = (x - bw - 15, y - bh - 15, x + bw + 15, y + bh + 15)
            if any(b and boxes_overlap(box, b) for b in avoid):
                continue
            dist = math.hypot(x - px, y - py)
            if dist > 200:
                return x, y
            if dist > best_dist:
                best, best_dist = (x, y), dist
        return best

    def _animate_no(self):
        if self.no_target is None or self.accepted:
            return
        x, y = self.canvas.coords(self.no_win)
        tx, ty = self.no_target
        if math.hypot(tx - x, ty - y) < 1:
            self.no_target = None
            return
        self.canvas.coords(self.no_win, x + (tx - x) * 0.3, y + (ty - y) * 0.3)

    def on_no(self):
        # só acontece se a pessoa for MUITO rápida
        self.canvas.itemconfigure(self.hint, text="Esse botão está com defeito, tenta o outro")
        self._dodge(*self._pointer())

    # ---------- final feliz ----------

    def on_yes(self):
        self.accepted = True
        for win, btn in ((self.yes_win, self.yes_btn), (self.no_win, self.no_btn)):
            self.canvas.delete(win)
            btn.destroy()
        self.canvas.delete(self.hint)
        self.canvas.itemconfigure(self.title, text=ANSWER, font=(self.family, 28, "bold"))
        self.big_heart = self.canvas.create_text(0, 0, text=HEART, fill="#c9184a")
        self._layout()

        w, h = self._size()
        for _ in range(80):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 10)
            self._spawn_heart(
                w / 2, h * 0.62, math.cos(angle) * speed, math.sin(angle) * speed - 4, gravity=0.18
            )

    # ---------- corações ----------

    def _spawn_heart(self, x, y, vx, vy, gravity):
        item = self.canvas.create_text(
            x,
            y,
            text=HEART,
            fill=random.choice(HEART_COLORS),
            font=(self.family, random.randint(10, 28)),
        )
        self.canvas.tag_lower(item)
        self.hearts.append(Heart(item, x, y, vx, vy, gravity, random.uniform(0, 2 * math.pi)))

    def _update_hearts(self):
        w, h = self._size()
        if random.random() < (0.25 if self.accepted else 0.05):
            self._spawn_heart(random.uniform(0, w), h + 20, 0, random.uniform(-2.5, -1), gravity=0)

        alive = []
        for heart in self.hearts:
            heart.vy += heart.gravity
            heart.phase += 0.08
            heart.x += heart.vx + math.sin(heart.phase) * 0.6
            heart.y += heart.vy
            if -40 < heart.y < h + 40 and -40 < heart.x < w + 40:
                self.canvas.coords(heart.item, heart.x, heart.y)
                alive.append(heart)
            else:
                self.canvas.delete(heart.item)
        self.hearts = alive

    def _pulse(self):
        if self.big_heart is not None:
            size = int(80 + 10 * math.sin(time.monotonic() * 5))
            self.canvas.itemconfigure(self.big_heart, font=(self.family, size))

    def _tick(self):
        self._update_hearts()
        self._animate_no()
        self._pulse()
        self.root.after(FRAME_MS, self._tick)


def main():
    root = tk.Tk()
    ProposalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
