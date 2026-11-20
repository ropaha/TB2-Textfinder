# Changelog

Alle wesentlichen Änderungen am TB2-Textfinder und Negativtester werden hier dokumentiert.

Die Versionsnummer des Gesamtpakets ist unabhängig von den Programmversionen. Die Erkennung beruht auf empirisch untersuchten TB2-Dateien, nicht auf einer vollständigen offiziellen Formatspezifikation.

## [1.9.0] – Release

### Versionierung und Releases
- Einheitliche Versionsregel für beide Programme: Entwicklungsstände mit **-dev** (Entwicklungsstand **1.9.0-dev** vor diesem Release), veröffentlichte Versionen ohne Suffix. Test- und Release-Builds prüfen die Versionskonvention; der Release-Vorbereitungsschritt entfernt das Suffix und übernimmt den unveröffentlichten Changelog-Abschnitt. Kein automatischer Merge oder Release.
- Das Infofenster zeigt bei Entwicklungsversionen auch die unveröffentlichten Änderungen an.

### Oberfläche und Bedienung
- Beide Programme: Arbeitsfunktionen wieder in **einer einzigen Schaltflächenzeile**, während **Info** und **Programm beenden** rechtsbündig unter der Trefferliste bleiben. Die Speichern-Schaltfläche heißt platzsparend **TXT speichern …**.
- Beide Programme: **Info** und **Programm beenden** sind jetzt als separate, rechtsbündige Schaltflächen **unterhalb der Trefferliste** angeordnet. Die oberen Aktionszeilen enthalten nur noch Such- und Ergebnisfunktionen.
- Beide Programme: Schaltflächen auf zwei übersichtliche Aktionszeilen verteilt, damit **Programm beenden** und **Zugriffsprobleme** bei der bisherigen Standardfensterbreite nicht abgeschnitten werden. Hauptaktionen stehen oben, weitere Aktionen darunter.
- Beide Programme: **Programm beenden** als zusätzliche Schaltfläche. Das Windows-Fensterkreuz und die Schaltfläche schließen im Leerlauf sofort; während einer Suche/Prüfung erscheint eine Sicherheitsabfrage. Bei Bestätigung wird der laufende Vorgang kontrolliert abgebrochen und das Fenster nach Ende der Hintergrundarbeit geschlossen, bei Ablehnung läuft alles weiter.
- Textfinder: **Suchen** ist nur aktiv, wenn sowohl **Gesuchter Text** als auch **Ordner** ausgefüllt sind. Änderungen an beiden Feldern aktualisieren den Button unmittelbar; während einer laufenden Suche bleibt der Abbruch möglich.
- Textfinder: Verzeichnissuche läuft jetzt ebenfalls **im Hintergrund** und kann bereits beim Einsammeln der TB2-/TBL-Dateien abgebrochen werden. Die Oberfläche zeigt den Suchfortschritt, überspringt Windows-Junctions und bietet bei tatsächlich nicht lesbaren Verzeichnissen den Button **Zugriffsprobleme (Anzahl)** direkt hinter **Suchen** mit scrollbareren Details. Bestehende Suchmodi und Trefferverarbeitung bleiben unverändert.
- Negativtester: Zugriffsprobleme erscheinen nach der Prüfung nicht mehr als blockierende Warnmeldung. Stattdessen zeigt ein kompakter Button **Zugriffsprobleme (Anzahl)** direkt hinter **Ordner prüfen** in der oberen Schaltflächenleiste bei Bedarf ein scrollbareres Detailfenster mit allen betroffenen Pfaden und Fehlermeldungen. Beim Start einer neuen Prüfung oder beim Leeren wird der Hinweis zurückgesetzt.
- Negativtester: Auch das **Einsammeln der TB2-/TBL-Dateien** und das Einlesen der Ignorierlisten laufen jetzt im Hintergrund. Die Oberfläche bleibt während großer Verzeichnissuchen bedienbar; **Prüfung abbrechen** wirkt bereits in dieser Phase. Fortschrittsmeldung mit Anzahl durchsuchter Ordner und gefundener Dateien, Warnung bei übersprungenen Verzeichnissen oder nicht lesbaren Ignorierlisten; Windows-Junctions werden nicht rekursiv verfolgt.
- Negativtester: **Ordner prüfen** wechselt während der Analyse zu **Prüfung abbrechen**. Der Abbruch erfolgt nach der laufenden Datei; bereits erkannte Auffälligkeiten bleiben als Ergebnisse erhalten. Die Statuszeile zeigt den Abbruch sowie die Anzahl tatsächlich geprüfter Dateien.
- Negativtester: eigenes **Infofenster** im Stil des Textfinders mit dem bisherigen Erklärungstext sowie **Was ist neu?**, **GitHub**, **MIT-Lizenz** und **Schließen**. Der Erklärungstext unter der Trefferliste entfällt und gibt Platz frei.
- Textfinder und Negativtester: **Suchen** bzw. **Ordner prüfen** wird erst mit ausgefülltem Ordnerfeld aktiviert; **Leeren** nur bei vorhandenen Ergebnissen. Laufende Such-/Prüfvorgänge behalten ihre bisherigen Bedienregeln.
- Negativtester: Mehrere markierte Dateien können gemeinsam ignoriert oder wieder freigegeben werden, wenn alle denselben Ignorierstatus besitzen; bei gemischtem Status bleibt der Button deaktiviert. Die `ignore.txt` wird je betroffenem Ordner aktualisiert, Mehrfachauswahl nach dem Aktualisieren beibehalten. **Datei öffnen** bleibt auf genau eine Auswahl beschränkt.
- Negativtester: Die Statuszeile zeigt für **Fragmente**, **vermutlich ohne Text**, **leere Dateien** und **Lesefehler** jeweils die Anzahl ignorierter Einträge in Klammern (z. B. `14 Fragmente (9 ignoriert)`). Nach Ignorieren oder Aufheben wird die Zusammenfassung sofort aktualisiert.
- Negativtester: Startfenster von 1000 × 650 auf 900 × 560 Pixel verkleinert (Mindestgröße 800 × 480); Filterauswahl kompakter gestaltet.
- Negativtester: Ergebnisliste und beide Scrollleisten in einem gemeinsamen Rahmen angeordnet, sodass die Scrollleisten direkt an der Liste sitzen.
- Negativtester: Alle drei Ergebnisspalten (**Status**, **Dateipfad**, **Hinweis**) passen sich nach der Analyse und nach jedem Filterwechsel an die sichtbaren Inhalte an; lange Einträge bleiben horizontal scrollbar.
- Info-Fenster des TB2-Textfinders: **„Was ist neu? / Versionsverlauf“** öffnet ein natives, scrollbareres Fenster mit dem lokal eingebundenen Changelog (offline).
- Die Schaltflächen **Was ist neu?**, **GitHub**, **MIT-Lizenz** und **Schließen** sind platzsparend in einer Zeile angeordnet.
- Info-, Versionsverlauf- und Lizenztext verwenden einheitlich die Tk-Standardschrift statt unterschiedlicher Text-Schriften.
- Das Changelog zeigt nur veröffentlichte Einträge bis einschließlich der installierten Version; unveröffentlichte und neuere Einträge werden ausgeblendet.
- Lokale BAT-Builds und beide GitHub-Actions-Builds binden `CHANGELOG.md` in die EXE-Dateien ein.
- Info-Fenster wieder kompakter gestaltet.
- **Windows-Praxistest steht noch aus.** Such- und Erkennungslogik unverändert.

## [1.8.8] – 2026-11-19

### Build-Automatisierung
- GitHub Actions: Manuell startbarer Windows-Test-Build für beide EXE-Dateien ergänzt und erfolgreich unter Windows getestet.
- Die EXE-Dateien stehen als gemeinsames Workflow-Artefakt 14 Tage zum Download bereit.
- Separater Release-Workflow ergänzt, der bei Veröffentlichung eines GitHub-Releases beide EXE-Dateien aus dem Release-Tag baut und als Release-Assets hochlädt.
- Der automatische Release-Upload ist noch nicht praktisch getestet; erster Test mit Release 1.8.8 vorgesehen.
- Programmversionen von TB2-Textfinder und TB2-Negativtester auf 1.8.8 angehoben. Keine Änderungen an der Suchlogik.

## [1.8.7] – 2026-11-19

### Oberfläche und Bedienung
- Im Info-Fenster des TB2-Textfinders die Schaltfläche **„GitHub-Projekt öffnen“** ergänzt. Sie öffnet das öffentliche Projekt-Repository im Standardbrowser.
- Gemeinsames Modul `tb2_window_position.py` zur Fensterzentrierung ergänzt, ohne zusätzliche Python-Abhängigkeiten.
- Hauptfenster von TB2-Textfinder und TB2-Negativtester werden auf dem Monitor unter dem Mauszeiger zentriert. Info- und MIT-Lizenzfenster werden über ihrem jeweiligen Elternfenster positioniert; der nutzbare Monitorbereich wird berücksichtigt.
- Startgröße des TB2-Textfinders von **940 × 600** auf **800 × 520 Pixel** reduziert; Mindestgröße **720 × 420 Pixel** unverändert.
- Spalte **„Dateipfad“** in der Trefferliste passt ihre Breite an die gefundenen Pfade an; bei kurzen Inhalten wird unnötiges horizontales Scrollen vermieden. Die Anpassung erfolgt auch bei Teilergebnissen nach einem Suchabbruch.
- Trefferliste und Scrollleisten in einen eigenen Layout-Rahmen verschoben. Die vertikale Scrollleiste liegt direkt an der Liste; die horizontale befindet sich unmittelbar darunter.
- Gemeinsames Modul `tb2_app_identity.py` ergänzt: eigene Windows-Anwendungskennungen für Textfinder und Negativtester sowie ausdrückliche Zuweisung von `logo.ico` als Tkinter-Fenstersymbol.
- Windows-Taskleistenicon korrigiert: Zusätzlich werden `ICON_SMALL` und `ICON_BIG` über `WM_SETICON` am Tkinter-Fenster und dessen Windows-Wrapper gesetzt. Das behebt das zuvor angezeigte blaue Tkinter-Standardsymbol.

### Praxistests und Hinweise
- GitHub-Schaltfläche unter Windows erfolgreich getestet.
- Fensterzentrierung auf einem Monitor erfolgreich getestet; Mehrmonitorbetrieb noch nicht praktisch geprüft.
- Dynamische Spaltenbreite, kompaktere Startgröße und bündige Scrollleisten unter Windows erfolgreich getestet.
- Taskleistenicon unter Windows erfolgreich getestet: Sowohl beim Start über die BAT-Datei als auch bei der neu erstellten EXE wird nun das festgelegte Programmsymbol angezeigt. Die vorherige Lösung mit Tkinter-Icon und Anwendungskennung allein hatte das Problem noch nicht behoben.
- Die Position von Windows-Systemdialogen wird teilweise vom Betriebssystem bestimmt und kann nicht in jedem Fall exakt zentriert werden.
- Änderungen betreffen die Oberfläche; die Such- und Erkennungslogik bleibt unverändert.

### Versionierung und Repository
- Versionsangaben von TB2-Textfinder und TB2-Negativtester auf **1.8.7** gesetzt.
- GitHub-Schaltfläche über Pull Request #8 von `dev` nach `main` übernommen. Die weiteren Oberflächenänderungen befinden sich derzeit im Entwicklungsbranch `dev`.

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
