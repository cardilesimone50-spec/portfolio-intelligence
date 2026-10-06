"""Marchio Smarteefinance: il simbolo (rombo sfaccettato) e la scritta.

Un'unica definizione geometrica per tre usi: SVG nell'interfaccia (via CSS),
disegno vettoriale reportlab nei PDF, PNG per l'icona del browser
(`assets/logo-mark.png`, rigenerabile con `python -m portfolio_intelligence.ui.brand`).

Il simbolo è un rombo diviso in quattro facce attorno al centro: due blu
notte, una blu del marchio e una più chiara, come una gemma vista dall'alto.
"""

from pathlib import Path

NAVY = "#0B1F4D"
ACCENT = "#1E40AF"
LIGHT = "#4F7BE8"

# facce del rombo in coordinate 0-100: (punti, colore)
FACETS: tuple[tuple[tuple[tuple[float, float], ...], str], ...] = (
    (((50, 4), (50, 50), (4, 50)), NAVY),  # alto-sinistra
    (((50, 4), (96, 50), (50, 50)), ACCENT),  # alto-destra
    (((96, 50), (50, 96), (50, 50)), NAVY),  # basso-destra
    (((50, 96), (4, 50), (50, 50)), LIGHT),  # basso-sinistra
)

MARK_PNG = Path(__file__).resolve().parents[2] / "assets" / "logo-mark.png"


def mark_svg(size: int = 20) -> str:
    """Il simbolo come SVG in linea (nessuna risorsa esterna)."""
    polygons = "".join(
        f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}" fill="{color}"/>'
        for points, color in FACETS
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 100 100" role="img" aria-label="Smarteefinance">{polygons}</svg>'
    )


def mark_data_uri() -> str:
    """Il simbolo come data URI, per l'uso da CSS (background-image)."""
    from urllib.parse import quote

    return "data:image/svg+xml," + quote(mark_svg(100))


def mark_drawing(size: float):
    """Il simbolo come disegno vettoriale reportlab di lato `size` punti."""
    from reportlab.graphics.shapes import Drawing, Polygon
    from reportlab.lib import colors

    drawing = Drawing(size, size)
    scale = size / 100
    for points, color in FACETS:
        # reportlab ha l'asse y verso l'alto: si ribalta la geometria SVG
        coords = [c for x, y in points for c in (x * scale, (100 - y) * scale)]
        drawing.add(Polygon(coords, fillColor=colors.HexColor(color), strokeColor=None))
    return drawing


def page_icon() -> str:
    """Icona della scheda del browser: il PNG del simbolo se presente, altrimenti il rombo."""
    return str(MARK_PNG) if MARK_PNG.exists() else "◆"


def write_png(path: Path = MARK_PNG, size: int = 256) -> Path:
    """Rigenera il PNG del simbolo (sfondo trasparente) con Pillow."""
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 100
    for points, color in FACETS:
        draw.polygon([(x * scale, y * scale) for x, y in points], fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


if __name__ == "__main__":
    print(write_png())
