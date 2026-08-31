"""Prüft, ob die gebaute Windows-Fassung hochkommt.

Dasselbe Anliegen wie `pruefe_buendel.py` auf dem Mac, nur für den Ordner
aus PyInstaller: Ein Startfehler zeigt sich sonst erst beim Anwender.

**„Prozess lebt noch" allein genügt nicht** – ein Tk-Programm mit einem
Fehlerdialog lebt auch. Deshalb wird die Ausgabe gelesen.
"""
import os
import subprocess
import sys
import time

ORDNER = os.path.join("dist", "Brickfolio Live-Scanner")
EXE = os.path.join(ORDNER, "Brickfolio Live-Scanner.exe")
VERDAECHTIG = ("Traceback", "ModuleNotFoundError", "ImportError",
               "Failed to execute")


def main():
    if not os.path.exists(EXE):
        print("FEHL: nicht gebaut:", EXE)
        return 1

    # Das Handbuch muss mit - sonst zeigt die Hilfe ins Leere.
    handbuch = os.path.join(ORDNER, "_internal", "README.md")
    if not os.path.exists(handbuch):
        handbuch = os.path.join(ORDNER, "README.md")
    if not os.path.exists(handbuch):
        print("FEHL: das Handbuch fehlt im Ordner")
        return 1

    # cloudflared muss mitreisen – sonst steht der Anwender vor dem Knopf
    # und soll etwas nachinstallieren, was gerade vermieden werden sollte.
    dabei = [os.path.join(ORDNER, "_internal", "cloudflared.exe"),
             os.path.join(ORDNER, "cloudflared.exe")]
    if not any(os.path.exists(d) for d in dabei):
        print("FEHL: cloudflared.exe fehlt im Ordner")
        return 1

    p = subprocess.Popen([EXE], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    time.sleep(15)
    lebt = p.poll() is None
    if lebt:
        p.terminate()
        time.sleep(2)
        if p.poll() is None:
            p.kill()
        ausgabe = ""
    else:
        ausgabe = p.stdout.read() or ""

    if ausgabe.strip():
        print("--- Ausgabe ---")
        print(ausgabe[-3000:])
    if not lebt:
        print("FEHL: gestorben, Rückgabe", p.returncode)
        return 1
    schlimm = [w for w in VERDAECHTIG if w in ausgabe]
    if schlimm:
        print("FEHL: meldet beim Start:", ", ".join(schlimm))
        return 1
    print("ok   die Windows-Fassung kommt hoch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
