"""Prueft, ob die gebaute .app wirklich hochkommt.

    python3 pruefe_buendel.py "dist/Brickfolio Live-Scanner.app"

**Warum es diese Datei gibt.** Der naheliegende Test ist "Prozess laeuft
nach zehn Sekunden noch" - und der ist wertlos: py2app faengt einen
Startfehler ab und zeigt einen Dialog. Der Prozess lebt dann munter
weiter, waehrend der Anwender "Launch error" liest. Genau so ist am
30.08.2026 ein Buendel als heil durchgegangen, dem die Skript-
Bibliothek von Tcl fehlte.

Deshalb wird hier die Ausgabe gelesen: Eine Rueckverfolgung oder ein
"Launch error" laesst die Pruefung durchfallen.

Nicht zwei Pruefungen gleichzeitig laufen lassen: Ein zweiter Start
desselben Buendels beendet sich sofort mit 0, und das sieht hier wie
ein Fehlschlag aus.
"""
import fcntl
import os
import signal
import subprocess
import sys
import time

WARTEN = 12

# **Verlangt wird Stille, nicht die Abwesenheit bekannter Woerter.** Am
# 04.09.2026 ist ein Buendel hier als heil durchgegangen, das Python gar
# nicht laden konnte: dyld schrieb seitenlang "code signature ... not valid
# for use in process", und keines der gesuchten Woerter kam darin vor. Eine
# Liste verdaechtiger Woerter kennt immer nur die Fehler von gestern.
#
# Eine heile App sagt beim Start nichts. Also ist jede Ausgabe ein Grund
# zum Hinsehen - lieber einmal zu viel als noch so ein Durchrutscher.


def main(app):
    exe = os.path.join(app, "Contents", "MacOS", os.path.basename(app)[:-4])
    if not os.path.exists(exe):
        print("Starter nicht gefunden:", exe)
        return 1

    # **Das Wichtigste zuerst, und zwar als Dateiprobe.** Fehlt die
    # Skript-Bibliothek von Tcl im Buendel, faellt Tcl auf den
    # einkompilierten Homebrew-Pfad zurueck. Den gibt es auf jeder
    # Maschine, die das Buendel baut oder prueft - und genau deshalb kann
    # *kein* Startversuch diesen Mangel aufdecken. Er zeigt sich erst beim
    # Anwender, der kein Homebrew hat oder eine andere Fassung. Also wird
    # hier nachgesehen statt ausprobiert.
    fehlt = [w for w in ("lib/tcl9.0/init.tcl", "lib/tk9.0/tk.tcl")
             if not os.path.exists(os.path.join(app, "Contents/Resources", w))]
    if fehlt:
        print("FEHL: im Buendel fehlt:", ", ".join(fehlt))
        print("      Ohne das startet die App nur dort, wo Homebrew-Tcl liegt.")
        return 1

    # Laeuft schon eine Instanz, beendet sich die zweite sofort mit 0 -
    # und das sieht hier wie ein Absturz aus. Zweimal heute darauf
    # hereingefallen; jetzt sagt es, was los ist, statt Alarm zu schlagen.
    laeuft = subprocess.run(["pgrep", "-f", os.path.basename(exe)],
                            capture_output=True, text=True)
    if laeuft.stdout.strip():
        print("FEHL: es laeuft schon eine Instanz (PID %s)."
              % laeuft.stdout.split()[0])
        print("      Erst beenden, sonst misst diese Pruefung nichts.")
        return 1

    umgebung = dict(os.environ)

    p = subprocess.Popen([exe], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, env=umgebung)
    fd = p.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL,
                fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)

    gesammelt = ""
    for _ in range(WARTEN):
        time.sleep(1)
        try:
            gesammelt += p.stdout.read() or ""
        except (BlockingIOError, TypeError):
            pass
        if p.poll() is not None:
            break

    lebt = p.poll() is None
    if lebt:
        p.send_signal(signal.SIGTERM)
        time.sleep(1)
        if p.poll() is None:
            p.kill()

    if gesammelt.strip():
        print("--- Ausgabe der App ---")
        print(gesammelt.strip()[-3000:])

    if not lebt:
        print("FEHL: die App ist gestorben (Rueckgabe %s)" % p.returncode)
        return 1
    if gesammelt.strip():
        print("FEHL: die App meldet beim Start etwas - siehe oben.")
        print("      Eine heile App sagt hier nichts.")
        return 1
    print("ok   die App kommt hoch und meldet nichts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "dist/Brickfolio Live-Scanner.app"))
