"""Ein Bildschirmfoto des Scanners mit einer Beispielfigur – ohne Instanz.

Wozu: Wie die selbst gezeichneten Knöpfe unter **Windows** aussehen, lässt
sich vom Mac aus nicht prüfen. Der Bau-Runner führt dieses Skript aus und
legt das Bild als Artefakt ab; auf dem Mac geht es genauso.

    python ansicht.py ansicht.png

An die Stelle der Instanz tritt eine Attrappe: keine Anmeldung, keine
Anfrage, keine Datei außerhalb eines Wegwerf-Ordners.
"""
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk

import livescan

ZIEL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "ansicht.png")
ORDNER = tempfile.mkdtemp(prefix="livescan-ansicht-")
livescan.EINSTELLUNGEN = os.path.join(ORDNER, "einstellungen.json")
livescan.VERLAUF_DATEI = os.path.join(ORDNER, "verlauf.json")
with open(livescan.EINSTELLUNGEN, "w") as f:
    json.dump({"updates_pruefen": False, "adresse": "http://example.invalid",
               "token": "attrappe", "bereich": [100, 100, 400, 400]}, f)
livescan.ton_spielen = lambda datei=None: None

INFO = {
    "sw0188": {"owned": 1, "year": 2007, "new": 5.95, "used": 3.70,
               "all_sets": [{"no": "10188-1", "name": "Death Star - UCS"}]},
    "sw0036": {"wanted": True, "year": 2001, "new": 13.59, "used": 6.18},
}


class Attrappe:
    token = "attrappe"
    adresse = "http://example.invalid"
    katalogbild = lambda self, adresse: None
    sets_der_figur = lambda self, nummer: []

    def listen(self):
        return [{"id": 1, "name": "Flohmarkt"}]

    def infos(self, artikel, bei_bricklink=False):
        return {t["item_id"]: dict(INFO.get(t["item_id"], {}))
                for t in artikel}


def knipsen(wurzel):
    wurzel.update_idletasks()
    x, y = wurzel.winfo_rootx(), wurzel.winfo_rooty()
    b, h = wurzel.winfo_width(), wurzel.winfo_height()
    if livescan.IST_WINDOWS:
        from PIL import ImageGrab
        ImageGrab.grab(bbox=(x, y, x + b, y + h), all_screens=True).save(ZIEL)
    else:
        subprocess.run(["screencapture", "-x", "-R",
                        f"{x},{y},{b},{h}", ZIEL])
    print("Bild:", ZIEL, f"({b}×{h})")
    wurzel.destroy()


def main():
    livescan.windows_dpi_beachten()
    wurzel = tk.Tk()
    if livescan.IST_WINDOWS:
        wurzel.tk.call("tk", "scaling", wurzel.winfo_fpixels("1i") / 72.0)
    app = livescan.LiveScanner(wurzel)
    app.instanz = Attrappe()
    app.listen_laden()
    wurzel.geometry("+40+40")
    wurzel.attributes("-topmost", True)

    def zeigen():
        app._kandidaten_zeigen([
            {"item_id": "sw0188", "item_type": "minifig", "score": 78,
             "name": "Imperial Stormtrooper - Black Head, Dotted Mouth Helmet",
             "img_url": "", "_info": dict(INFO["sw0188"])},
            {"item_id": "sw0036", "item_type": "minifig", "score": 62,
             "name": "Imperial Stormtrooper - Yellow Head", "img_url": "",
             "_info": dict(INFO["sw0036"])},
        ])

    wurzel.after(400, zeigen)
    wurzel.after(2500, lambda: knipsen(wurzel))
    wurzel.mainloop()


if __name__ == "__main__":
    main()
