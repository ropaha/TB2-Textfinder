# Changelog

Alle wesentlichen Änderungen am TB2-Textfinder und Negativtester werden hier dokumentiert.

Die Versionsnummer des Gesamtpakets ist unabhängig von den Programmversionen. Die Erkennung beruht auf empirisch untersuchten TB2-Dateien, nicht auf einer vollständigen offiziellen Formatspezifikation.

## [Unveröffentlicht] – Entwicklungsbranch `dev`

### Fensterpositionierung
- Gemeinsames Modul `tb2_window_position.py` für die Fensterzentrierung ergänzt; keine zusätzliche Python-Bibliothek erforderlich.
- Hauptfenster von TB2-Textfinder und TB2-Negativtester werden beim Start auf dem Monitor unter dem Mauszeiger zentriert.
- Info-Fenster wird über dem Textfinder-Hauptfenster, das MIT-Lizenzfenster über seinem Elternfenster zentriert. Die Position wird auf den nutzbaren Monitorbereich begrenzt.
- Windows-Einzelmonitorbetrieb manuell erfolgreich getestet; Mehrmonitorbetrieb noch nicht praktisch geprüft.
- Windows-Systemdialoge werden weiterhin teilweise vom Betriebssystem positioniert; exakte Zentrierung ist dort nicht garantiert.

## [1.8.7] – 2026-11-19

### Transparenz und Dokumentation
- Im Info-Fenster des TB2-Textfinders die Schaltfläche **„GitHub-Projekt öffnen“** ergänzt. Sie öffnet das öffentliche Projekt-Repository im Standardbrowser.
- Neue Schaltfläche unter Windows erfolgreich getestet.
- Änderung über Pull Request #8 von `dev` nach `main` übernommen.

### Versionierung
- Versionsangaben des TB2-Textfinders und TB2-Negativtesters auf **1.8.7** gesetzt.
- Keine Änderung an der Such- oder Erkennungslogik.

## [1.8.6] – 2026-11-11

### Neu
- Option **„Nur ganze Wörter“** als zweites Kontrollkästchen ergänzt und standardmäßig aktiviert. Die Ganzwortsuche berücksichtigt Wortgrenzen in Klartext und bekannten TB2-Glyphenprofilen; Bindestriche gelten als Wortgrenzen.
- Laufende Suche über **„Suche abbrechen“** abbrechbar.
- Dauerhafte Zusammenfassung der letzten Suche getrennt von der laufenden Statusanzeige.

### Verbesserungen
- Zweistufige Ganzwortsuche: Zuerst schnelle Kandidatenprüfung, dann Wortgrenzenprüfung nur bei möglichen Treffern.
- Während einer Suche ist **„Leeren“** deaktiviert.
- Versionsnummern von Textfinder und Negativtester auf **1.8.6** vereinheitlicht.

### Tests und Repository-Pflege
- Regressionstests für Ganzwortsuche in Klartext und bekannten Glyphenprofilen ergänzt.
- Manuelle Prüfung der Ganzwortsuche mit „Hagen“ und „Meyer“ auf 7.879 Dateien: kontrollierte Treffer korrekt; für „Hagen“ ca. 86 s mit Ganzwortsuche gegenüber ca. 88 s ohne Ganzwortfilter.
- Vier Benchmark-Skripte in `tests/` verschoben; Import- und Aufrufpfade angepasst.
- Vier interaktive Windows-Batchdateien zum Starten der Benchmarks mit Parameterabfrage ergänzt und ebenfalls in `tests/` abgelegt. Batchdateien unter Windows erfolgreich erprobt.

### Hinweise
- Die Ganzwortsuche basiert auf empirisch bekannten Dateimustern und kann bei unbekannten Varianten Treffer übersehen.
- Die Aufräumarbeiten an den Benchmarks sind Bestandteil des Entwicklungsstands **1.8.6**; keine zusätzliche Versionsnummer.

## [1.8.5] – 2026-11-11

### Verbesserungen
- Ressourcenpfad-Maskierung beschleunigt: Der Regex für historische Netzwerkpfade wird nur ausgeführt, wenn der Anker `\\SYS\\` in den Dateidaten vorkommt.
- Benchmark-Skript `benchmark_resource_paths.py` zum Vergleich der Pfadmaskierung ergänzt.

### Praxistests
- Suche nach „Hagen“ über 7.879 Dateien: 286 s → 87 s bei 21 identischen Treffern.
- Suche über 14.539 Dateien: 506 s → 233 s bei 111 identischen Treffern und Dateipfaden.
- Die Ergebnisse belegen die Übereinstimmung der getesteten Bestände, nicht sämtlicher denkbarer Dateivarianten.

## [1.8.4] – 2026-11-10 (Releasevorbereitung)

### Neu
- Zwei Suchmodi: **Schnell** (Standard; erkannte JPEG-Datenbereiche werden übersprungen) und **Vollständig** (Suche über alle Bytes).
- Laufzeit der Suche wird in der Statusanzeige ausgegeben.
- **Info**-Fenster mit Programmname, Versionsnummer, bisherigen Hinweisen und separater Anzeige der vollständigen MIT-Lizenz.
- Erkennung und Maskierung eingebetteter Ressourcen- und Netzwerkdateipfade, unter anderem mit den Endungen `.STN`, `.ORN` und `.BAU`, zur Verringerung von Fehlalarmen.

### Verbesserungen
- Schnellmodus steht in der Oberfläche an erster Stelle und ist vorausgewählt.
- Der bisherige Hinweistext wurde aus dem Hauptfenster in das Info-Fenster verlagert.
- MIT-Copyright-Hinweis auf `Roga Hagen (roga@hagen.me)` aktualisiert.
- Suche nach `.TB2`- und `.TBL`-Dateien; Ergebnisliste weiterhin mit vollständigen Dateipfaden.

### Praxiserfahrung und Einschränkungen
- Bei einer manuell kontrollierten Suche nach „Hagen“ wurden durch die Pfadfilterung zahlreiche Treffer aus gespeicherten Dateipfaden ausgeschlossen.
- Die zusätzliche Pfadanalyse kann die Suche verlangsamen.
- **Schnell** kann Treffer übersehen; bei Zweifeln **Vollständig** verwenden.
- Die Formaterkennung bleibt empirisch und kann bei unbekannten Dateivarianten Treffer übersehen. Die Originaldateien werden nicht verändert.

## [1.8.0] – 2026-11-07 (Releasepaket vorbereitet)

**Enthalten:** TB2-Textfinder 1.7 und TB2-Negativtester 1.2.

### Neu
- Negativtester: Treffer nach möglichen Textfragmenten, vermutlich textfreien Dateien und Fehlern/leeren Dateien filtern – ohne erneuten Scan.
- TXT-Export und Kopieren berücksichtigen die aktuell gefilterte Liste.
- Dreistufige Erkennung: vollständiges bekanntes Muster (mindestens drei Zeichen), Fragment (zwei Zeichen), kein bekanntes Muster/Fragment.
- Erweiterte empirische Textprofile mit 80, 98, 106 und 587 Bytes Zeichenabstand und variablen Steuerbytes.
- Zusätzliche Referenzfälle mit Namen, Datumsangaben und Umlauten.

### Praxistest
- Bei 14.538 Dateien wurden 14 zur weiteren Untersuchung angezeigt. Das ist keine garantierte Texterkennungsquote: Es gibt reine Grafikdateien und potenziell unbekannte Textstrukturen.

### Einschränkungen
- „Enthält vermutlich keinen Text“ ist keine Gewissheit.
- Fragmente können auch in Grafikdaten vorkommen.
- Windows benötigt Python 3.10+ inklusive Tkinter; keine eigenständige EXE.
- GUI nicht automatisiert unter Windows getestet.

## [0.7.0] – früherer GitHub-Stand
- Experimenteller TB2-Finder für Signum-/SignumNext-Dateien, mit Windows-Oberfläche und Ordnersuche.
- Erste Glyphenprofile und Negativtester.
