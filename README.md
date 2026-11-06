# TB2-Textfinder

Ein kleines Windows-Programm zum Durchsuchen von \`*.TB2\`-Dateien nach Texten, die in unterschiedlichen Signum-/SignumNext-Dateigenerationen gespeichert sein können.

**Aktueller Entwicklungsstand:** 0.7 (experimentell)

## Funktionen

- Durchsucht einen gewählten Ordner nach \`.TB2\`-Dateien.
- Kann Unterordner einbeziehen.
- Sucht Klartext und mehrere bisher beobachtete Glyphen-/Datensatzmuster.
- Ignoriert die Groß-/Kleinschreibung standardmäßig, auch bei deutschen Umlauten.
- Zeigt als Treffer den vollständigen Dateipfad.
- Treffer können kopiert oder als TXT-Datei gespeichert werden.
- Ein Treffer lässt sich per Doppelklick oder über **Datei öffnen** mit der in Windows verknüpften Anwendung öffnen.
- Die TB2-Dateien werden nur gelesen und nicht verändert.

## Starten

Voraussetzung: Windows und Python 3.10 oder neuer mit Tkinter.

1. Dieses Repository herunterladen oder klonen.
2. \`Start_TB2_Textfinder.bat\` doppelt anklicken.
3. Suchbegriff und Ordner auswählen und auf **Suchen** klicken.

Es werden keine zusätzlichen Pakete benötigt, um das Python-Skript direkt auszuführen.

## Eine Windows-EXE erstellen

Eine EXE lässt sich direkt auf Windows erzeugen:

1. Python 3.10 oder neuer installieren.
2. \`Build_EXE.bat\` doppelt anklicken.
3. Beim ersten Lauf benötigt der Build eine Internetverbindung, um PyInstaller herunterzuladen.
4. Die fertige Datei liegt anschließend unter \`dist\\TB2_Textfinder.exe\`.

Die BAT-Datei erstellt eine lokale virtuelle Python-Umgebung im Ordner \`.venv\`, installiert darin PyInstaller und erstellt eine einzelne EXE ohne zusätzliches Konsolenfenster. Die EXE enthält den Python-Interpreter und benötigt auf dem Zielrechner keine Python-Installation.

Der Build verwendet PyInstaller mit \`--onefile\` und \`--windowed\`. Details dazu stehen in der [PyInstaller-Dokumentation](https://pyinstaller.org/en/stable/usage.html).

## Bisher untersuchte TB2-Muster

Die folgenden Muster wurden anhand der bislang vorliegenden Beispieldateien empirisch beobachtet:

- Datensatzabstand \`0x6A\` (106 Bytes) mit Marker \`81 00 00\`.
- Datensatzabstand \`0x6A\` (106 Bytes) mit einem weiteren beobachteten Marker.
- Älteres Muster mit Abstand \`0x50\` (80 Bytes) und Marker \`81 00 00\`.
- Frühes Muster mit Abstand \`0x50\` (80 Bytes) und Marker \`81 7C E9 E4 58 09\`.
- Ein-Byte-Zeichenkodierungen wie CP850, CP437, CP1252 und Latin-1 werden bei den Glyphenprofilen berücksichtigt.

Das ist **keine vollständige oder offizielle Spezifikation** des TB2-Dateiformats. Die Muster sind aus einzelnen Beispieldateien abgeleitet. Ein Nichttreffer beweist daher nicht, dass der gesuchte Text nicht in der Datei vorkommt.

## Tests

Die Parser-Tests verwenden künstlich erzeugte Bytefolgen und benötigen keine Kundendateien:

\`\`\`powershell
py -3 -m unittest discover -s tests -v
\`\`\`

## Privatsphäre und Dateien

Der Textfinder durchsucht Dateien lokal auf dem Rechner. Er lädt keine TB2-Dateien hoch und verändert sie nicht. Bitte vor dem Teilen von Beispieldateien prüfen, ob diese Kunden- oder andere vertrauliche Daten enthalten.

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz**. Du darfst den Quellcode verwenden, kopieren, verändern, zusammenführen, veröffentlichen, weitergeben, unterlizenzieren und auch kommerziell nutzen. Voraussetzung ist, dass der Copyright- und Lizenzhinweis in allen Kopien oder wesentlichen Teilen des Projekts erhalten bleibt.

Den vollständigen Lizenztext findest Du in der Datei [\`LICENSE\`](LICENSE).

## Hinweis

Dieses Projekt ist ein unabhängiges Experiment zur Untersuchung von TB2-Dateien. Es ist nicht mit dem Hersteller von Signum/SignumNext verbunden oder von diesem autorisiert.
