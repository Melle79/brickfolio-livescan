# Fremde Bestandteile

Dieses Programm liefert Software Dritter mit. Hier steht, welche und
unter welchen Bedingungen.

## cloudflared

**Wozu.** Steht eine Brickfolio-Instanz hinter Cloudflare Access, öffnet
`cloudflared` den Browser für die Anmeldung und hält danach die Sitzung
bereit. Ohne das müsste man es selbst installieren – und genau das soll
niemand müssen.

**Herkunft.** <https://github.com/cloudflare/cloudflared>
**Lizenz.** Apache License 2.0

    Copyright Cloudflare, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
    implied. See the License for the specific language governing
    permissions and limitations under the License.

Der Vollständigkeit halber: Das Programm wird **unverändert**
mitgeliefert, so wie es von Cloudflare bezogen wurde.

## Pillow – nur in der Windows-Fassung

**Wozu.** Bildschirmaufnahme, Skalieren und Bildwandlung. Auf dem Mac
erledigen `screencapture` und `sips` das, dort reist Pillow nicht mit.

**Herkunft.** <https://python-pillow.org>
**Lizenz.** MIT-CMU

## Python und Tcl/Tk

Beide stecken im Bündel, damit nichts vorinstalliert sein muss.

- Python – <https://www.python.org> – PSF License
- Tcl/Tk – <https://www.tcl-lang.org> – BSD-artige Lizenz
