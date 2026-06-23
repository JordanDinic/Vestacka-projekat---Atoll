"""Ulazna tacka aplikacije Atoll.

Ovaj modul ima jednu odgovornost:
- prikupiti parametre partije od korisnika,
- sastaviti GameState + GUI,
- pokrenuti glavni loop.

Sva pravila igre su u state.py, a AI logika u ai.py.
main.py je namerno tanak i organizacioni.
"""

from state import Cell, GameState
from gui import AtolGUI


# Ova metoda ucitava velicinu table n (neparan broj 5-9).
def _read_n() -> int:
    """Procitaj n iz konzole uz bezbedan fallback.

    Pravila:
    - ENTER -> 5,
    - nevalidan unos -> 5.

    Napomena:
    - Validaciju opsega [5,9] i neparnosti definitivno radi GameState.__init__.
    """
    try:
        raw = input("Unesi n (neparan 5-9, ENTER za 5): ").strip()
        n = 5 if raw == "" else int(raw)
    except Exception:
        n = 5
    return n



# Ova metoda ucitava ko igra prvi potez (X ili O).
def _read_first_player() -> Cell:
    """Procitaj igraca koji otvara partiju.

    - ENTER -> X
    - eksplicitno O -> O
    """
    raw = input("Ko igra prvi? (X/O, ENTER za X): ").strip().upper()
    if raw == "O":
        return Cell.O
    return Cell.X


# Ova metoda ucitava mod igre: covek-covek ili covek-racunar.
def _read_mode() -> str:
    """Procitaj mod igre.

    Povratna vrednost:
    - "HH" za covek-covek,
    - "HAI" za covek-racunar.
    """
    raw = input("Mod igre: 1=Covek-Covek, 2=Covek-Racunar (ENTER za 2): ").strip()
    return "HH" if raw == "1" else "HAI"


# Ova metoda ucitava da li covek igra kao X ili O.
def _read_human_player() -> Cell:
    """Odredi boju coveka u HAI rezimu."""
    raw = input("Covek igra kao? (X/O, ENTER za X): ").strip().upper()
    if raw == "O":
        return Cell.O
    return Cell.X


# Ova metoda ucitava dubinu AI pretrage i ogranicava je na [1, 4].
def _read_ai_depth() -> int:
    """Procitaj dubinu pretrage AI-a.

    Razlog ogranicenja:
    - veca dubina eksponencijalno uvecava broj stanja,
    - za interaktivnu igru [1,4] je praktican opseg.
    """
    raw = input("AI dubina (1-4, ENTER za 2): ").strip()
    if raw == "":
        return 2

    try:
        d = int(raw)
    except Exception:
        return 2

    return max(1, min(4, d))


# Ova metoda ucitava max broj kandidata po cvoru AI stabla.
def _read_ai_move_limit() -> int:
    """Procitaj limit kandidata po cvoru.

    Sustina:
    - manji limit: brzi AI, slabije pretrazuje,
    - veci limit: sporiji AI, kvalitetnija odluka.
    """
    raw = input("AI max poteza po cvoru (ENTER za 30): ").strip()
    if raw == "":
        return 30

    try:
        k = int(raw)
    except Exception:
        return 30

    return max(5, min(200, k))


# Ova metoda je ulazna tacka programa: ucita parametre, kreira stanje i pokrece GUI.
def main() -> None:
    """Sastavi i pokreni celu aplikaciju."""
    # 1) Osnovna konfiguracija table i moda.
    n = _read_n()
    mode = _read_mode()

    # 2) Podrazumevane AI vrednosti.
    ai_player = None
    ai_depth = 2
    ai_limit = 30

    # 3) Ako je HAI, procitaj dodatne AI/covek parametre.
    if mode == "HAI":
        human = _read_human_player()
        ai_player = Cell.O if human == Cell.X else Cell.X
        ai_depth = _read_ai_depth()
        ai_limit = _read_ai_move_limit()

    # 4) Ko igra prvi (vazi i za HH i za HAI).
    first = _read_first_player()

    # 5) Napravi model stanja i postavi igraca na potezu.
    state = GameState(n=n)
    state.current_player = first

    # 6) Podigni GUI sloj i prepusti mu glavni loop.
    gui = AtolGUI(state, ai_player=ai_player, ai_depth=ai_depth, ai_move_limit=ai_limit)
    gui.run()


if __name__ == "__main__":
    main()
