#!/bin/sh
# Baut die App und unterschreibt sie.
#
# **Warum nicht ad hoc.** Eine Ad-hoc-Unterschrift hat als designierte
# Anforderung nur den Fingerabdruck des Programms - der aendert sich mit
# jedem Bau. macOS haelt die neue Fassung dann fuer eine fremde App und
# vergisst die Freigabe fuer die Bildschirmaufnahme; der Eintrag in den
# Systemeinstellungen bleibt stehen, gehoert aber zu nichts mehr.
#
# Mit einem gleichbleibenden Zertifikat lautet die Anforderung
# "identifier ... and certificate root = H'...'" und bleibt ueber
# Fassungen hinweg gleich. Die Freigabe ueberlebt damit das Update.
#
# Das Zertifikat ist selbst ausgestellt (kostenlos, im Anmeldeschluessel-
# bund). Gegen die Gatekeeper-Sperre beim Herunterladen hilft es nicht -
# dafuer braeuchte es ein Apple-Entwicklerkonto.
#
# Der Bau-Runner hat den privaten Schluessel nicht und unterschreibt
# deshalb weiter ad hoc. Wer die Freigabe behalten will, nimmt eine hier
# gebaute App.
set -e

PYTHON="${PYTHON:-.venv-bau/bin/python}"
IDENT="${BFLS_SIGNATUR:-Brickfolio Selbstsigniert}"
APP="dist/Brickfolio Live-Scanner.app"

"$PYTHON" setup.py py2app

if security find-certificate -c "$IDENT" >/dev/null 2>&1; then
    echo "Unterschrift mit »$IDENT«"
else
    echo "Zertifikat »$IDENT« liegt nicht im Schlüsselbund – ad hoc."
    IDENT="-"
fi
# **Von innen nach aussen, nicht mit --deep.** `--deep` prueft die
# eingebetteten Teile, bevor es sie neu unterschreibt - und bricht ab,
# sobald eines davon nicht streng gueltig ist (bei py2app kommt das vom
# Strippen). Es meldet den Abbruch, gibt aber trotzdem 0 zurueck und
# hinterlaesst die App **ad hoc**. Genau so ist 1.1.0 beinahe
# unsigniert ausgeliefert worden.
find "$APP" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
    | xargs -0 -n1 codesign --force --sign "$IDENT"
for teil in "$APP/Contents/MacOS/python" \
            "$APP/Contents/Frameworks/Python.framework/Versions/Current"; do
    [ -e "$teil" ] && codesign --force --sign "$IDENT" "$teil"
done
codesign --force --sign "$IDENT" "$APP"

echo "Designierte Anforderung:"
codesign -d -r- "$APP" 2>&1 | grep designated

# **Nachsehen, nicht hoffen.** Ohne diese Wache faellt ein gescheitertes
# Unterschreiben nicht auf: Die App laeuft ja, sie ist nur ad hoc - und
# das merkt man erst, wenn die Freigabe fuer die Bildschirmaufnahme beim
# naechsten Update wieder weg ist.
if [ "$IDENT" != "-" ]; then
    if ! codesign -d -r- "$APP" 2>&1 | grep -q "certificate root"; then
        echo "FEHLER: Das Bündel trägt nicht das Zertifikat, sondern nur" >&2
        echo "        einen Fingerabdruck. So darf es nicht hinaus." >&2
        exit 1
    fi
    codesign --verify --strict "$APP" || {
        echo "FEHLER: Die Unterschrift validiert nicht." >&2
        exit 1
    }
fi
