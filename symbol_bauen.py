"""Baut livescan.icns aus dem Symbol der Brickfolio-App.

    python3 symbol_bauen.py ~/dev/brickfolio/frontend/icons/icon-basis.png

Das Vorbild ist der gelbe Kachel mit dem Minifiguren-Kopf. Damit man den
Scanner davon unterscheidet und zugleich sieht, was er tut, kommt der
Rahmen dazu, den man um eine Figur zieht: vier Eckwinkel um den Kopf.

Ohne Fremdbibliotheken - PNG lesen und schreiben steht hier zu Fuss.
Pillow waere weniger Zeilen, aber eine Abhaengigkeit fuer eine Datei,
die sich fast nie aendert.
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

STRICH = 17.0          # so dick wie der Kopfumriss im Vorbild
ARM = 66.0             # Laenge eines Winkelschenkels
RAHMEN = (84, 112, 428, 400)   # links, oben, rechts, unten (auf 512)


def png_lesen(pfad):
    roh = open(pfad, "rb").read()
    i, daten, kopf = 8, b"", None
    while i < len(roh):
        laenge, art = struct.unpack(">I4s", roh[i:i + 8])
        inhalt = roh[i + 8:i + 8 + laenge]
        if art == b"IHDR":
            kopf = struct.unpack(">IIBBBBB", inhalt)
        elif art == b"IDAT":
            daten += inhalt
        i += 12 + laenge
    breite, hoehe, tiefe, farbart = kopf[0], kopf[1], kopf[2], kopf[3]
    if (tiefe, farbart) != (8, 6):
        raise SystemExit("Erwartet wird RGBA mit 8 Bit, nicht %s/%s"
                         % (tiefe, farbart))
    r = zlib.decompress(daten)
    schritt, k = breite * 4, 4
    zeilen, vor, p = [], bytearray(schritt), 0
    for _ in range(hoehe):
        f = r[p]; p += 1
        z = bytearray(r[p:p + schritt]); p += schritt
        for x in range(schritt):
            a = z[x - k] if x >= k else 0
            o = vor[x]
            c = vor[x - k] if x >= k else 0
            if f == 1:
                z[x] = (z[x] + a) & 255
            elif f == 2:
                z[x] = (z[x] + o) & 255
            elif f == 3:
                z[x] = (z[x] + (a + o) // 2) & 255
            elif f == 4:
                pp = a + o - c
                pa, pb, pc = abs(pp - a), abs(pp - o), abs(pp - c)
                z[x] = (z[x] + (a if pa <= pb and pa <= pc
                                else o if pb <= pc else c)) & 255
        zeilen.append(z); vor = z
    return breite, hoehe, zeilen


def png_schreiben(pfad, breite, hoehe, zeilen):
    roh = b"".join(b"\0" + bytes(z) for z in zeilen)
    def block(art, inhalt):
        return (struct.pack(">I", len(inhalt)) + art + inhalt
                + struct.pack(">I", zlib.crc32(art + inhalt) & 0xffffffff))
    with open(pfad, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(block(b"IHDR", struct.pack(">IIBBBBB", breite, hoehe, 8, 6, 0, 0, 0)))
        f.write(block(b"IDAT", zlib.compress(roh, 9)))
        f.write(block(b"IEND", b""))


def _abstand(px, py, ax, ay, bx, by):
    """Kuerzester Abstand eines Punktes zur Strecke a-b."""
    dx, dy = bx - ax, by - ay
    laenge = dx * dx + dy * dy
    t = 0.0 if laenge == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / laenge))
    ex, ey = ax + t * dx - px, ay + t * dy - py
    return (ex * ex + ey * ey) ** 0.5


def winkel_zeichnen(breite, hoehe, zeilen, farbe):
    l, o, r, u = RAHMEN
    strecken = []
    for (ex, ey, sx, sy) in ((l, o, 1, 1), (r, o, -1, 1),
                             (l, u, 1, -1), (r, u, -1, -1)):
        strecken.append((ex, ey, ex + sx * ARM, ey))       # waagerecht
        strecken.append((ex, ey, ex, ey + sy * ARM))       # senkrecht

    halb = STRICH / 2.0
    rand = int(halb + 2)
    for (ax, ay, bx, by) in strecken:
        for y in range(max(0, int(min(ay, by)) - rand),
                       min(hoehe, int(max(ay, by)) + rand + 1)):
            z = zeilen[y]
            for x in range(max(0, int(min(ax, bx)) - rand),
                           min(breite, int(max(ax, bx)) + rand + 1)):
                # Vier Unterproben je Pixel - reicht fuer weiche Kanten.
                deckung = 0.0
                for dy in (0.25, 0.75):
                    for dx in (0.25, 0.75):
                        d = _abstand(x + dx, y + dy, ax, ay, bx, by)
                        if d <= halb - 0.5:
                            deckung += 1.0
                        elif d < halb + 0.5:
                            deckung += halb + 0.5 - d
                deckung /= 4.0
                if deckung <= 0:
                    continue
                p = x * 4
                for kanal in range(3):
                    alt = z[p + kanal]
                    z[p + kanal] = int(alt + (farbe[kanal] - alt) * deckung + 0.5)
                z[p + 3] = max(z[p + 3], int(255 * deckung + 0.5))


def main(quelle):
    breite, hoehe, zeilen = png_lesen(quelle)
    if (breite, hoehe) != (512, 512):
        raise SystemExit("Die Masse sind auf 512x512 abgestimmt, nicht %dx%d"
                         % (breite, hoehe))
    # Schwarz aus dem Vorbild, nicht geraten.
    p = 200 * 4
    farbe = tuple(zeilen[215][p:p + 3])
    winkel_zeichnen(breite, hoehe, zeilen, farbe)

    with tempfile.TemporaryDirectory() as tmp:
        gross = os.path.join(tmp, "gross.png")
        png_schreiben(gross, breite, hoehe, zeilen)
        satz = os.path.join(tmp, "livescan.iconset")
        os.mkdir(satz)
        # 1024 laesst sich aus 512 nicht ehrlich gewinnen - also weglassen.
        for kante, name in ((16, "16x16"), (32, "16x16@2x"), (32, "32x32"),
                            (64, "32x32@2x"), (128, "128x128"),
                            (48, "48x48"), (256, "128x128@2x"),
                            (256, "256x256"),
                            (512, "256x256@2x"), (512, "512x512")):
            ziel = os.path.join(satz, "icon_%s.png" % name)
            subprocess.run(["sips", "-z", str(kante), str(kante), gross,
                            "--out", ziel], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["iconutil", "-c", "icns", satz,
                        "-o", "livescan.icns"], check=True)
        subprocess.run(["cp", gross, "symbol-vorschau.png"], check=True)
        ico_bauen(satz, "livescan.ico")
    print("livescan.icns und livescan.ico gebaut, "
          "Vorschau in symbol-vorschau.png")


def ico_bauen(satz, ziel):
    """Die Windows-Datei aus denselben Bildern.

    ICO ist ein kurzer Kopf und dahinter die Bilder. Seit Vista duerfen
    das PNGs sein - deshalb reicht Zusammenpacken, kein Umrechnen. Damit
    tragen Mac und Windows dasselbe Symbol, aus derselben Quelle.
    """
    kanten = (16, 32, 48, 64, 128, 256)
    bilder = []
    for kante in kanten:
        # 48 hat der Satz fuer macOS nicht - dann aus dem naechstgroesseren.
        for name in ("icon_%dx%d.png" % (kante, kante),
                     "icon_%dx%d@2x.png" % (kante // 2, kante // 2)):
            weg = os.path.join(satz, name)
            if os.path.exists(weg):
                with open(weg, "rb") as f:
                    bilder.append((kante, f.read()))
                break

    kopf = struct.pack("<HHH", 0, 1, len(bilder))
    eintraege, daten, versatz = b"", b"", 6 + 16 * len(bilder)
    for kante, inhalt in bilder:
        eintraege += struct.pack("<BBBBHHII",
                                 0 if kante >= 256 else kante,
                                 0 if kante >= 256 else kante,
                                 0, 0, 1, 32, len(inhalt), versatz)
        daten += inhalt
        versatz += len(inhalt)
    with open(ziel, "wb") as f:
        f.write(kopf + eintraege + daten)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else os.path.expanduser("~/dev/brickfolio/frontend/icons/icon-basis.png"))
