# TB2-Textfinder

<p align="center"><img src="logo.svg" alt="TB2-Textfinder Bandzugfeder-Logo" width="150"></p>

Ein kleines Windows-Programm zum Durchsuchen von `.TB2`-Dateien nach Texten, die in unterschiedlichen Signum-/SignumNext-Dateigenerationen gespeichert sein können.

**Aktuelle Version:** 1.8.4. · [Änderungsverlauf](CHANGELOG.md) · [English version](README_EN.md)

![TB2-Textfinder Projektbanner](banner.svg)

## Wie dieses Projekt entstanden ist

Der Anlass war ein ganz praktisches Problem aus dem Steinmetzhandwerk: Eine Steininschrift aus dem Jahr 1992 sollte ergänzt werden. Die damalige Beschriftung war noch als Signum-Datei vorhanden – nur welche der vielen Dateien aus diesem Jahr war die richtige?

Um die Vorlage wiederzufinden, musste ich zahlreiche Dateien einzeln in Signum öffnen und durchsehen. Das hat funktioniert, war aber mühsam und zeitaufwendig. Daraus entstand die Idee für den TB2-Textfinder: Warum nicht die alten Dateien direkt nach einem Namen oder einem Text durchsuchen und sich die passenden Dateipfade anzeigen lassen?

Das Programm ist deshalb in erster Linie ein Werkzeug für meinen eigenen Arbeitsalltag. Vielleicht kennt aber auch der eine oder andere Kollege die Situation: Alte digitale Vorlagen sind noch da, doch die Suche nach der richtigen Datei dauert länger als die eigentliche Arbeit.

Die bisher untersuchten Dateien lassen sich in meinem Bestand inzwischen praktisch vollständig bearbeiten beziehungsweise nach manueller Prüfung gezielt ausnehmen. Andere Bestände können bislang unbekannte Dateimuster enthalten; eine vollständige Erkennung aller Signum-Varianten ist nicht garantiert.

## Funktionen

- Durchsucht einen gewählten Ordner nach `.TB2`- und `.TBL`-Dateien, auf Wunsch einschließlich Unterordnern.
- Sucht Klartext und mehrere bislang empirisch beobachtete Glyphen-/Datensatzmuster.
- Zwei Suchmodi: **Schnell** (Standard; überspringt erkannte JPEG-Bereiche) und **Vollständig** (prüft alle Bytes). Die schnelle Suche kann Treffer übersehen.
- Filtert erkennbare eingebettete Ressourcen- und Netzwerkdateipfade, um Fehlalarme zu reduzieren.
- Zeigt nach der Suche die benötigte Laufzeit an.
- **Info**-Fenster mit Hinweisen und vollständiger MIT-Lizenz.
- Ignoriert standardmäßig die Groß-/Kleinschreibung, auch bei deutschen Umlauten.
- Zeigt vollständige Dateipfade an.
- Trefferpfade können kopiert oder als TXT-Datei gespeichert werden.
- Treffer lassen sich per Doppelklick oder über **Datei öffnen** mit der in Windows verknüpften Anwendung öffnen.
- TB2-Dateien werden nur gelesen und nicht verändert.

## Programmoberfläche

![Schematische Vorschau der Programmoberfläche](docs/screenshot.svg)

*Hinweis: Dies ist eine schematische Vorschau, kein echter Screenshot eines laufenden Programms. Das tatsächliche Erscheinungsbild kann je nach Version und Windows-Design abweichen.*

## Starten

Voraussetzung: Windows und Python 3.10 oder neuer mit Tkinter.

1. Dieses Repository herunterladen oder klonen.
2. `Start_TB2_Textfinder.bat` doppelt anklicken.
3. Suchbegriff und Ordner auswählen und auf **Suchen** klicken.

Für den direkten Start des Python-Skripts werden keine zusätzlichen Pakete benötigt. Die Dateien `TB2_Textfinder.py`, `tb2_jpeg_fast.py` und `tb2_resource_paths.py` müssen im selben Verzeichnis liegen.

## Windows-EXE erstellen

1. Python 3.10 oder neuer installieren.
2. `Build_EXE.bat` doppelt anklicken.
3. Beim ersten Lauf wird eine Internetverbindung benötigt, um PyInstaller zu installieren.
4. Die fertige Datei liegt anschließend unter `dist\TB2_Textfinder.exe`.

Das Build-Skript erstellt eine lokale virtuelle Umgebung unter `.venv`, installiert PyInstaller und baut eine einzelne EXE ohne zusätzliches Konsolenfenster. Der Python-Interpreter wird mitgeliefert.

## Bisher untersuchte TB2-Muster

Die folgenden Muster wurden anhand der bislang vorliegenden Beispieldateien empirisch beobachtet:

- Datensatzabstand `0x6A` (106 Bytes) mit Marker `81 00 00`.
- Ein weiteres beobachtetes Markermuster mit 106-Byte-Abstand.
- Älteres Muster mit Abstand `0x50` (80 Bytes) und Marker `81 00 00`.
- Frühes Muster mit Abstand `0x50` (80 Bytes) und Marker `81 7C E9 E4 58 09`.
- Ein-Byte-Zeichenkodierungen wie CP850, CP437, CP1252 und Latin-1 werden bei den Glyphenprofilen berücksichtigt.

Dies ist **keine vollständige oder offizielle Spezifikation** des TB2-Dateiformats. Die Beobachtungen beruhen auf einer begrenzten Zahl von Beispieldateien. Ein Nichttreffer beweist daher nicht, dass der gesuchte Text in einer Datei fehlt.

## Tests

Die Parser-Tests verwenden künstlich erzeugte Bytefolgen und benötigen keine Kundendateien:

```powershell
py -3 -m unittest discover -s tests -v
```

## Datenschutz

Die Suche läuft lokal auf dem Rechner. Das Programm lädt keine TB2-Dateien hoch und verändert sie nicht. Vor dem Teilen von Beispieldateien bitte prüfen, ob diese Kunden- oder andere vertrauliche Daten enthalten.

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz**. Den vollständigen Lizenztext findest du in [LICENSE](LICENSE) und über **Info → MIT-Lizenz anzeigen** im Programm.

## Hinweis

Dieses Projekt ist ein unabhängiges Community-Projekt zur Untersuchung von TB2-Dateien. Es ist nicht mit dem Hersteller von Signum/SignumNext verbunden, wird von diesem nicht unterstützt und ist kein offizielles Produkt.
