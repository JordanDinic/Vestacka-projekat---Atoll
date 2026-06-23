"""AI modul za igru Atoll.

Ovaj fajl implementira potragu poteza za racunar:
1) takticke provere (trenutna pobeda / blok protivnikove pobede),
2) heuristicku procenu stanja,
3) minimax sa alfa-beta odsecanjem.

Kljucevi dizajna:
- Pravilo pobede se ne duplira ovde; koristi se preko GameState.
- Pretraga je depth-limited da bi bila dovoljno brza.
- candidate_moves() suzava grananje da minimax ostane praktican.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Set, Tuple

from state import Cell, Coord, GameState

# INF je sentinel za "prakticno terminalnu" vrednost.
# Koristi se kao ekstrem za pobedu/poraz i za inicijalizaciju minimax granica.
INF = 10**9


# Ova metoda vraca protivnika za prosledjenog igraca.
def opponent(p: Cell) -> Cell:
    """Vrati suprotnog igraca.

    Parametri:
    - p: igrac ciji protivnik treba da se dobije.

    Povratna vrednost:
    - Cell.O ako je p == Cell.X, inace Cell.X.
    """
    return Cell.O if p == Cell.X else Cell.X


@dataclass(frozen=True)
# Ova klasa cuva konfiguraciju AI pretrage.
class AIConfig:
    """Konfiguracija pretrage.

    Polja:
    - depth: maksimalna dubina rekurzije minimax-a.
    - move_limit: maksimalan broj kandidata po cvoru nakon rangiranja.
      Ako je None, ne radi se secenje kandidata.
    - min_keep: donja granica kandidata koja se cuva i kada je move_limit mali.

    Napomena:
    - Efektivan broj kandidata je max(min_keep, move_limit) kada move_limit nije None.
    """

    depth: int = 2
    move_limit: Optional[int] = 40
    min_keep: int = 12


# Ova metoda vraca sve zauzete celije (X i O) u stanju.
def _occupied_cells(st: GameState) -> Iterable[Coord]:
    """Iteriraj kroz sva zauzeta polja.

    Zasto postoji:
    - candidate_moves() koristi susede zauzetih polja kao dobru lokalnu aproksimaciju
      smislenih poteza, umesto da razmatra sva prazna polja.
    """
    # p: koordinata celije, c: stanje te celije.
    for p, c in st.nodes.items():
        if c in (Cell.X, Cell.O):
            yield p


# Ova metoda vraca sve poteze koji igracu odmah donose pobedu.
def winning_moves(st: GameState, player: Cell) -> List[Coord]:
    """Nadji sve legalne poteze koji daju trenutnu pobedu (win-in-1).

    Algoritam:
    1) Prodji kroz sva prazna polja.
    2) Simuliraj potez preko apply_move().
    3) Ako je novo stanje game_over i winner == player, potez je pobednicki.

    Slozenost:
    - O(B * C), gde je B broj praznih polja, a C cena check_winner() u apply_move().
    """
    wins: List[Coord] = []

    # mv: kandidat potez u prazno polje.
    for mv in st.get_valid_moves():
        # ns: novo simulirano stanje posle mv.
        ns = st.apply_move(mv, player)
        if ns is None:
            # Teoretski ne bi trebalo (mv je iz get_valid_moves),
            continue

        if ns.game_over and ns.winner == player:
            wins.append(mv)

    return wins


# Ova metoda vraca osnovne metrike najboljih komponenti ostrva igraca.
def _best_component_features(st: GameState, player: Cell) -> Tuple[int, int, int]:
    """Izdvoji najvaznije topoloske informacije o igracu.

    Povratna trojka:
    - best_dom: najbolja boundary-dominance vrednost medju komponentama igraca.
    - best_islands: velicina najvece komponente po broju ostrva.
    - num_components: ukupan broj komponenti ostrva igraca.

    Zasto je korisno:
    - Heuristika ima signal "koliko sam blizu pobede" (best_dom),
      i signal "koliko sam topoloski stabilan" (best_islands, num_components).
    """
    comps = st._connected_island_components(player)
    if not comps:
        return 0, 0, 0

    # best_dom: maksimum dominacije medju komponentama.
    best_dom = 0
    # best_islands: najveci broj ostrva u jednoj komponenti.
    best_islands = 0

    # comp: jedna komponenta (skup ID-jeva ostrva).
    for comp in comps:
        best_islands = max(best_islands, len(comp))
        best_dom = max(best_dom, st._boundary_dominance_score(comp))

    return best_dom, best_islands, len(comps)


# Ova metoda racuna heuristicku vrednost stanja iz perspektive igraca.
def evaluate(st: GameState, perspective: Cell) -> int:
    """Heuristika: veca vrednost znaci bolje za 'perspective'.

    Struktura ocene:
    1) Terminalna stanja: +/- INF.
    2) Takticke pretnje: broj win-in-1 poteza za oba igraca.
    3) Strategijski signal: razlika dominacije obodom.
    4) Struktura komponenti ostrva.
    5) Slab tie-break po broju kamenja.

    Napomena:
    - Ponderi su empirijski, birani da taktika (trenutne pretnje) ima
      prioritet nad "meksim" signalima.
    """
    # Ako je stanje terminalno i postoji pobednik, vrati ekstrem.
    if st.game_over and st.winner is not None:
        return INF if st.winner == perspective else -INF

    # opp: protivnik igraca perspective.
    opp = opponent(perspective)

    # Metrike strukture igre za oba igraca.
    dom_p, isl_p, comps_p = _best_component_features(st, perspective)
    dom_o, isl_o, comps_o = _best_component_features(st, opp)

    # Broj trenutnih taktickih pretnji (pobeda u jednom potezu).
    p_wins = len(winning_moves(st, perspective))
    o_wins = len(winning_moves(st, opp))

    # Broj kamenja oba igraca (slab tie-break signal).
    stones_p = sum(1 for c in st.nodes.values() if c == perspective)
    stones_o = sum(1 for c in st.nodes.values() if c == opp)

    # score: akumulirana heuristicka vrednost.
    score = 0

    # (1) Taktika: ko ima vise neposrednih pretnji.
    if p_wins > 0:
        score += 200_000 + 10_000 * p_wins
    if o_wins > 0:
        score -= 220_000 + 12_000 * o_wins

    # (2) Dominacija obodom kao glavni strategijski signal.
    score += 3000 * (dom_p - dom_o)

    # (3) Veca komponenta ostrva je pozeljna.
    score += 600 * (isl_p - isl_o)

    # (4) Manje mojih komponenti je bolje; vise protivnickih je bolje za mene.
    score += 80 * (comps_o - comps_p)

    # (5) Broj kamenja: vrlo mali uticaj, samo tie-break.
    score += 1 * (stones_p - stones_o)

    # Dodatni "boost" blizu pobednickog praga (7).
    # Ovi skokovi ubrzavaju AI ka kljucnim prelazima dominacije.
    if dom_p == 6:
        score += 25_000
    if dom_o == 6:
        score -= 28_000
    if dom_p == 5:
        score += 9_000
    if dom_o == 5:
        score -= 10_000

    return score


# Ova metoda bira razuman skup kandidata koji idu u minimax.
def candidate_moves(st: GameState, player: Cell, cfg: AIConfig) -> List[Coord]:
    """Generisi i rangiraj poteze koji ulaze u pretragu.

    Prioriteti:
    1) Ako postoji moj instant win, vrati samo te poteze.
    2) Ako protivnik ima instant win, vrati samo blok poteze.
    3) Inace: kandidati su susedi zauzetih polja + prazna obodna polja.
    4) Kandidati se lokalno rangiraju i skracuju na top-K.

    Zasto ovaj dizajn:
    - Drasticno smanjuje grananje minimax stabla.
    - I dalje cuva takticke obavezne poteze (win/block).
    """

    # (1) Trenutna pobeda ima apsolutni prioritet.
    my_wins = winning_moves(st, player)
    if my_wins:
        # sorted() osigurava deterministicko ponasanje pri istom score-u.
        return sorted(my_wins)

    opp = opponent(player)

    # (2) Ako protivnik ima win-in-1, prioritet je blok.
    opp_wins = set(winning_moves(st, opp))
    if opp_wins:
        return sorted(opp_wins)

    # (3) Kandidati iz lokalnog konteksta table.
    cand: Set[Coord] = set()

    # Dodaj sva prazna susedna polja oko vec postavljenih kamenova.
    for occ in _occupied_cells(st):
        for nb in st._neighbors(occ):
            if st.nodes.get(nb) == Cell.EMPTY:
                cand.add(nb)

    # Dodaj i prazna obodna polja (cesto su vazna za spajanje ostrva).
    for e in st._edge_cells_excluding_corners():
        if st.nodes.get(e) == Cell.EMPTY:
            cand.add(e)

    # Fallback: ako nema kandidata po lokalnom pravilu, uzmi sve legalne poteze.
    if not cand:
        return st.get_valid_moves()

    # edge: set za O(1) proveru da li je potez na obodu.
    edge = st._edge_cells_excluding_corners()

    # Ova pomocna metoda lokalno ocenjuje jedan kandidat bez rekurzije.
    def local_score(mv: Coord) -> int:
        """Brza lokalna procena poteza mv.

        Skor favorizuje:
        - kontakt sa sopstvenim ostrvom,
        - vise sopstvenih suseda,
        - obodna polja.

        Penalizuje:
        - kontakt sa protivnickim ostrvom,
        - vise protivnickih suseda.
        """
        # Broj suseda koji su moji/protivnikovi kamenovi.
        adj_my = 0
        adj_opp = 0

        # Binarni indikatori kontakta sa ostrvima.
        touch_my_island = 0
        touch_opp_island = 0

        for nb in st._neighbors(mv):
            c = st.nodes.get(nb)
            if c == player:
                adj_my += 1
            elif c == opp:
                adj_opp += 1

            # iid je definisan samo ako je nb deo pocetnog ostrva.
            iid = st.island_at_cell.get(nb)
            if iid is not None:
                if st.islands[iid].owner == player:
                    touch_my_island = 1
                else:
                    touch_opp_island = 1

        on_edge = 1 if mv in edge else 0

        return (
            8 * touch_my_island
            + 1 * adj_my
            + 2 * on_edge
            - 2 * touch_opp_island
            - 4 * adj_opp
        )

    # (4) Deterministicko sortiranje: prvo po local_score, pa po koordinati.
    ordered = sorted(cand, key=lambda mv: (local_score(mv), mv[0], mv[1]), reverse=True)

    # Secenje kandidata na top-K prema konfiguraciji.
    if cfg.move_limit is None:
        return ordered

    k = max(cfg.min_keep, cfg.move_limit)
    return ordered[:k]


# Ova metoda implementira minimax sa alfa-beta odsecanjem.
def alphabeta(
    st: GameState,
    depth: int,
    alpha: int,
    beta: int,
    root_player: Cell,
    cfg: AIConfig,
) -> Tuple[int, Optional[Coord]]:
    """Rekurzivna minimax pretraga sa alfa-beta odsecanjem.

    Parametri:
    - st: trenutno stanje cvora.
    - depth: koliko jos slojeva pretrazujemo.
    - alpha: najbolja garantovana vrednost za MAX na putu od korena.
    - beta: najbolja garantovana vrednost za MIN na putu od korena.
    - root_player: igrac iz cijeg ugla se vrednuje stablo.
    - cfg: konfiguracija kandidata/dubine.

    Povratna vrednost:
    - (value, move), gde move vazi samo za trenutni nivo.
    """
    # Baza rekurzije: ili je dubina potrosena, ili je stanje terminalno.
    if depth == 0 or st.game_over:
        return evaluate(st, root_player), None

    cur = st.current_player
    maximizing = cur == root_player

    # Generisi kandidatske poteze za igraca koji je trenutno na potezu.
    moves = candidate_moves(st, cur, cfg)
    if not moves:
        # Ako nema poteza, vrati evaluaciju trenutnog stanja.
        return evaluate(st, root_player), None

    # best_move: najbolji potez za ovaj cvor, inicijalno nepoznat.
    best_move: Optional[Coord] = None

    if maximizing:
        # MAX nivo zeli sto vecu vrednost.
        value = -INF

        for mv in moves:
            ns = st.apply_move(mv, cur)
            if ns is None:
                continue

            child_val, _ = alphabeta(ns, depth - 1, alpha, beta, root_player, cfg)

            # Vazno: best_move se popunjava i kada je prvi child_val == value.
            # Time izbegavamo scenario "ima poteza, a move ostane None".
            if best_move is None or child_val > value:
                value = child_val
                best_move = mv

            # alpha je donja granica koju MAX moze da garantuje.
            alpha = max(alpha, value)

            # Ako su se granice preklopile, ostatak grane ne moze promeniti odluku.
            if alpha >= beta:
                break

        return value, best_move

    # MIN nivo zeli sto manju vrednost.
    value = INF

    for mv in moves:
        ns = st.apply_move(mv, cur)
        if ns is None:
            continue

        child_val, _ = alphabeta(ns, depth - 1, alpha, beta, root_player, cfg)

        # Isto pravilo za inicijalno biranje poteza na MIN nivou.
        if best_move is None or child_val < value:
            value = child_val
            best_move = mv

        # beta je gornja granica koju MIN moze da garantuje.
        beta = min(beta, value)

        if alpha >= beta:
            break

    return value, best_move


# Ova metoda bira konacan potez koji AI treba da odigra u trenutnom stanju.
def choose_best_move(st: GameState, player: Cell, cfg: AIConfig) -> Optional[Coord]:
    """Javni API za izbor AI poteza.

    Redosled odluke:
    1) Ako nije red na AI ili je igra gotova -> None.
    2) Ako postoji root win-in-1 -> odigraj odmah.
    3) Inace pokreni minimax.
    4) Ako minimax vrati None (zastita), uzmi prvi legalan potez.
    """
    if st.game_over or st.current_player != player:
        return None

    wins = winning_moves(st, player)
    if wins:
        return sorted(wins)[0]

    _, mv = alphabeta(st, cfg.depth, -INF, INF, player, cfg)
    if mv is not None:
        return mv

    # Safety fallback: ne ostavljaj AI bez poteza ako legalni potezi postoje.
    legal = st.get_valid_moves()
    if legal:
        return sorted(legal)[0]

    # Nema legalnih poteza.
    return None
