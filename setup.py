"""Bündelt den Live-Scanner zu einer eigenständigen Mac-App.

    python3 -m pip install py2app
    python3 setup.py py2app

Danach liegt `dist/Brickfolio Live-Scanner.app` – mit Python und Tk darin.
Wer sie herunterlädt, braucht nichts weiter installiert zu haben.

**Warum gebündelt und nicht als Skript-Starter.** Vorher war es ein
AppleScript-Häppchen mit dem festen Pfad `/Users/nutzer/dev/…` und der
Annahme, es liege ein Python mit brauchbarem Tk herum. Das macOS-eigene
Python bringt ein zu altes Tk mit und zeichnet nur ein weißes Fenster –
also lief es genau auf einem Rechner.
"""
import os
import pathlib
import re

from setuptools import setup

# Aus livescan.py *gelesen*, nicht importiert: ein Import zöge tkinter mit,
# und py2app soll setup.py auch dort ausführen können, wo kein Tk steht.
def _tcl_bibliotheken():
    """Die beiden Skript-Ordner von Tcl und Tk, oder ein klarer Abbruch.

    Lieber hier laut scheitern als ein Buendel ausliefern, das nur auf
    Rechnern mit Homebrew-Tcl startet.
    """
    stamm = "/opt/homebrew/opt/tcl-tk/lib"
    ordner = [os.path.join(stamm, n) for n in ("tcl9.0", "tk9.0")]
    fehlt = [o for o in ordner if not os.path.isdir(o)]
    if fehlt:
        raise SystemExit(
            "Die Skript-Bibliothek von Tcl/Tk fehlt: %s\n"
            "Abhilfe:  brew install tcl-tk python-tk" % ", ".join(fehlt))
    return ordner


VERSION = re.search(r'^VERSION = "([^"]+)"',
                    pathlib.Path("livescan.py").read_text(),
                    re.M).group(1)

setup(
    app=["livescan.py"],
    # Die Skript-Bibliothek von Tcl/Tk. Ohne sie startet das Buendel auf
    # einem fremden Mac nicht ("Cannot find a usable init.tcl") - py2app
    # nimmt nur die .dylib mit, nicht die .tcl-Dateien daneben.
    # livescan.py zeigt beim Start per TCL_LIBRARY/TK_LIBRARY hierher.
    # Das Handbuch reist mit: Der Hilfe-Eintrag im Menue oeffnet es, und
    # das soll auch ohne Netz und ohne Zugang zum privaten Repo gehen.
    data_files=[("lib", _tcl_bibliotheken()), ("", ["README.md"])],
    options={"py2app": {
        "iconfile": "livescan.icns",
        # Tkinter kommt nicht von allein mit – py2app findet es nur, wenn
        # es ausdrücklich dabeisteht.
        "packages": ["tkinter"],
        "includes": ["queue", "json", "urllib.request", "ssl"],
        # **Ballast, den py2app von allein einpackt.** setup_requires zieht
        # setuptools in die Abhaengigkeitssuche, setuptools importiert
        # test.support - und schon liegen die Testdaten der Standard-
        # bibliothek (decimaltestdata, certdata, cjkencodings) im Buendel:
        # allein 2,8 MB von 6,8 MB des Archivs. Der Scanner benutzt nichts
        # davon; er kommt mit reiner Standardbibliothek aus.
        "excludes": [
            "test", "setuptools", "pkg_resources", "distutils",
            "_distutils_hack", "packaging", "wheel", "pydoc_data",
        ],
        # Der Scanner liegt über anderen Fenstern und hat kein Dock-Symbol
        # nötig? Doch – man will ihn wiederfinden. Also normale App.
        "plist": {
            "CFBundleName": "Brickfolio Live-Scanner",
            "CFBundleDisplayName": "Brickfolio Live-Scanner",
            "CFBundleIdentifier": "cc.brickfolio.livescan",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHumanReadableCopyright": "Melle79 – MIT-Lizenz",
            # Ohne diese Zeile fragt macOS beim ersten Bildschirmfoto
            # nicht, sondern liefert stumm ein schwarzes Bild.
            "NSAppleEventsUsageDescription":
                "Der Scanner nimmt einen Ausschnitt des Bildschirms auf.",
            "LSMinimumSystemVersion": "12.0",
        },
    }},
    setup_requires=["py2app"],
)
