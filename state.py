from __future__ import annotations

"""Model stanja igre Atoll.

Ceo projekat se oslanja na ovu klasu jer ovde zivi:
- reprezentacija table,
- operator prelaza stanja,
- pravilo pobede.

Konceptualno, ovo je "single source of truth" za logiku igre.
GUI i AI samo koriste API iz ove datoteke.
"""

import math
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Deque, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from geometry import NEIGHBORS


class Cell(Enum):
    """Tip sadrzaja jednog polja table.

    Vrednosti:
    - BLOCKED: teme heksagona, neigraljivo polje.
    - EMPTY: prazno polje na koje se moze igrati.
    - X / O: polje zauzeto kamenom igraca X ili O.
    """

    BLOCKED = auto()
    EMPTY = auto()
    X = auto()
    O = auto()


# Coord je axial koordinata jednog polja (x, y).
Coord = Tuple[int, int]


# Ova metoda racuna trecu cube koordinatu z za date axial koordinate x i y.
def _cube_z(x: int, y: int) -> int:
    """Pretvori axial koordinatu u cube komponentu z.

    Veza je standardna za heks mrezu: x + y + z = 0, pa je z = -x - y.
    """
    return -x - y


# Ova metoda proverava da li je polje jedno od 6 temena spoljnog heksagona.
def _is_corner(x: int, y: int, z: int, R: int) -> bool:
    """Vrati True ako je (x, y, z) teme heksagona radijusa R."""
    return (
        (abs(x) == R and abs(y) == R)
        or (abs(x) == R and abs(z) == R)
        or (abs(y) == R and abs(z) == R)
    )


@dataclass(frozen=True)
# Ova klasa opisuje jedno pocetno ostrvo na obodu table.
class Island:
    """Podaci o ostrvu.

    Polja:
    - id: indeks ostrva 0..11 po smeru kazaljke.
    - owner: igrac kome ostrvo pripada (X ili O).
    - cells: sva polja koja cine ostrvo.
    """

    id: int
    owner: Cell
    cells: FrozenSet[Coord]


# Ova klasa cuva kompletno stanje partije.
class GameState:
    """Glavni model partije Atoll.

    Atributi koje koristi ostatak sistema:
    - nodes: mapa Coord -> Cell (tabla).
    - current_player: igrac na potezu.
    - islands/island_at_cell: indeksirana ostrva.
    - game_over/winner/win_details: status zavrsetka partije.
    """

    # Ova metoda inicijalizuje novu igru za zadatu velicinu n.
    def __init__(self, n: int):
        """Kreiraj pocetno stanje igre.

        Parametar:
        - n: neparan broj iz [5, 9].

        Napomena:
        - U ovom projektu je R = n.
        """
        if n < 5 or n > 9 or n % 2 == 0:
            raise ValueError("n must be odd in range [5, 9]")

        # n i R opisuju geometriju table.
        self.n = n
        self.R = n

        # Igrac na potezu i sama tabla.
        self.current_player: Cell = Cell.X
        self.nodes: Dict[Coord, Cell] = {}

        # Model ostrva (inicijalnih obodnih grupa kamenja).
        self.islands: List[Island] = []
        self.island_at_cell: Dict[Coord, int] = {}

        # Status kraja partije.
        self.game_over: bool = False
        self.winner: Optional[Cell] = None
        self.win_details: Optional[dict] = None

        self._init_nodes_and_islands()

    # Ova metoda pravi pocetnu tablu i raspored ostrva po pravilima zadatka.
    def _init_nodes_and_islands(self) -> None:
        """Generisi sve celije table i postavi pocetne kamenove.

        Koraci:
        1) Napravi pun heksagon radijusa R sa EMPTY poljima.
        2) Oznaci 6 temena kao BLOCKED.
        3) Postavi pocetna ostrva X/O po obodu.
        4) Otkrij ostrva i indeksiraj ih 0..11.
        """
        R = self.R

        # 1) Kreiranje svih polja heksagona.
        for x in range(-R, R + 1):
            for y in range(-R, R + 1):
                z = _cube_z(x, y)
                if abs(x) <= R and abs(y) <= R and abs(z) <= R:
                    self.nodes[(x, y)] = Cell.EMPTY

        # 2) Temena postaju BLOCKED.
        for (x, y) in list(self.nodes.keys()):
            z = _cube_z(x, y)
            if _is_corner(x, y, z, R):
                self.nodes[(x, y)] = Cell.BLOCKED

        # 3) Pocetna ostrva po stranama spoljnog heksagona.
        # i pomera duz svake strane od temena ka sredini.
        for i in range(1, (R + 1) // 2):
            self.nodes[(-R, i)] = Cell.X
            self.nodes[(-R, R - i)] = Cell.O

            self.nodes[(-R + i, R)] = Cell.X
            self.nodes[(-i, R)] = Cell.O

            self.nodes[(i, R - i)] = Cell.X
            self.nodes[(R - i, i)] = Cell.O

            self.nodes[(R, -i)] = Cell.X
            self.nodes[(R, -R + i)] = Cell.O

            self.nodes[(R - i, -R)] = Cell.X
            self.nodes[(i, -R)] = Cell.O

            self.nodes[(-i, -R + i)] = Cell.X
            self.nodes[(-R + i, -i)] = Cell.O

        # 4) Svako ostrvo treba da ima (n-1)//2 celija.
        expected_island_size = (self.n - 1) // 2
        self._discover_islands_clockwise(expected_island_size)

    # Ova metoda vraca susede jednog polja (bez izlaska sa table i bez BLOCKED).
    def _neighbors(self, pos: Coord) -> Iterable[Coord]:
        """Generator legalnih suseda polja pos.

        Susedstvo je definisano preko geometry.NEIGHBORS (6 smerova).
        """
        x, y = pos
        for dx, dy in NEIGHBORS:
            nb = (x + dx, y + dy)
            if nb in self.nodes and self.nodes[nb] != Cell.BLOCKED:
                yield nb

    # Ova metoda vraca sva obodna polja osim temena.
    def _edge_cells_excluding_corners(self) -> Set[Coord]:
        """Vrati spoljasnji prsten bez coskova."""
        R = self.R
        out: Set[Coord] = set()

        for (x, y), cell in self.nodes.items():
            if cell == Cell.BLOCKED:
                continue

            z = _cube_z(x, y)
            # Polje je na obodu ako je max(|x|, |y|, |z|) == R.
            if max(abs(x), abs(y), abs(z)) != R:
                continue
            if _is_corner(x, y, z, R):
                continue
            out.add((x, y))

        return out

    # Ova metoda pretvara jedno axial polje u 2D koordinate.
    @staticmethod
    def _axial_to_cartesian(p: Coord) -> Tuple[float, float]:
        """Mapiranje axial -> 2D radi sortiranja po uglu.

        Ovo ne sluzi za GUI crtanje (to radi geometry.to_pixel),
        nego za stabilno odredjivanje CW redosleda ostrva.
        """
        x, y = p
        cx = x + y / 2.0
        cy = (math.sqrt(3) / 2.0) * y
        return cx, cy

    # Ova metoda pronalazi svih 12 ostrva i dodeljuje im ID redom po smeru kazaljke.
    def _discover_islands_clockwise(self, expected_island_size: int) -> None:
        """Detektuj i indeksiraj ostrva.

        Strategija:
        - kandidati su obodna X/O polja,
        - BFS deli kandidate na komponente istog vlasnika,
        - komponente se sortiraju po uglu centroida (CW),
        - rezultat su islands + island_at_cell.
        """
        edge = self._edge_cells_excluding_corners()
        candidate = {p for p in edge if self.nodes[p] in (Cell.X, Cell.O)}

        # comps: lista parova (owner, skup_polja_ostrva).
        comps: List[Tuple[Cell, Set[Coord]]] = []
        seen: Set[Coord] = set()

        for start in list(candidate):
            if start in seen:
                continue

            owner = self.nodes[start]
            q: Deque[Coord] = deque([start])
            comp: Set[Coord] = set()
            seen.add(start)

            while q:
                cur = q.popleft()
                comp.add(cur)

                for nb in self._neighbors(cur):
                    if nb not in candidate:
                        continue
                    if nb in seen:
                        continue
                    if self.nodes[nb] != owner:
                        continue
                    seen.add(nb)
                    q.append(nb)

            comps.append((owner, comp))

        # Sanity check: po pravilima mora biti tacno 12 ostrva.
        if len(comps) != 12:
            raise RuntimeError(f"Expected 12 islands, discovered {len(comps)}")

        for _owner, comp in comps:
            if len(comp) != expected_island_size:
                raise RuntimeError(
                    f"Island size mismatch: expected {expected_island_size}, got {len(comp)}"
                )

        # Pomocna funkcija za sortiranje komponenti po uglu centroida.
        def centroid_angle(cells: Set[Coord]) -> float:
            xs: List[float] = []
            ys: List[float] = []

            for c in cells:
                cx, cy = self._axial_to_cartesian(c)
                xs.append(cx)
                ys.append(cy)

            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            return math.atan2(my, mx)

        # reverse=True daje smer kazaljke na satu.
        comps_sorted = sorted(comps, key=lambda t: centroid_angle(t[1]), reverse=True)

        islands: List[Island] = []
        island_at_cell: Dict[Coord, int] = {}

        for iid, (owner, cells) in enumerate(comps_sorted):
            fs = frozenset(cells)
            islands.append(Island(id=iid, owner=owner, cells=fs))
            for c in fs:
                island_at_cell[c] = iid

        self.islands = islands
        self.island_at_cell = island_at_cell

    # Ova metoda proverava da li je potez legalan (ciljno polje je EMPTY).
    def is_valid_move(self, pos: Coord) -> bool:
        """Provera legalnosti jednog poteza."""
        return self.nodes.get(pos) == Cell.EMPTY

    # Ova metoda vraca sva trenutno legalna polja za potez.
    def get_valid_moves(self) -> List[Coord]:
        """Vrati listu svih praznih polja."""
        return [p for (p, c) in self.nodes.items() if c == Cell.EMPTY]

    # Ova metoda pravi plitki klon stanja za potrebe simulacije poteza.
    def clone(self) -> "GameState":
        """Napravi kopiju stanja bez ponovnog racunanja ostrva.

        Zasto object.__new__:
        - izbegavamo ponovno pokretanje __init__ i skupu inicijalizaciju.
        """
        st = object.__new__(GameState)
        st.n = self.n
        st.R = self.R
        st.current_player = self.current_player
        st.nodes = dict(self.nodes)
        st.islands = self.islands
        st.island_at_cell = self.island_at_cell
        st.game_over = self.game_over
        st.winner = self.winner
        st.win_details = self.win_details
        return st

    # Ova metoda vraca novo stanje nakon simuliranog poteza, bez promene originala.
    def apply_move(self, pos: Coord, player: Optional[Cell] = None) -> Optional["GameState"]:
        """Functional style operator promene stanja.

        Parametri:
        - pos: polje gde se odigrava potez.
        - player: igrac koji igra potez; ako je None, uzima se current_player.

        Povratna vrednost:
        - Novo stanje ako je potez legalan.
        - None ako potez nije legalan.
        """
        if player is None:
            player = self.current_player

        if self.nodes.get(pos) != Cell.EMPTY:
            return None

        ns = self.clone()
        ns.nodes[pos] = player
        ns.current_player = Cell.O if player == Cell.X else Cell.X
        ns._update_game_over()
        return ns

    # Ova metoda vraca sve sledbenike stanja: (potez, novo_stanje).
    def successors(self, player: Optional[Cell] = None) -> List[Tuple[Coord, "GameState"]]:
        """Enumeracija svih legalnih sledecih stanja za igraca."""
        if player is None:
            player = self.current_player

        out: List[Tuple[Coord, GameState]] = []
        for mv in self.get_valid_moves():
            ns = self.apply_move(mv, player)
            if ns is not None:
                out.append((mv, ns))

        return out

    # Ova metoda menja trenutno stanje (koristi se u realnoj partiji kroz GUI).
    def place_stone(self, pos: Coord) -> bool:
        """Imperativni operator poteza za runtime partiju.

        Razlika u odnosu na apply_move:
        - apply_move pravi novo stanje,
        - place_stone menja postojece stanje "in-place".
        """
        if self.game_over:
            return False
        if not self.is_valid_move(pos):
            return False

        self.nodes[pos] = self.current_player
        self.current_player = Cell.O if self.current_player == Cell.X else Cell.X
        self._update_game_over()
        return True

    # Ova metoda vraca sva polja koja pripadaju igracu (i ostrva i kasnije poteze).
    def _player_cells(self, player: Cell) -> Set[Coord]:
        """Skup svih koordinata koje pripadaju igracu player."""
        return {p for (p, c) in self.nodes.items() if c == player}

    # Ova metoda nalazi komponente povezanih ostrva igraca preko njegovih kamenja.
    def _connected_island_components(self, player: Cell) -> List[Set[int]]:
        """Vrati povezane komponente ostrva igraca.

        Ideja:
        - krecemo od svakog igracevog ostrva,
        - BFS prolazi kroz sva igraceva polja,
        - kad BFS dodirne polje koje je deo ostrva, upise se ID ostrva,
        - rezultat je lista skupova ID-jeva ostrva po komponentama.
        """
        player_cells = self._player_cells(player)

        player_islands = [isl.id for isl in self.islands if isl.owner == player]
        if len(player_islands) < 2:
            return []

        seen_islands: Set[int] = set()
        components: List[Set[int]] = []

        for isl in self.islands:
            if isl.owner != player or isl.id in seen_islands:
                continue

            start_cell = next(iter(isl.cells))
            q: Deque[Coord] = deque([start_cell])
            visited_cells: Set[Coord] = set()
            comp_islands: Set[int] = set()

            while q:
                cur = q.popleft()
                if cur in visited_cells:
                    continue
                visited_cells.add(cur)

                iid = self.island_at_cell.get(cur)
                if iid is not None and self.islands[iid].owner == player:
                    comp_islands.add(iid)

                for nb in self._neighbors(cur):
                    if nb in player_cells and nb not in visited_cells:
                        q.append(nb)

            if comp_islands:
                seen_islands |= comp_islands
                components.append(comp_islands)

        return components

    # Ova metoda vraca broj obodnih koraka do poslednjeg ostrva komponente u smeru step.
    @staticmethod
    def _count_to_last_in_dir(start: int, comp_set: Set[int], step: int, m: int = 12) -> int:
        """Obodno brojanje od jednog ostrva do "poslednjeg" ostrva komponente.

        Parametri:
        - start: id ostrva odakle brojimo.
        - comp_set: skup ostrva posmatrane komponente.
        - step: +1 CW, -1 CCW.
        - m: broj ostrva na obodu (ovde 12).

        Povratna vrednost:
        - Broj "preskocenih" ostrva ukljucujuci i start i poslednje ostrvo.
        """
        last_dist = 0
        pos = start
        dist = 0

        for _k in range(1, m):
            pos = (pos + step) % m
            dist += 1
            if pos in comp_set:
                last_dist = dist

        return last_dist + 1

    # Ova metoda racuna boundary-dominance skor za jednu komponentu ostrva.
    def _boundary_dominance_score(self, comp_islands: Set[int]) -> int:
        """Skor dominacije komponente po obodu.

        Definicija iz zadatka:
        - Za svako ostrvo s u komponenti:
          cw = broj do poslednjeg ostrva u CW smeru,
          ccw = broj do poslednjeg ostrva u CCW smeru,
          local = min(cw, ccw).
        - Skor komponente je minimum local vrednosti preko svih s.
        """
        if not comp_islands:
            return 0

        global_min = 10**9
        for s in comp_islands:
            cw = self._count_to_last_in_dir(s, comp_islands, +1, 12)
            ccw = self._count_to_last_in_dir(s, comp_islands, -1, 12)
            global_min = min(global_min, min(cw, ccw))

        return global_min

    # Ova metoda proverava da li neki igrac ispunjava uslov pobede.
    def check_winner(self) -> Optional[Cell]:
        """Proveri pobedu po pravilu dominacije obodom.

        Pravilo:
        - m = 12 ostrva,
        - prag d = m/2 + 1 = 7,
        - igrac pobedjuje ako neka njegova povezana komponenta ostrva ima
          dominance >= d.
        """
        m = 12
        d = (m // 2) + 1

        for player in (Cell.X, Cell.O):
            for comp in self._connected_island_components(player):
                if len(comp) < 2:
                    # Jedno ostrvo samo po sebi nije smislen uslov povezivanja.
                    continue

                dom = self._boundary_dominance_score(comp)
                if dom >= d:
                    self.win_details = {
                        "player": player,
                        "component": sorted(comp),
                        "dominance": dom,
                        "threshold": d,
                    }
                    return player

        return None

    # Ova metoda azurira zastavice kraja igre nakon svake promene stanja.
    def _update_game_over(self) -> None:
        """Sinhronizuj game_over/winner sa trenutnom tablom.

        Redosled je bitan:
        1) prvo proveri pobednika,
        2) ako nema pobednika, proveri da li je igra ostala bez legalnih poteza.
        """
        w = self.check_winner()
        if w is not None:
            self.game_over = True
            self.winner = w
            return

        # Ako nema legalnih poteza i nema pobednika, zatvori kao nereseno.
        if not self.get_valid_moves():
            self.game_over = True
            self.winner = None
            self.win_details = {"reason": "no_moves"}
