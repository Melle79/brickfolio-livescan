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
codesign --force --deep --sign "$IDENT" "$APP"

echo "Designierte Anforderung:"
codesign -d -r- "$APP" 2>&1 | grep designated
