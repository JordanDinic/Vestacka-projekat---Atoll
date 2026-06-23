# """Geometrijske pomocne funkcije za heksagonalnu tablu.

# Ovaj modul je namerno mali i cist:
# - definise 6 suseda u axial koordinatama,
# - prevodi axial koordinate u piksele za GUI crtanje.
# """

# import math

# # SCALE kontrolise vizuelnu gustinu mreze na ekranu.
# # Veci SCALE -> veca tabla na ekranu.
# SCALE = 45

# # SIN60 je konstanta potrebna za vertikalnu projekciju heks mreze.
# # Koristi se u formuli py = cy + SCALE * y * sin(60deg).
# SIN60 = math.sin(math.pi / 3)


# # Ova metoda pretvara axial koordinate (x, y) u piksel koordinate na ekranu.
# def to_pixel(x: int, y: int, cx: int, cy: int) -> tuple[int, int]:
#     """Mapiranje axial -> ekran.

#     Parametri:
#     - x, y: axial koordinate celije.
#     - cx, cy: centar table u koordinatama prozora.

#     Formula i intuicija:
#     - Axial osa x u pikselima ima vektor (SCALE, 0).
#     - Axial osa y u pikselima ima vektor (SCALE/2, SCALE*sin(60)).
#     - Koordinata polja je linearna kombinacija tih osa plus centar table:
#       px = cx + SCALE * x + (SCALE/2) * y
#       py = cy + SCALE * sin(60) * y
#     - Isto kao skraceni zapis:
#       px = cx + SCALE * (x + y/2)
#       py = cy + SCALE * y * sin(60)

#     Povratna vrednost:
#     - (px, py) kao celobrojne piksel koordinate.
#     """
#     # x doprinos: cisto horizontalno pomeranje.
#     # y doprinos: pola horizontalnog + puno vertikalno pomeranje (zbog ugla od 60 stepeni).
#     px = cx + SCALE * (x + y / 2)
#     py = cy + SCALE * y * SIN60
#     return int(px), int(py)


# # NEIGHBORS su standardni axial pomeraji do 6 susednih celija.
# # Redosled nije semanticki presudan, ali je konzistentan kroz ceo projekat.
# NEIGHBORS = [
#     (1, 0),
#     (0, 1),
#     (-1, 1),
#     (-1, 0),
#     (0, -1),
#     (1, -1),
# ]
import math

SCALE = 45
SIN60 = math.sin(math.pi / 3)
ROT_DEG = 30 # Promeni na 0, 30 ili 45 po zelji.
ROT = math.radians(ROT_DEG)
COS_R = math.cos(ROT)
SIN_R = math.sin(ROT)


def to_pixel(x, y, cx, cy):
    # Axial -> lokalni 2D (pre rotacije)
    ux = SCALE * (x + y / 2)
    uy = SCALE * y * SIN60

    # Rotacija cele mreze oko centra (cx, cy)
    rx = ux * COS_R - uy * SIN_R
    ry = ux * SIN_R + uy * COS_R

    px = cx + rx
    py = cy + ry
    return int(px), int(py)


NEIGHBORS = [
    (1, 0),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (0, -1),
    (1, -1),
]