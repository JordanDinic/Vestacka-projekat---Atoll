"""GUI sloj igre Atoll (Pygame).

Ovaj modul namerno ne sadrzi pravila igre.
Njegova odgovornost je:
- vizuelizacija stanja iz GameState,
- prihvat korisnickih inputa (klikovi, zatvaranje prozora),
- poziv AI-a kada je AI na potezu.
"""

import math
from typing import Optional

import pygame

from ai import AIConfig, choose_best_move
from geometry import NEIGHBORS, to_pixel
from state import Cell

# Dimenzije prozora.
WIDTH, HEIGHT = 1000, 900

# Poluprecnik kruzica koji predstavlja jedno polje.
RADIUS = 15

# Mapa boja po tipu celije.
COLORS = {
    Cell.EMPTY: (230, 230, 230),
    Cell.X: (0, 170, 0),
    Cell.O: (200, 0, 0),
    Cell.BLOCKED: (40, 40, 40),
}


# Ova klasa implementira graficki interfejs i glavni game-loop igre.
class AtolGUI:
    """Pygame omotac oko modela stanja i AI-a.

    Atributi:
    - state: referenca na GameState (jedini izvor logike stanja).
    - ai_player: koji igrac je pod kontrolom AI-a (ili None).
    - ai_cfg: parametri pretrage AI-a.
    - screen/clock/font...: GUI infrastruktura.
    """

    # Ova metoda inicijalizuje Pygame, cuva stanje i konfiguraciju AI-a.
    def __init__(
        self,
        state,
        ai_player: Optional[Cell] = None,
        ai_depth: int = 2,
        ai_move_limit: int = 30,
    ):
        """Podigni GUI i pripremi sve sto je potrebno za crtanje."""
        pygame.init()

        # state je "live" referenca; GUI citanjem i pozivima menja isto stanje.
        self.state = state

        # Ako je None -> covek-covek mod.
        self.ai_player = ai_player

        # Konfiguracija AI pretrage.
        self.ai_cfg = AIConfig(depth=ai_depth, move_limit=ai_move_limit)

        # Kreiranje prozora i osnovnih pygame objekata.
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Atoll - Phase III")
        self.clock = pygame.time.Clock()

        # Fontovi za glavni status i pomocne oznake.
        self.font = pygame.font.SysFont(None, 32)
        self.small_font = pygame.font.SysFont(None, 22)

        # Centar table na ekranu.
        self.center = (WIDTH // 2, HEIGHT // 2)

        # Fiksni layout labela se racuna jednom na pocetku partije.
        self._axis_letter_layout = []
        self._axis_number_layout = []
        self._build_axis_label_layout()

    # Ova metoda proverava da li je sada red na AI igraca.
    def _is_ai_turn(self) -> bool:
        """Vrati True ako AI treba sada da odigra potez."""
        return (
            self.ai_player is not None
            and not getattr(self.state, "game_over", False)
            and self.state.current_player == self.ai_player
        )

    # Ova metoda, ako je red na AI, trazi najbolji potez i odmah ga odigra.
    def _maybe_ai_move(self) -> None:
        """Odigravanje AI poteza u jednom "tick" ciklusu petlje."""
        if not self._is_ai_turn():
            return

        # mv: koordinata poteza koji je AI izracunao.
        mv = choose_best_move(self.state, self.ai_player, self.ai_cfg)
        if mv is not None:
            self.state.place_stone(mv)

    # Ova metoda crta oznake ostrva (id + vlasnik), korisno za pracenje logike.
    def _draw_island_labels(self) -> None:
        """Nacrtaj ID ostrva i vlasnika na centroidu ostrva."""
        if not hasattr(self.state, "islands"):
            return

        for isl in self.state.islands:
            # pts: sve celije ostrva pretvorene u piksel koordinate.
            pts = [to_pixel(x, y, *self.center) for (x, y) in isl.cells]

            # mx/my: centroid u piksel prostoru.
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)

            owner = "X" if isl.owner == Cell.X else "O"
            label = f"{isl.id}{owner}"

            surf = self.small_font.render(label, True, (255, 255, 255))
            rect = surf.get_rect(center=(int(mx), int(my)))
            self.screen.blit(surf, rect)

    # Ova metoda pre-racuna fiksan raspored spoljasnjih oznaka na startu partije.
    def _build_axis_label_layout(self) -> None:
        """Izracunaj pozicije labela jednom, da se oznake ne pomeraju tokom igre."""
        self._axis_letter_layout = []
        self._axis_number_layout = []

        # Mapiranje baziramo na pocetnim slobodnim poljima.
        initial_empty = [(x, y) for (x, y), c in self.state.nodes.items() if c == Cell.EMPTY]
        if not initial_empty:
            return

        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        top_bottom_gap = RADIUS + 34
        side_gap = RADIUS + 44

        # Slova: vertikalne kolone (x) sa slobodnim poljima.
        x_values = sorted({x for (x, _y) in initial_empty})
        for idx, x in enumerate(x_values):
            col_cells = [(cx, cy) for (cx, cy) in initial_empty if cx == x]
            if not col_cells:
                continue

            top = min(col_cells, key=lambda p: to_pixel(p[0], p[1], *self.center)[1])
            bottom = max(col_cells, key=lambda p: to_pixel(p[0], p[1], *self.center)[1])
            tpx, tpy = to_pixel(top[0], top[1], *self.center)
            bpx, bpy = to_pixel(bottom[0], bottom[1], *self.center)

            label = letters[idx] if idx < len(letters) else f"A{idx - len(letters) + 1}"
            top_pos = (tpx, tpy - top_bottom_gap)
            bottom_pos = (bpx, bpy + top_bottom_gap)
            self._axis_letter_layout.append((label, top_pos, bottom_pos))

        # Brojevi: dijagonale pravca "/" (konstanta x+y), sortirane odozgo nadole.
        diag_values = sorted({x + y for (x, y) in initial_empty})
        ordered = []
        for d in diag_values:
            diag_cells = [(cx, cy) for (cx, cy) in initial_empty if (cx + cy) == d]
            if not diag_cells:
                continue

            left = min(diag_cells, key=lambda p: to_pixel(p[0], p[1], *self.center)[0])
            right = max(diag_cells, key=lambda p: to_pixel(p[0], p[1], *self.center)[0])
            lpx, lpy = to_pixel(left[0], left[1], *self.center)
            rpx, rpy = to_pixel(right[0], right[1], *self.center)
            ordered.append(((lpx, lpy), (rpx, rpy)))

        ordered.sort(key=lambda item: item[0][1])

        total = len(ordered)
        if total == 0:
            return
        mid = (total + 1) // 2

        # idx je broj koji se ispisuje. Levi deo: <= mid, desni deo: >= mid.
        for idx, (left_px, right_px) in enumerate(ordered, start=1):
            left_pos = (left_px[0] - side_gap, left_px[1]) if idx <= mid else None
            right_pos = (right_px[0] + side_gap, right_px[1]) if idx >= mid else None
            self._axis_number_layout.append((str(idx), left_pos, right_pos))

    # Ova metoda crta spoljne oznake koordinata (slova i brojevi) oko table.
    def _draw_axis_labels(self) -> None:
        """Iscrtaj fiksno mapirane oznake (bez pomeranja nakon poteza)."""
        if not self._axis_letter_layout and not self._axis_number_layout:
            return

        # Slova: ista gore i dole po vertikalnim kolonama.
        for label, top_pos, bottom_pos in self._axis_letter_layout:
            surf = self.small_font.render(label, True, (245, 245, 245))
            self.screen.blit(surf, surf.get_rect(center=top_pos))
            self.screen.blit(surf, surf.get_rect(center=bottom_pos))

        # Brojevi: / dijagonale, rasporedjeni sa leve/desne strane.
        for label, left_pos, right_pos in self._axis_number_layout:
            surf = self.small_font.render(label, True, (245, 245, 245))
            if left_pos is not None:
                self.screen.blit(surf, surf.get_rect(center=left_pos))
            if right_pos is not None:
                self.screen.blit(surf, surf.get_rect(center=right_pos))

    # Ova metoda iscrta tablu, kamenje i status partije.
    def draw(self) -> None:
        """Kompletan render jednog frame-a."""
        self.screen.fill((90, 90, 90))

        # 1) Crtanje mreze (linije susedstva).
        for (x, y), cell in self.state.nodes.items():
            if cell == Cell.BLOCKED:
                continue

            px, py = to_pixel(x, y, *self.center)
            for dx, dy in NEIGHBORS:
                nb = (x + dx, y + dy)
                if nb in self.state.nodes and self.state.nodes[nb] != Cell.BLOCKED:
                    nx, ny = to_pixel(nb[0], nb[1], *self.center)
                    pygame.draw.line(self.screen, (70, 70, 70), (px, py), (nx, ny), 1)

        # 2) Crtanje polja kao kruzica.
        for (x, y), cell in self.state.nodes.items():
            px, py = to_pixel(x, y, *self.center)
            pygame.draw.circle(self.screen, COLORS[cell], (px, py), RADIUS)
            pygame.draw.circle(self.screen, (0, 0, 0), (px, py), RADIUS, 2)

        # 3) Pomocni overlay: ostrva i spoljne koordinatne oznake.
        self._draw_island_labels()
        self._draw_axis_labels()

        # 4) Status teksta.
        if getattr(self.state, "game_over", False):
            winner = getattr(self.state, "winner", None)

            if winner is not None:
                winner_txt = "Pobednik: X" if winner == Cell.X else "Pobednik: O"
                self.screen.blit(self.font.render(winner_txt, True, (255, 255, 255)), (20, 20))

                details = getattr(self.state, "win_details", None) or {}
                if "dominance" in details and "threshold" in details:
                    dom = details["dominance"]
                    thr = details["threshold"]
                    line2 = f"Dominacija (min CW/CCW): {dom}  (prag: {thr})"
                    self.screen.blit(
                        self.small_font.render(line2, True, (255, 255, 255)),
                        (20, 55),
                    )
            else:
                # Kraj bez pobednika (npr. nema legalnih poteza).
                self.screen.blit(
                    self.font.render("Kraj igre: Nereseno", True, (255, 255, 255)),
                    (20, 20),
                )
        else:
            # Informativni status: ko je na potezu i da li je covek ili AI.
            who = "AI" if (self.ai_player == self.state.current_player) else "covek"
            txt = (
                ("Na potezu: X" if self.state.current_player == Cell.X else "Na potezu: O")
                + f"  ({who})"
            )
            self.screen.blit(self.font.render(txt, True, (255, 255, 255)), (20, 20))

        pygame.display.flip()

    # Ova metoda obradjuje klik misa i, ako je validan, odigrava potez coveka.
    def handle_click(self, pos) -> None:
        """Pretvori klik u potez ako su ispunjeni svi uslovi."""
        # 1) Posle kraja igre nema novih poteza.
        if getattr(self.state, "game_over", False):
            return

        # 2) Dok je AI na potezu, covekov klik se ignorise.
        if self._is_ai_turn():
            return

        # 3) Nadji kliknuto prazno polje unutar RADIUS distance.
        for (x, y), cell in self.state.nodes.items():
            if cell != Cell.EMPTY:
                continue

            # Ključno: koristimo ISTU projekciju kao pri crtanju (to_pixel),
            # pa je centar kruga ovde tacno isti kao centar nacrtanog polja.
            # Zato je test distance <= RADIUS pouzdan hit-test za "koji stone/polje je kliknuto".
            px, py = to_pixel(x, y, *self.center)
            if math.dist(pos, (px, py)) <= RADIUS:
                self.state.place_stone((x, y))
                return

    # Ova metoda pokrece glavni loop aplikacije i upravlja svim eventima.
    def run(self) -> None:
        """Glavna pygame petlja.

        Redosled po frame-u:
        - obrada event-a,
        - eventualni AI potez,
        - redraw scene.
        """
        running = True

        while running:
            # Ogranicenje FPS-a radi stabilnog CPU opterecenja.
            self.clock.tick(60)

            # Event processing.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)

            # AI igra automatski kada je njegov red.
            self._maybe_ai_move()

            # Render frame-a.
            self.draw()

        pygame.quit()
