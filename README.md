# Atoll - Projekat iz Vestacke Inteligencije

Ovaj projekat predstavlja implementaciju igre **Atoll** u Python-u, sa grafickim interfejsom i podrskom za igranje protiv racunara. Aplikacija omogucava:

- covek vs covek mod,
- covek vs racunar mod,
- izbor velicine table,
- izbor igraca koji prvi igra,
- podesavanje dubine AI pretrage i broja kandidata po cvoru.

AI koristi **Minimax** sa **alfa-beta odsecanjem**, uz heuristiku prilagodjenu pravilima igre Atoll.

## Tehnologije

- Python
- Pygame

## Struktura projekta

- `main.py` - ulazna tacka aplikacije; cita parametre i pokrece GUI
- `gui.py` - prikaz table, obrada klikova i integracija AI poteza
- `state.py` - model stanja igre i kompletna logika pravila
- `ai.py` - AI pretraga, heuristika i izbor poteza
- `geometry.py` - rad sa heksagonalnom mrezom i projekcija koordinata
- `I_FAZA.txt` - kratak opis resenja prve faze
- `III_FAZA.txt` - opis prosirenja za AI fazu
- `Izvestaj_Atoll_Projekat.pdf` - prateci izvestaj

## Pokretanje projekta

Preporuceno je koristiti virtuelno okruzenje.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pygame
python main.py
```

Ako koristite `py` launcher na Windows-u, ekvivalentno moze i:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install pygame
py main.py
```

## Unos parametara pri pokretanju

Program pri startu trazi nekoliko vrednosti kroz konzolu:

- `n` - neparna velicina table u opsegu `5-9`
- mod igre:
  - `1` = Covek-Covek
  - `2` = Covek-Racunar
- koji igrac igra prvi: `X` ili `O`
- u AI rezimu:
  - da li covek igra kao `X` ili `O`
  - dubina AI pretrage `1-4`
  - maksimalan broj kandidata po cvoru

Posle unosa otvara se Pygame prozor i igra se odvija klikom na prazna polja.

## Osnovna pravila i implementacija

Tabla je modelovana kao pravilni heksagon u **axial/cube** koordinatnom sistemu. Sest temena spoljnog heksagona su blokirana, dok su uz ivice rasporedjena pocetna ostrva igraca `X` i `O`.

Pobeda se proverava preko pravila **dominacije obodom**:

- posmatraju se povezane komponente igracevih ostrva,
- za svaku komponentu racuna se boundary-dominance skor,
- igrac pobedjuje kada neka njegova komponenta dostigne prag `>= 7`.

Kompletna logika pravila nalazi se u `state.py`, dok GUI i AI koriste taj modul kao jedini izvor istine za stanje partije.

## Kako radi AI

AI u `ai.py` bira potez kroz nekoliko koraka:

1. proverava da li postoji trenutna pobeda u jednom potezu,
2. proverava da li mora da blokira protivnikovu trenutnu pobedu,
3. generise smislen skup kandidata,
4. pokrece Minimax sa alfa-beta odsecanjem,
5. koristi heuristiku zasnovanu na:
   - dominaciji obodom,
   - strukturi povezanih komponenti,
   - broju neposrednih pretnji,
   - slabom tie-break signalu po broju kamenja.

Ovakav pristup omogucava razumno vreme odziva i na vecim tablama, bez potpunog pretrazivanja svih mogucih stanja.

## Napomene

- Projekat trenutno nema `requirements.txt`, pa se zavisnost `pygame` instalira rucno.
- AI dubina `3-4` daje bolju igru, ali moze znacajno usporiti odgovor racunara.
- `.gitignore` je dodat za Python lokalne artefakte i virtuelno okruzenje.
