#!/usr/bin/env python3
"""Prüfung des Live-Scanners – am verborgenen Fenster, ohne Netz.

    /opt/homebrew/bin/python3 pruefung.py

Es wird **kein** Bildschirmfoto gemacht, **keine** Anfrage an die Instanz
geschickt und **nicht** in die echten Einstellungen geschrieben: Statt der
Instanz steht eine Attrappe, statt der Abzüge ein Drehbuch, und die beiden
Dateien zeigen ins Temp-Verzeichnis.

Warum am verborgenen Fenster und nicht über `start.sh`: Das echte Fenster
legt sich über alles und blockiert. Zwei Fallstricke dabei, die schon zweimal
für Fehlalarm gesorgt haben:

* `event_generate("<<ListboxSelect>>")` kommt am verborgenen Fenster nicht an –
  die Behandlung wird direkt aufgerufen.
* Alles aus den Hintergrundfäden geht über `self.post` und wird per
  `after(120, …)` abgeholt. `update()` lässt diese Zeit **nicht** vergehen;
  dafür ist `takt()` da.
"""
import base64
import json
import os
import pathlib
import queue
import sys
import tempfile
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import livescan

ORDNER = tempfile.mkdtemp(prefix="livescan-pruefung-")
livescan.EINSTELLUNGEN = os.path.join(ORDNER, "einstellungen.json")
livescan.VERLAUF_DATEI = os.path.join(ORDNER, "verlauf.json")
livescan.WUNSCH_TAKT = 15            # nicht zwei Sekunden warten

# Ein winziges, echtes PNG – die Vorschau soll etwas zu tun bekommen.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg==")

def bild(nummer):
    """Ein echtes, aber unterscheidbares PNG – Tk muss es laden koennen,
    sonst entstehen keine Daumennaegel und der Test prueft ins Leere."""
    return PNG + b"\x00" * nummer

toene = []
livescan.ton_spielen = lambda datei=None: toene.append("ton")

bestand = {}          # was die Attrappe auf `infos` antwortet
erkannt = {"items": []}
geschickt = []


class Attrappe:
    """Die Instanz, ohne eine einzige Anfrage."""
    token = "attrappe"
    adresse = "http://example.invalid"
    katalogbild = lambda self, a: None
    sets_der_figur = lambda self, i: []
    listen = lambda self: []
    infos = lambda self, a, bei_bricklink=False: dict(bestand)

    def erkennen(self, bild):
        geschickt.append(bild)
        return {"items": [dict(t) for t in erkannt["items"]]}

    def nummer_suchen(self, nummer):
        katalog = {
            "sw0011": ("minifig", "Chewbacca"),
            "75192": ("set", "Millennium Falcon"),
        }
        if nummer not in katalog:
            return []
        typ, name = katalog[nummer]
        return [{"item_id": nummer, "item_type": typ, "name": name,
                 "img_url": "", "bricklink_url": "", "score": 100}]

    def in_sammlung(self, *a, **k):
        raise AssertionError("es wurde ungefragt gebucht!")
    auf_wunschliste = auf_liste = in_sammlung


def artikel(nr, punkte, name, typ="minifig", **info):
    return {"item_id": nr, "item_type": typ, "score": punkte, "name": name,
            "img_url": "", "_info": dict(info)}


# ----------------------------------------------------------- Prüfgerüst
bilanz = {"gut": 0, "schlecht": 0}


def abschnitt(titel):
    print("\n\033[1m%s\033[0m" % titel)


def pruefe(bedingung, text):
    bilanz["gut" if bedingung else "schlecht"] += 1
    print(("   ok   " if bedingung else "  FEHL  ") + text)
    assert bedingung, text


def fenster():
    w = tk.Tk()
    w.withdraw()
    a = livescan.LiveScanner(w)
    a.instanz = Attrappe()
    return w, a


def takt(w, ms=250):
    """Zeit wirklich vergehen lassen – `update()` genügt nicht."""
    w.after(ms, w.quit)
    w.mainloop()


def trennen(app):
    """Den nächsten Scan als neuen Artikel gelten lassen.

    Sonst zieht das Programm zusammen, was hier zwei unabhängige Prüfungen
    sein sollen – sobald sich die Vorschläge überschneiden, ist es für den
    Scanner dieselbe Figur aus einem anderen Winkel. Das ist gewolltes
    Verhalten; hier wird nur der Zeitablauf vorgespult.
    """
    if app.verlauf_daten and app.verlauf_daten[0]:
        app.verlauf_daten[0]["zeit"] = 0


# ============================================================ 1. Rennen
abschnitt("1. Verspätete Antworten überschreiben die Karte nicht")
wurzel, app = fenster()

app._kandidaten_zeigen([artikel("11833", 61, "Plate, Round 4 x 4", "part")])
takt(wurzel)
platte = app.kandidaten[0]
app._kandidaten_zeigen([artikel("sw0579", 92, "General Veers")])
takt(wurzel)
platte["_info"] = {"used": 0.07}
app.post.put(("fuer", (platte, "treffer", platte)))
takt(wurzel)
pruefe(app.name.cget("text") == "General Veers",
       "die Karte gehört weiter zum neuen Scan")
pruefe(app.treffer["item_id"] == "sw0579",
       "und gebucht würde der neue, nicht der alte")

app.treffer["_info"] = {"used": 7.25}
app.post.put(("fuer", (app.treffer, "treffer", app.treffer)))
takt(wurzel)
pruefe("7.25" in app.unter.cget("text"),
       "der Preis für den aktuellen Treffer kommt aber an")

# ==================================================== 2. Ansichten vereinen
abschnitt("2. Drehscheibe: Ansichten werden vereint")
wurzel.destroy()
os.remove(livescan.VERLAUF_DATEI)
wurzel, app = fenster()

app.letztes_bild = bild(1)
app._kandidaten_zeigen([artikel("sw0417", 71, "Mace Windu"),
                        artikel("11833", 64, "Ständer", "part")])
takt(wurzel)
pruefe(app.verlauf.size() == 1, "eine Zeile")

# Die Scheibe dreht sich: andere Quoten, ein neuer Vorschlag, Überschneidung
app.letztes_bild = bild(2)
app._kandidaten_zeigen([artikel("sw0417", 78, "Mace Windu"),
                        artikel("sw0056", 55, "Mace Windu Ep2")])
takt(wurzel)
print("     Liste:", [app.liste.get(i) for i in range(app.liste.size())])
pruefe(app.verlauf.size() == 1, "immer noch eine Verlaufszeile")
pruefe("⟳2" in app.verlauf.get(0), "mit der Zahl der Ansichten")
pruefe(app.liste.size() == 3, "alle Vorschläge beider Ansichten stehen da")
pruefe(app.kandidaten[0]["item_id"] == "sw0417",
       "die zweimal gesehene Figur steht oben")
pruefe(app.kandidaten[0]["score"] == 78, "mit ihrer besten Quote")
pruefe("(2×)" in app.liste.get(0), "und der Zahl der Ansichten in der Zeile")
pruefe(app.bilder == [bild(1), bild(2)],
       "beide Aufnahmen werden aufgehoben")
pruefe(app.bilder_an == {1},
       "vorgewählt ist die Ansicht, die den besten Treffer lieferte")
pruefe(app.ansichtsreihe.winfo_manager() == "pack"
       and len(app._mini_rahmen) == 2,
       "und die Reihe zeigt beide zum Aussuchen")

# Dritte Ansicht, in der die Figur schlechter erkannt wird
app.letztes_bild = bild(3)
app._kandidaten_zeigen([artikel("sw0417", 60, "Mace Windu")])
takt(wurzel)
pruefe(app.kandidaten[0]["score"] == 78, "die beste Quote bleibt die beste")
pruefe(app.kandidaten[0]["_ansichten"] == 3, "dreimal gesehen")
pruefe(len(app.bilder) == 3, "alle drei Aufnahmen liegen bereit")
pruefe(app.bilder_an == {1},
       "die Vorwahl wechselt nicht auf die schlechtere Ansicht")
pruefe(app.letztes_bild == bild(2), "und die Vorschau zeigt die gewählte")

# Von Hand aussuchen – auch mehrere.
app._ansicht_umschalten(2)
pruefe(app.bilder_an == {1, 2}, "ein Klick nimmt eine zweite Ansicht dazu")
pruefe(app.letztes_bild == bild(3), "und zeigt sie groß")
app._ansicht_umschalten(1)
pruefe(app.bilder_an == {2}, "noch ein Klick nimmt die erste wieder heraus")
app._ansicht_umschalten(0)
pruefe(app.bilder_an == {0, 2}, "aussuchen geht in beide Richtungen")
print("     Beschriftung:", app.ansichtstext.cget("text"))
pruefe("2 von 3" in app.ansichtstext.cget("text"),
       "die Reihe sagt in Worten, wie viele angehängt werden")
app.bilder_an.clear()
app._ansichten_faerben()
pruefe("kein Foto" in app.ansichtstext.cget("text"),
       "und sagt es auch, wenn keines ausgesucht ist")
app.bilder_an.add(1)
app._ansichten_faerben()

# Von Hand nachgeschoben, eine Minute später: Rahmen ziehen dauert, und die
# 25 Sekunden für den Wächter reichen dafür nicht.
app.auto_lauf = True                     # die Ansichten kamen vom Wächter
app.eintrag["auto"] = True
app.eintrag["zeit"] = time.time() - 60
zeilen_davor = app.verlauf.size()
app.auto_lauf = False                    # jetzt löst der Mensch aus
app.letztes_bild = bild(4)
app._kandidaten_zeigen([artikel("sw0417", 89, "Mace Windu")])
takt(wurzel)
print("     Verlauf:", app.verlauf.get(0))
pruefe(app.verlauf.size() == zeilen_davor,
       "die eigene Aufnahme zählt zur selben Figur, auch nach einer Minute")
pruefe("⟳4" in app.verlauf.get(0), "und wird mitgezählt")
pruefe(app.verlauf.get(0).count("⏱") == 1,
       "das ⏱ bleibt – eine der Ansichten kam ja vom Wächter")

# Auch der Wächter zählt nach einer Pause weiter mit: Nach vier Ansichten
# macht er von sich aus Halt, und bis sich wieder etwas tut, vergeht Zeit.
app.auto_lauf = True
app.eintrag["zeit"] = time.time() - 90
zeilen_davor = app.verlauf.size()
app._kandidaten_zeigen([artikel("sw0417", 70, "Mace Windu")])
takt(wurzel)
pruefe(app.verlauf.size() == zeilen_davor,
       "auch nach anderthalb Minuten Pause bleibt es dieselbe Figur")

# Irgendwann ist es aber eine neue Begegnung.
app.eintrag["zeit"] = time.time() - livescan.ANSICHT_FENSTER - 5
zeilen_davor = app.verlauf.size()
app._kandidaten_zeigen([artikel("sw0417", 70, "Mace Windu")])
takt(wurzel)
pruefe(app.verlauf.size() == zeilen_davor + 1,
       "nach %.0f Minuten fängt eine neue Zeile an"
       % (livescan.ANSICHT_FENSTER / 60))
app.auto_lauf = False

# Viele Ansichten: Es werden nur so viele gehalten, wie auch gezeigt werden –
# sonst fiele die Vorauswahl auf ein Bild, das man nie zu sehen bekommt.
gewaehlt_vorher = set(app.bilder_an)
app.bilder_an.clear()
app.bilder_an.add(0)                    # die erste ausdrücklich behalten
erstes = app.bilder[0]
for n in range(5, 12):
    app.letztes_bild = bild(n)
    app._kandidaten_zeigen([artikel("sw0417", 70, "Mace Windu")])
takt(wurzel)
print("     Aufnahmen:", len(app.bilder), "· gezeigt:", len(app._mini_rahmen),
      "· gewählt:", app.bilder_an)
pruefe(len(app.bilder) == livescan.MINI_HOECHSTENS,
       "höchstens %d Aufnahmen werden gehalten" % livescan.MINI_HOECHSTENS)
pruefe(len(app._mini_rahmen) == len(app.bilder),
       "und alle davon stehen zum Aussuchen da")
pruefe(all(i < len(app.bilder) for i in app.bilder_an),
       "die Auswahl zeigt auf ein Bild, das es noch gibt")
pruefe(erstes in app.bilder,
       "die ausgesuchte Aufnahme überlebt, verworfen wird eine ungewählte")

# Etwas völlig anderes: keine Überschneidung -> neue Zeile
zeilen_davor = app.verlauf.size()
app._kandidaten_zeigen([artikel("sw0900", 88, "Ganz andere Figur")])
takt(wurzel)
pruefe(app.verlauf.size() == zeilen_davor + 1,
       "ohne Überschneidung fängt eine neue Zeile an")

# ================================================ 3. Auswahl festhalten
abschnitt("3. Eine neue Ansicht reißt die Auswahl nicht weg")
app._kandidaten_zeigen([artikel("sw0100", 90, "Erster"),
                        artikel("sw0101", 60, "Zweiter")])
takt(wurzel)
app.liste.selection_clear(0, "end")
app.liste.selection_set(1)
app._auswahl_geaendert()                 # am verborgenen Fenster direkt
takt(wurzel)
pruefe(app.treffer["item_id"] == "sw0101", "von Hand auf den zweiten gestellt")

app._kandidaten_zeigen([artikel("sw0100", 95, "Erster"),
                        artikel("sw0102", 70, "Dritter")])
takt(wurzel)
print("     Liste:", [app.liste.get(i)[:28] for i in range(app.liste.size())])
pruefe(app.treffer["item_id"] == "sw0101",
       "nach der nächsten Ansicht steht die Wahl unverändert")
pruefe(app.liste.get(app.liste.curselection()[0]).find("sw0101") > 0,
       "und die Markierung ist mitgewandert")

# ==================================================== 4. Wunschliste
abschnitt("4. Wunschliste: Blinken und Ton")
toene.clear()
app._kandidaten_zeigen([artikel("sw0500", 88, "Wunschfigur", wanted=1)])
takt(wurzel, 30)
pruefe(len(toene) == 1, "es klingt")
pruefe(app._blinkt is not None, "und blinkt")
farben = set()
for _ in range(6):
    takt(wurzel, 25)
    farben.add(app.rahmen.cget("background"))
pruefe(livescan.WUNSCH_AN in farben, "in der Wunschfarbe")
takt(wurzel, 300)
pruefe(app._blinkt is None, "danach hört es auf")
pruefe(app.liste.get(0).startswith("☆"), "die Zeile trägt das ☆")

# Weitere Ansicht derselben Figur: still, der Wunsch ist nicht neu
toene.clear()
app._kandidaten_zeigen([artikel("sw0500", 80, "Wunschfigur", wanted=1)])
takt(wurzel, 30)
pruefe(toene == [], "die nächste Ansicht bleibt still")
pruefe(app._blinkt is None, "und dunkel")

# Ein Wunsch, der erst in der zweiten Ansicht auftaucht: klingt
toene.clear()
app._kandidaten_zeigen([artikel("sw0500", 80, "Wunschfigur", wanted=1),
                        artikel("sw0501", 62, "Neuer Wunsch", wanted=1)])
takt(wurzel, 30)
pruefe(len(toene) == 1, "ein neu hinzugekommener Wunsch klingt sehr wohl")

# ============================================ 5. Nummer nachtragen
abschnitt("5. Nummer nachtragen – des Anwenders Chewbacca")
app._kandidaten_zeigen([artikel("11833", 62, "Plate, Round 4 x 4", "part"),
                        artikel("60474", 59, "Plate mit Loch", "part")])
takt(wurzel)
app.nummerfeld.delete(0, "end")
app.nummerfeld.insert(0, "sw0011")
app.nummer_suchen()
takt(wurzel)
print("     Liste:", [app.liste.get(i)[:30] for i in range(app.liste.size())])
pruefe(app.liste.size() == 3, "die Vorschläge bleiben stehen")
pruefe(app.treffer["item_id"] == "sw0011", "die getippte Figur ist gewählt")
pruefe("✎" in app.liste.get(app.liste.curselection()[0]),
       "sie trägt ein ✎ statt einer Trefferquote")
pruefe("von Hand eingetragen" in app.unter.cget("text"),
       "auch die Karte sagt es")

# ============================================== 6. Nur Figuren
abschnitt("6. Haken »Nur Figuren«")
trennen(app)          # sonst vereint er es mit dem Chewbacca von eben
erkannt = {"items": [artikel("11833", 62, "Platte", "part"),
                     artikel("sw0011", 55, "Chewbacca"),
                     artikel("75192", 40, "Falcon", "set")]}
app.nur_figuren.set(False)
app._ausloesen(lambda: PNG)
takt(wurzel, 350)
pruefe(app.liste.size() == 3, "ohne Haken kommen alle drei Arten")

app.nur_figuren.set(True)
trennen(app)
app._ausloesen(lambda: PNG)
takt(wurzel, 350)
pruefe(app.liste.size() == 1, "mit Haken nur die Figur")

erkannt = {"items": [artikel("11833", 62, "Platte", "part"),
                     artikel("60474", 59, "Platte mit Loch", "part")]}
app._treffer_leeren()      # ohne bestehenden Treffer – der Fall steht in 8b
app._ausloesen(lambda: PNG)
takt(wurzel, 350)
print("     Meldung:", app.stand.cget("text"))
pruefe(app.liste.size() == 0, "wird alles aussortiert, bleibt die Liste leer")
pruefe("alle 2 Vorschläge waren Sets oder Teile" in app.stand.cget("text"),
       "und es wird gesagt, wie viel weggefiltert wurde")
pruefe("Nichts erkannt" not in app.stand.cget("text"),
       "nicht behauptet, es sei nichts erkannt worden")
app.nur_figuren.set(False)

# ====================================== 7. Rücksprung im Verlauf
abschnitt("7. Rücksprung im Verlauf")
app.letztes_bild = b"altes-bild"
app._kandidaten_zeigen([artikel("sw0700", 77, "Alte Figur"),
                        artikel("sw0701", 71, "Alte Variante")])
takt(wurzel)
app.liste.selection_clear(0, "end")
app.liste.selection_set(1)
app._auswahl_geaendert()
takt(wurzel)
app.letztes_bild = b"neues-bild"
app._kandidaten_zeigen([artikel("sw0800", 92, "Neue Figur")])
takt(wurzel)

bestand = {"sw0701": {"owned": 1}}
app.verlauf.selection_clear(0, "end")
app.verlauf.selection_set(1)
app._verlauf_geklickt()
takt(wurzel)
print("     Karte:", app.name.cget("text"), "|", app.stand.cget("text")[:40])
pruefe(app.treffer["item_id"] == "sw0701", "die gewählte Variante ist zurück")
pruefe(app.letztes_bild == b"altes-bild", "samt der Aufnahme von damals")
pruefe(app.stand.cget("text").startswith("↩"), "mit Hinweis auf die Vergangenheit")
pruefe("1×" in app.besitz.cget("text"),
       "und der Bestand wurde frisch geholt")
bestand = {}

# ============================== 8. Verlauf über den Neustart
abschnitt("8. Der Verlauf übersteht das Schließen")
gemerkt = [app.verlauf.get(i) for i in range(app.verlauf.size())]
wurzel.destroy()
roh = open(livescan.VERLAUF_DATEI).read()
pruefe("altes-bild" not in roh and "neues-bild" not in roh,
       "keine Aufnahme steht in der Datei")
pruefe(oct(os.stat(livescan.VERLAUF_DATEI).st_mode)[-3:] == "600",
       "die Datei ist nur für den Benutzer lesbar")

wurzel, app = fenster()
zeilen = [app.verlauf.get(i) for i in range(app.verlauf.size())]
print("     oben:", zeilen[0])
pruefe("vorige Sitzung" in zeilen[0], "eine Trennzeile steht oben")
pruefe(zeilen[1:] == gemerkt[:livescan.VERLAUF_MERKEN],
       "darunter der Verlauf von vorhin")
app.verlauf.selection_set(1)
app._verlauf_geklickt()
takt(wurzel)
pruefe(app.treffer is not None, "der Rücksprung geht auch nach dem Neustart")
pruefe(app.letztes_bild is None, "nur die Aufnahme fehlt")
pruefe("nicht mehr" in app.vorschau.cget("text"), "und das steht auch da")
wurzel.destroy()

# ================== 8b. Ein Fehlversuch nimmt nichts weg
abschnitt("8b. Ein erfolgloser Scan lässt die Karte stehen")
wurzel, app = fenster()
erkannt = {"items": [artikel("sw0011", 88, "Chewbacca")]}
app._ausloesen(lambda: PNG)
takt(wurzel, 350)
pruefe(app.treffer["item_id"] == "sw0011", "eine Figur steht auf der Karte")
app.preisfeld.insert(0, "7,50")
bild_davor = app.letztes_bild

# Jetzt funkt der Wächter dazwischen und findet nichts.
erkannt = {"items": []}
app._ausloesen(lambda: b"anderes-bild", automatisch=True)
takt(wurzel, 350)
print("     Meldung:", app.stand.cget("text"))
pruefe(app.treffer is not None and app.treffer["item_id"] == "sw0011",
       "der Treffer bleibt stehen")
pruefe(str(app.k_sammlung.cget("state")) == "normal",
       "die Knöpfe bleiben scharf")
pruefe(app.preisfeld.get() == "7,50", "der eingetippte Preis bleibt")
pruefe(app.letztes_bild == bild_davor,
       "und die Aufnahme gehört weiter zu dieser Figur")
pruefe("bleibt stehen" in app.stand.cget("text"), "gesagt wird es trotzdem")

# Eine erkannte Figur wechselt die Karte sehr wohl.
erkannt = {"items": [artikel("sw0579", 92, "Veers")]}
app._ausloesen(lambda: b"neues-bild", automatisch=True)
takt(wurzel, 350)
pruefe(app.treffer["item_id"] == "sw0579", "eine erkannte Figur wechselt")
pruefe(app.letztes_bild == b"neues-bild", "und bringt ihre eigene Aufnahme mit")

# Ohne Treffer auf der Karte wird weiterhin aufgeräumt.
app._treffer_leeren()
erkannt = {"items": []}
app._ausloesen(lambda: PNG)
takt(wurzel, 350)
print("     ohne Stand:", app.stand.cget("text")[:46])
pruefe(app.treffer is None, "ohne bestehenden Treffer bleibt es leer")
pruefe("Nichts erkannt – enger rahmen" in app.stand.cget("text"),
       "und der alte Rat steht wieder da")
pruefe(app.letztes_bild == PNG, "die Aufnahme sieht man trotzdem")
wurzel.destroy()

# ============================= 9a. Fenstergröße und Preisfeld
abschnitt("9a. Alles Bedienbare bleibt erreichbar")
# Früher stand hier „bleibt im Fenster", und dafür sorgte eine Mindesthöhe
# in Höhe des ganzen Bedarfs. Auf einem kleineren Bildschirm kippte das ins
# Gegenteil: Das Fenster ließ sich nicht kleiner ziehen als der Schirm hoch
# ist, unten hing es heraus, und scrollen ging nicht. Jetzt scrollt der
# Inhalt – geprüft wird deshalb Erreichbarkeit, nicht Sichtbarkeit.
wurzel, app = fenster()
wurzel.deiconify()
wurzel.update()
wurzel.update_idletasks()
mindest = wurzel.minsize()
print("     Mindestgröße:", mindest, "· Bedarf:", wurzel.winfo_reqheight())
pruefe(mindest[1] <= 400,
       "das Fenster lässt sich klein ziehen (Mindesthöhe %d)" % mindest[1])
wurzel.geometry("%dx%d" % mindest)
# Der schwerste Fall: kleinstes Fenster **und** vier Ansichten zum Aussuchen.
for n in range(4):
    app.letztes_bild = bild(n)
    app._kandidaten_zeigen([artikel("sw0417", 70 + n, "Mace Windu")])
takt(wurzel, 300)
wurzel.update_idletasks()
pruefe(len(app._mini_rahmen) == 4, "vier Ansichten stehen zur Wahl")

felder = ((app.preisfeld, "Einkaufspreis"),
          (app.preisfeld.master, "Zustand-Reihe"),
          (app.k_sammlung, "＋ Sammlung"),
          (app.listenwahl, "Listenauswahl"),
          (app.nummerfeld, "Nummernfeld"),
          (app.verlauf, "Verlauf"))
pruefe(app.balken.winfo_ismapped(),
       "im kleinsten Fenster ist die Bildlaufleiste da")
for feld, name in felder:
    pruefe(feld.winfo_ismapped(), "%s ist angelegt" % name)

def hinscrollen(feld):
    """Zu einem Feld scrollen und melden, ob es dann in der Fläche steht.

    Nicht einfach ganz nach unten: Das Nummernfeld liegt **über** dem
    Preisfeld – am unteren Ende ist es oben aus der Fläche heraus. Erreichbar
    heißt, dass es zu jedem Feld eine Stellung gibt, in der es dasteht.
    """
    ganz = float(app.innen.winfo_height())
    oben = feld.winfo_rooty() - app.innen.winfo_rooty()
    app.leinwand.yview_moveto(max(0.0, (oben - 20) / ganz))
    wurzel.update_idletasks()
    y = feld.winfo_rooty() - app.leinwand.winfo_rooty()
    return 0 <= y and y + feld.winfo_height() <= app.leinwand.winfo_height() + 2

for feld, name in felder:
    pruefe(hinscrollen(feld), "%s ist nach dem Scrollen erreichbar" % name)
app.leinwand.yview_moveto(0.0)
wurzel.update_idletasks()
pruefe(app.ausloeser.winfo_rooty() - app.leinwand.winfo_rooty() >= 0,
       "und ganz oben steht wieder der Auslöser")

# Und auf einem großen Bildschirm darf sich nichts geändert haben: Ist Platz
# übrig, füllt der innere Rahmen die Fläche, sonst wüchse der Verlauf nicht
# mehr mit.
app.leinwand.yview_moveto(0.0)
app.preisfeld.insert(0, "4,50")
pruefe(app._preis_lesen() == (True, 4.5), "und nimmt einen Preis entgegen")
wurzel.destroy()

# ======================== 9a-2. Die Bildlaufleiste kommt und geht
abschnitt("9a-2. Die Bildlaufleiste kommt und geht")
wurzel, app = fenster()
wurzel.deiconify()

# **Das Fenster zwischen die beiden Inhaltshöhen legen, statt auf den
# Bildschirm zu hoffen.**
#
# Vorher stand hier fast die volle Schirmhöhe, und die Probe setzte
# voraus, dass der Inhalt dabei überläuft. Auf einem 4K-Schirm tut er das
# nicht: 1482 px Inhalt in 2080 px Fenster – die Leiste fehlte zu Recht,
# die Prüfung brach ab, und alles dahinter lief nie (30.08.2026).
#
# Jetzt werden beide Höhen gemessen und das Fenster dazwischen gelegt.
app.verlauf.config(height=40)
takt(wurzel, 200)
gross = app.innen.winfo_reqheight()
app.verlauf.config(height=1)
takt(wurzel, 200)
klein = app.innen.winfo_reqheight()
mitte = (gross + klein) // 2
print("     Inhalt groß %d px, klein %d px -> Fenster %d px"
      % (gross, klein, mitte))
if mitte + 80 > wurzel.winfo_screenheight():
    print("     (Bildschirm zu klein für diese Probe – übersprungen)")
else:
    app.verlauf.config(height=40)
    wurzel.geometry("560x%d" % mitte)
    takt(wurzel, 300)
    pruefe(app.balken.winfo_ismapped(), "voller Verlauf: die Leiste ist da")
    app.verlauf.config(height=1)      # nimmt rund 100 px weg
    takt(wurzel, 400)
    print("     Inhalt %d px in %d px Fläche"
          % (app.innen.winfo_reqheight(), app.leinwand.winfo_height()))
    pruefe(not app.balken.winfo_ismapped(),
           "passt alles hinein, verschwindet die Leiste wieder")
    pruefe(app.innen.winfo_height() >= app.leinwand.winfo_height(),
           "der Inhalt füllt die Fläche, der Verlauf wächst wie bisher mit")
    # Das ging vorher **nicht** von selbst: Die Nachführung setzt die Höhe
    # des inneren Rahmens fest, damit ändert sich seine tatsächliche Größe
    # nicht mehr, und das <Configure>, auf das sie horcht, blieb aus.
    # Seither schaut der ohnehin laufende 120-ms-Takt mit nach.
    app.verlauf.config(height=40)
    takt(wurzel, 300)
    pruefe(app.balken.winfo_ismapped(),
           "wächst der Inhalt wieder, kommt die Leiste von selbst zurück")
wurzel.destroy()

# ================================ 9a-3. Das Mausrad
abschnitt("9a-3. Das Mausrad geht dorthin, wo es hingehört")
wurzel, app = fenster()
wurzel.deiconify()
wurzel.geometry("560x300")
takt(wurzel, 200)


class Rad:
    """Ein Rad-Ereignis von Hand – `event_generate` kommt hier nicht an."""
    def __init__(self, widget, delta):
        self.widget, self.delta = widget, delta


oben = app.leinwand.yview()[0]
app._rad(Rad(app.leinwand, -3))
wurzel.update_idletasks()
pruefe(app.leinwand.yview()[0] > oben, "über der Karte schiebt das Rad sie")

stand = app.leinwand.yview()[0]
app._rad(Rad(app.verlauf, -3))
wurzel.update_idletasks()
pruefe(app.leinwand.yview()[0] == stand,
       "über dem Verlauf bleibt die Karte stehen – die Liste scrollt selbst")
app._rad(Rad(app.liste, -3))
wurzel.update_idletasks()
pruefe(app.leinwand.yview()[0] == stand,
       "über der Trefferliste ebenso")

# Ein zweites Fenster (das große Bild) darf die Karte nicht bewegen.
zweit = tk.Toplevel(wurzel)
inhalt = tk.Frame(zweit)
inhalt.pack()
wurzel.update_idletasks()
app._rad(Rad(inhalt, -3))
wurzel.update_idletasks()
pruefe(app.leinwand.yview()[0] == stand,
       "aus einem anderen Fenster kommt gar nichts an")
zweit.destroy()

# Und wenn nichts zu schieben ist, passiert nichts.
#
# **Nicht auf Platz hoffen.** Frueher zog diese Probe das Fenster auf
# Bildschirmhoehe und nahm an, dann passe der Inhalt hinein. Auf des Anwenders
# 2160-px-Schirm stimmte das, auf dem Bau-Runner nicht - dort scheiterte
# sie, obwohl nichts kaputt war. Also andersherum: den Inhalt so lange
# kleiner machen, bis er hineinpasst, und das vorher nachweisen.
app.verlauf.config(height=1)
wurzel.geometry("560x%d" % min(900, wurzel.winfo_screenheight() - 80))
takt(wurzel, 250)
uebrig = list(app.innen.pack_slaves())
while app.innen.winfo_reqheight() > app.leinwand.winfo_height() and uebrig:
    uebrig.pop().pack_forget()
    takt(wurzel, 150)
pruefe(app.innen.winfo_reqheight() <= app.leinwand.winfo_height(),
       "Voraussetzung: der Inhalt passt jetzt in die Flaeche")
app.leinwand.yview_moveto(0.0)
app._rad(Rad(app.leinwand, -3))
wurzel.update_idletasks()
pruefe(app.leinwand.yview()[0] == 0.0,
       "passt alles hinein, bewegt das Rad nichts")
wurzel.destroy()

# ================================ 9b. Fotos nicht doppelt anhängen
abschnitt("9b. Ein Foto je Artikel und Aufnahme")
wurzel, app = fenster()
angehaengt = []


class MitFoto(Attrappe):
    def foto_anhaengen(self, t, bild):
        angehaengt.append((t["item_id"], bild))
    in_sammlung = lambda self, t, z="used", p=None: "in der Sammlung"
    auf_wunschliste = lambda self, t: "auf der Wunschliste"
    auf_liste = lambda self, i, t, z="used", p=None: "auf der Liste"


app.instanz = MitFoto()
app.listen = [{"id": 1, "name": "Flohmarkt"}]
app.listenwahl.config(values=["Flohmarkt"])
app.listenwahl.current(0)
app.letztes_bild = b"aufnahme-A"
app._kandidaten_zeigen([artikel("sw0011", 88, "Chewbacca")])
takt(wurzel)

app.zur_sammlung()
takt(wurzel)
app.auf_liste()
takt(wurzel)
app.merken()
takt(wurzel)
print("     angehängt:", [(nr, b.decode()) for nr, b in angehaengt])
pruefe(len(angehaengt) == 1,
       "dreimal gebucht, aber nur ein Foto in der Galerie")
pruefe("hängt schon dran" in app.verlauf.get(0),
       "und der Verlauf sagt, warum kein zweites kam")

# Eine neue Aufnahme derselben Figur kommt sehr wohl dazu.
app.letztes_bild = b"aufnahme-B"
app._kandidaten_zeigen([artikel("sw0011", 90, "Chewbacca")])
takt(wurzel)
app.zur_sammlung()
takt(wurzel)
print("     angehängt:", [(nr, b.decode()) for nr, b in angehaengt])
pruefe(len(angehaengt) == 2, "eine neue Aufnahme wird angehängt")

# Und eine andere Figur bekommt ihr eigenes Foto.
trennen(app)
app._kandidaten_zeigen([artikel("sw0579", 92, "Veers")])
takt(wurzel)
app.zur_sammlung()
takt(wurzel)
pruefe(len(angehaengt) == 3, "eine andere Figur bekommt ihr eigenes")

# Mehrere ausgesuchte Ansichten gehen alle mit.
angehaengt.clear()
app.letztes_bild = b"dreh-1"
app._kandidaten_zeigen([artikel("sw0700", 70, "Drehfigur")])
takt(wurzel)
app.letztes_bild = b"dreh-2"
app._kandidaten_zeigen([artikel("sw0700", 75, "Drehfigur")])
takt(wurzel)
app.letztes_bild = b"dreh-3"
app._kandidaten_zeigen([artikel("sw0700", 60, "Drehfigur")])
takt(wurzel)
pruefe(len(app.bilder) == 3, "drei Ansichten liegen bereit")
app.bilder_an.clear()
app.bilder_an.update({0, 2})
app.zur_sammlung()
takt(wurzel)
print("     angehängt:", [b.decode() for _n, b in angehaengt])
pruefe([b for _n, b in angehaengt] == [b"dreh-1", b"dreh-3"],
       "genau die beiden ausgesuchten Ansichten hängen am Artikel")
pruefe("mit 2 Fotos" in app.verlauf.get(0), "und der Verlauf sagt, wie viele")

# Ohne Auswahl kommt keins mit.
angehaengt.clear()
app.bilder_an.clear()
app.auf_liste()
takt(wurzel)
pruefe(angehaengt == [], "ohne ausgesuchte Ansicht bleibt die Galerie leer")
wurzel.destroy()

# ================================================ 9. Der Wächter
abschnitt("9. Der Wächter – Stillstand und Drehscheibe")
livescan.AUTO_TAKT = 0.01
livescan.AUTO_PAUSE = 0.0


def wacht_lauf(drehbuch, stufe="mittel", je_minute=99, findet=True):
    """`_wachen` braucht nur eine Handvoll Attribute – die bekommt es hier,
    dazu ein Drehbuch statt echter Bildschirmabzüge."""
    livescan.AUTO_JE_MINUTE = je_minute
    folge = list(drehbuch)
    stand = {"name": "?"}
    raus = []

    class Merkende(queue.Queue):
        """Hält fest, **wann** ausgelöst wurde – hinterher steht im Drehbuch
        längst das letzte Bild, und man erführe nie, für welches es war."""
        def put(self, stueck, *a, **k):
            if stueck[0] == "auto-los":
                raus.append(stand["name"])
                # Statt der Erkennung: Sie meldet zurück, ob sie etwas
                # gefunden hat – genau das tut sonst `_ausloesen`.
                w.auto_leer = 0 if findet else w.auto_leer + 1
            elif stueck[0] == "auto-aus":
                raus.append("ABBRUCH")
            queue.Queue.put(self, stueck, *a, **k)

    class Wacht:
        pass

    w = Wacht()
    w.post, w.wacht, w.stufe = Merkende(), True, stufe
    w.bereich, w.beschaeftigt, w.auto_anfragen = (0, 0, 9, 9), False, []
    w.auto_leer = 0

    def abzug(_b):
        if not folge:
            w.wacht = False
        return PNG

    def finger(roh, kante=0):
        if not folge:
            return [0] * 576
        stand["name"], hell = folge.pop(0)
        return [hell] * 576

    livescan.bereich_aufnehmen, livescan.fingerabdruck = abzug, finger
    livescan.LiveScanner._wachen(w)
    return raus


# Ein Verkäufer, der die Figur hochhält: Bewegung, dann Stillstand.
raus = wacht_lauf([("greifen", 150)] * 2 + [("Figur A", 60)] * 5
                  + [("greifen", 150)] * 2 + [("Figur B", 200)] * 5)
print("     Stillstand ->", raus)
pruefe(raus == ["Figur A", "Figur B"],
       "je einmal, wenn die Figur stillgehalten wird")

# Eine Drehscheibe: nie still, aber gleichmäßig. Das Bild wandert in
# gleichen Schritten hin und zurück – nie so weit auf einmal, dass es als
# Griff ins Bild durchginge.
welle = list(range(60, 100, 5)) + list(range(90, 60, -5))
dreh = [("Dreh %d" % i, welle[i % len(welle)]) for i in range(40)]
raus = wacht_lauf(dreh)
print("     Drehscheibe ->", len(raus), "Anfragen")
pruefe(len(raus) >= 2,
       "auf der Drehscheibe wird ausgelöst, obwohl nie Ruhe eintritt")
pruefe(len(raus) <= livescan.AUTO_ANSICHTEN,
       "aber höchstens %d Ansichten je Artikel – bei 40 Takten"
       % livescan.AUTO_ANSICHTEN)

# Und ein Griff ins Bild beendet die Sammlung: danach dürfen wieder
# Ansichten geholt werden.
raus = wacht_lauf(dreh[:20] + [("griff", 250)] + dreh[:20])
print("     Drehen, Griff, Drehen ->", len(raus), "Anfragen")
pruefe(len(raus) > livescan.AUTO_ANSICHTEN,
       "nach dem Artikelwechsel beginnt das Zählen von vorn")

# Eine Laufschrift im Bereich: bewegt sich anhaltend, aber es gibt dort
# nichts zu erkennen. Nach ein paar Fehlversuchen soll Schluss sein.
raus = wacht_lauf(dreh, findet=False)
print("     Bewegung ohne Treffer ->", len(raus), "Anfragen")
pruefe(len(raus) == livescan.AUTO_LEERLAUF,
       "nach %d erfolglosen Anfragen hört der Dreh-Auslöser auf"
       % livescan.AUTO_LEERLAUF)

# Wichtig: Nur der Dreh-Auslöser gibt auf. Wer die Figur ruhig hält, bekommt
# weiterhin seinen Versuch – sonst wäre der Bereich für den Rest des Abends tot.
# Das Bild wandert dabei erst weg – käme es bei einem Wert zur Ruhe, der eben
# schon geschickt wurde, hielte der Wächter es zu Recht für dasselbe Bild.
raus = wacht_lauf(dreh[:24] + [("weg", 100), ("weg", 112)]
                  + [("still gehalten", 124)] * 5, findet=False)
print("     … dann still gehalten ->", raus[-1])
pruefe(raus[-1] == "still gehalten",
       "der Stillstand-Auslöser bleibt trotzdem scharf")

# Aber ein Artikelwechsel gibt ihm eine neue Chance.
raus = wacht_lauf(dreh[:24] + [("griff", 250)] + dreh[:24], findet=False)
print("     … nach einem Griff ins Bild ->", len(raus), "Anfragen")
pruefe(len(raus) > livescan.AUTO_LEERLAUF,
       "nach dem Sprung wird es erneut versucht")

# Ein Standbild, das nur leicht flimmert: nach dem ersten Blick nichts mehr.
raus = wacht_lauf([("flimmern", 100 + (i % 2)) for i in range(30)])
print("     Standbild ->", raus)
pruefe(len(raus) == 1, "ein ruhiges Bild löst nur beim Einschalten aus")

# ============================================================ Warum grün?
abschnitt("Die Marke sagt, warum die Zeile grün ist")

# Am 30.08.2026: Grüne Zeile über der Erklärung „— noch nicht in eurer
# Sammlung". Die Figur steckte in einem eigenen Set und lag auf einer
# Liste, war aber nicht als eigener Eintrag erfasst. Grün war richtig,
# nur sagte nichts, warum.
IN_SET = {"in_sets": "7931-1|T-6 Jedi Shuttle|1|used"}
IN_NEUEM_SET = {"in_sets": "7931-1|T-6 Jedi Shuttle|1|new"}
IN_SET_ALT = {"in_sets": "7931-1|T-6 Jedi Shuttle|1"}   # ohne Zustand
AUF_LISTE = {"on_lists": ["Flohmarkt 30.08."]}

pruefe(livescan._schon_da_marke({"owned": 2}) == "✔",
       "in der Sammlung -> ✔")
pruefe(livescan._schon_da_marke(AUF_LISTE) == "🛒",
       "auf einer Einkaufsliste -> 🛒")
pruefe(livescan._schon_da_marke(IN_SET) == " ",
       "ein eigenes Set allein -> kein Zeichen")
pruefe(livescan._schon_da_marke({}) == " ",
       "nichts davon -> kein Zeichen")
pruefe(livescan._schon_da_marke(dict(AUF_LISTE, owned=1)) == "✔",
       "beides -> Besitz schlägt Liste")

# **Ein eigenes Set färbt nicht mehr grün.** Man trägt die Figuren zu
# jedem Set einzeln ein; steht eine Figur nicht in der Sammlung, hat er sie
# auch nicht – viele Sets kommen ohne Figuren herein (30.08.2026).
pruefe(livescan._schon_da({"owned": 1}), "grün bei: Besitz")
pruefe(livescan._schon_da(AUF_LISTE), "grün bei: Einkaufsliste")
pruefe(not livescan._schon_da(IN_SET),
       "ein GEBRAUCHTES eigenes Set färbt NICHT grün")
pruefe(livescan._schon_da(IN_NEUEM_SET),
       "ein NEUES (versiegeltes) Set färbt grün – die Figur steckt drin")
pruefe(not livescan._schon_da(IN_SET_ALT),
       "ohne Zustandsangabe gilt die vorsichtigere Annahme: gebraucht")
pruefe(livescan._schon_da_marke(IN_NEUEM_SET) == "📦",
       "versiegeltes Set -> 📦")
pruefe("ungeöffneten Set 7931-1" in
       livescan._besitz_zeile(IN_NEUEM_SET)["text"],
       "und die Zeile sagt, dass es ungeöffnet ist")
pruefe("ungeöffnet" in livescan._woanders(IN_NEUEM_SET),
       "auch der Hinweis darunter unterscheidet versiegelt von offen")
pruefe("ungeöffnet" not in livescan._woanders(IN_SET),
       "beim gebrauchten Set steht das Wort nicht da")
pruefe(not livescan._schon_da({"wanted": 1}),
       "ein Wunsch allein färbt nicht grün")

# Die Zeile darunter beantwortet „habe ich das?" – und nennt die Liste.
pruefe("2× in eurer Sammlung" in livescan._besitz_zeile({"owned": 2})["text"],
       "Besitz steht als Besitz da")
pruefe("Flohmarkt 30.08." in livescan._besitz_zeile(AUF_LISTE)["text"],
       "ohne Besitz, aber auf einer Liste -> die Liste steht da")
pruefe("noch nicht" not in livescan._besitz_zeile(AUF_LISTE)["text"],
       "und nicht mehr »noch nicht in eurer Sammlung«")
zwei = livescan._besitz_zeile({"on_lists": ["A", "B"]})["text"]
pruefe("2 Einkaufslisten" in zwei and "A, B" in zwei,
       "bei mehreren Listen stehen Anzahl und Namen da")
pruefe("noch nicht in eurer Sammlung" in livescan._besitz_zeile(IN_SET)["text"],
       "ein eigenes Set ändert an der Antwort nichts")

# Und die Liste steht nur noch an einer Stelle.
pruefe("🛒" not in livescan._woanders(AUF_LISTE),
       "die Zeile darunter wiederholt die Liste nicht")
pruefe("7931-1" in livescan._woanders(IN_SET),
       "das eigene Set steht weiterhin als Hinweis darunter")

# ==================================================== Hilfe-Menue
# macOS legt den Hilfe-Eintrag von sich aus an. Ohne hinterlegten Befehl
# antwortet es "Help isn't available for Brickfolio Live-Scanner" - genau
# so trat es auf am 30.08.2026.
abschnitt("10. Die Hilfe zeigt das Handbuch")
_w = tk.Tk(); _w.withdraw()
_w.createcommand("::tk::mac::ShowHelp", livescan.handbuch_zeigen)
pruefe(_w.eval("info commands ::tk::mac::ShowHelp").strip() != "",
       "der Befehl haengt am Hilfe-Menue")
_w.destroy()

pruefe(livescan.handbuch_pfad() is not None,
       "das Handbuch wird neben dem Quelltext gefunden")
pruefe(os.path.basename(livescan.handbuch_pfad()) == "README.md",
       "und es ist das README")
# Die Probe oben meldet den Befehl selbst an - sie wuerde also auch
# bestehen, wenn main() das Anmelden vergisst. Darum hier zusaetzlich in
# den Quelltext geschaut.
_scan_roh = pathlib.Path(livescan.__file__).read_text()
_ab_main = _scan_roh[_scan_roh.index("def main():"):]
pruefe('createcommand("::tk::mac::ShowHelp"' in _ab_main,
       "main() meldet den Hilfe-Befehl auch wirklich an")

_bau_roh = pathlib.Path(__file__).with_name("bauen.sh").read_text()
pruefe("codesign --force --deep --sign" in _bau_roh,
       "bauen.sh unterschreibt das Buendel")
pruefe('IDENT="-"' in _bau_roh,
       "und faellt ohne Zertifikat auf ad hoc zurueck, statt abzubrechen")

_setup_roh = pathlib.Path(__file__).with_name("setup.py").read_text()
pruefe('"README.md"' in _setup_roh,
       "das Buendel nimmt das Handbuch mit - sonst zeigt die Hilfe im\n"
       "       fertigen Programm ins Leere")

# ================================================ Bauvorschrift
# Die Fassung steht in livescan.py; setup.py schreibt sie ins Info.plist des
# Bündels. Läuft das auseinander, zeigt die fertige App eine falsche Nummer –
# und niemand merkt es, weil nichts abstürzt. Darum hier eine Wache.
import re as _re

_setup = pathlib.Path(__file__).with_name("setup.py").read_text()
pruefe('re.search(r\'^VERSION = "([^"]+)"\'' in _setup,
       "setup.py liest die Fassung aus livescan.py, statt sie zu wiederholen")
pruefe(_re.match(r"^\d+\.\d+\.\d+$", livescan.VERSION) is not None,
       "die Fassung hat die Form 1.2.3")
_icns = pathlib.Path(__file__).with_name("livescan.icns")
pruefe(_icns.exists() and _icns.stat().st_size > 1000,
       "das Symbol fürs Bündel liegt bei")
# py2app zieht tkinter nur mit, wenn es ausdrücklich dabeisteht.
pruefe('"packages": ["tkinter"]' in _setup,
       "setup.py nimmt tkinter ausdrücklich mit")

# ============================================================ Bilanz
print("\n" + "─" * 58)
print("\033[1m%d Proben bestanden, %d fehlgeschlagen\033[0m"
      % (bilanz["gut"], bilanz["schlecht"]))
for p in (livescan.EINSTELLUNGEN, livescan.VERLAUF_DATEI):
    if os.path.exists(p):
        os.remove(p)
os.rmdir(ORDNER)
raise SystemExit(1 if bilanz["schlecht"] else 0)
