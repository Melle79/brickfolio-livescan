#!/bin/sh
# Sucht ein Python mit brauchbarem Tk und startet damit den Live-Scanner.
#
# **Warum das nötig ist:** In macOS steckt zwar ein Python (/usr/bin/python3),
# aber mit **Tk 8.5** – Apples altem, auf heutigem macOS kaputtem Bausatz.
# Damit kommt nur ein weißes Fenster, und PNG kann es auch nicht (das kam
# erst mit Tk 8.6), also gäbe es weder Vorschau noch Bereichsauswahl.
#
# Deshalb der Reihe nach durchprobieren und das erste nehmen, das Tk 8.6
# oder neuer hat.
set -eu

ORDNER="$(cd "$(dirname "$0")" && pwd)"

for P in \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /usr/bin/python3
do
    [ -x "$P" ] || continue
    if "$P" -c 'import sys, tkinter; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)' \
        >/dev/null 2>&1
    then
        exec "$P" "$ORDNER/livescan.py"
    fi
done

echo "Kein Python mit Tk 8.6 oder neuer gefunden." >&2
echo "Abhilfe:  brew install python-tk" >&2
exit 1
