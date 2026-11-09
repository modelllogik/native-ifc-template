# Anleitung für Ausbilder

*Deutsche Anleitung zu `native-ifc-template`. Stand: v0.3.0. Die Abschnitte zu Vorbereitung, Installation, Zeichenstil, Schraffur und Plankopf sind ausgeführt, die übrigen folgen mit späteren Releases.*

## Worum es geht

Die Vorlage ist eine IFC-Datei, in der direkt modelliert wird. Es gibt keinen Export aus einem Autorenformat und keine Rundreise. Die Pläne werden aus dem Modell abgeleitet und folgen den Darstellungsregeln der DIN 1356.

Für die Arbeit mit der Vorlage sind keine Programmierkenntnisse nötig. Für die Skripte genügt es, eine Zeile in der Eingabeaufforderung einzutippen oder eine Datei in Blender auszuführen.

## Abnahmekriterium dieser Anleitung

Sie ist gelungen, wenn Sie **ohne Rückfrage** eine eigene Schraffur oder einen eigenen Schichtaufbau ergänzen können.
Wenn das nicht klappt, ist die Anleitung unvollständig. Bitte melden Sie die Stelle als Issue, gern auf Deutsch.

## 0 · Vorbereitung: Blender und Bonsai

Diese Anleitung setzt zwei Programme voraus. Beide sind kostenlos und quelloffen und laufen unter Windows, macOS und Linux.

- **[Blender](https://www.blender.org)** ist ein 3D-Programm, ursprünglich für Animation und Visualisierung.
- **[Bonsai](https://bonsaibim.org)** ist eine Erweiterung für Blender. Sie macht aus Blender ein BIM-Programm, das IFC-Dateien direkt öffnet, bearbeitet und speichert. Dahinter steht die Bibliothek IfcOpenShell.

Gearbeitet wird also immer in Blender, mit eingeschaltetem Bonsai. Die Oberfläche ist englisch; lassen Sie Blender auf Englisch, dann passen die Menünamen dieser Anleitung und der Bonsai-Dokumentation.

**Was Sie brauchen:** einen Rechner, der die [Anforderungen von Blender](https://www.blender.org/download/requirements/) erfüllt, eine Maus mit Mausrad und Internetzugang für die Installation der Erweiterungen. Administratorrechte sind nicht nötig, wenn Sie die portable Fassung nehmen (Schritt 1).

### Schritt 1 · Blender installieren

1. Auf [blender.org/download](https://www.blender.org/download/) die Fassung **Blender 5.2 LTS** laden. LTS heißt Langzeitfassung; sie wird bis Juli 2028 gepflegt.
2. Unter Windows gibt es zwei Wege:
   - **Installer (.msi):** ausführen wie jedes Programm. Braucht Administratorrechte.
   - **Portable (.zip):** in einen eigenen Ordner entpacken, etwa einen Ordner `Blender` unter *Dokumente*, und dort `blender.exe` starten. Geht ohne Administratorrechte, zum Beispiel im Schulungsraum.
3. Blender starten. Der Begrüßungsbildschirm kann mit einem Klick daneben geschlossen werden.

### Schritt 2 · Online-Zugang für Erweiterungen erlauben

*Edit → Preferences → Get Extensions* öffnen und **Allow Online Access** drücken. Ohne diese Freigabe findet Blender keine Erweiterungen im Internet.

### Schritt 3 · Bonsai installieren

Bonsai gibt es in zwei Fassungen: eine stabile im Erweiterungsverzeichnis von Blender und eine tägliche Entwicklerfassung (*Unstable*). **Vorlage und Zeichenstil sind mit der täglichen Fassung erprobt** (Bonsai 0.9.1), deshalb beschreibt diese Anleitung diese. Die stabile Fassung 0.9.0 ist mit der Vorlage nicht erprobt.

1. In *Edit → Preferences → Get Extensions* oben rechts **Repositories** aufklappen, auf **+** klicken und **Add Remote Repository** wählen.
2. Als *URL* eintragen:

   ```
   https://raw.githubusercontent.com/IfcOpenShell/bonsai_unstable_repo/main/index.json
   ```

   Das Häkchen bei **Check for Updates on Startup** setzen und bestätigen.
3. Oben links im Suchfeld „Bonsai“ eingeben. Unter *Available* erscheinen **zwei Einträge „Bonsai“**: die tägliche Fassung aus dem eben angelegten Repository und die stabile aus extensions.blender.org. Beide sehen gleich aus. Klappen Sie sie mit dem Pfeil links vom Namen auf und klicken Sie bei dem Eintrag auf **Install**, bei dem unten unter *Repository* `raw.githubusercontent.com` steht (*Version* 0.9.1 oder höher), nicht `extensions.blender.org` (*Version* 0.9.0). Der Download ist groß und dauert einen Moment.
4. Prüfen, dass beim installierten Bonsai als Repository `raw.githubusercontent.com` steht und nicht `extensions.blender.org`.
5. Blender schließen und neu starten.

So steht es auch in der [Installationsanleitung von Bonsai](https://docs-unstable.bonsaibim.org/guides/development/installation.html), Abschnitt *Unstable installation*.

### Schritt 4 · Prüfen, ob alles läuft

Im Menü **File** gibt es jetzt Einträge für IFC-Projekte, etwa *Open IFC Project*. Ist das so, ist Bonsai eingeschaltet. Fehlt der Eintrag: *Edit → Preferences → Add-ons*, nach „Bonsai“ suchen und das Häkchen setzen. Dort steht auch die Versionsnummer, die Sie bei Rückfragen angeben.

### Aktualisieren

Die tägliche Fassung erscheint jeden Tag neu. Mit dem Häkchen aus Schritt 3 meldet Blender beim Start unten rechts in der Statusleiste, wenn es eine neue gibt. Aktualisiert wird in *Edit → Preferences → Get Extensions* mit dem Knopf *Update*, danach Blender neu starten. Eine neue Fassung kann etwas anders machen als die vorige: **Aktualisieren Sie nicht unmittelbar vor dem Unterricht**, sondern prüfen Sie vorher in Ruhe, ob Vorlage und Zeichnungen noch wie gewohnt funktionieren.

### Die ersten Handgriffe in Blender

Blender bedient sich anders als ein CAD-Programm. Für den Anfang genügen diese Griffe im 3D-Fenster:

- **Mittlere Maustaste gedrückt halten und ziehen:** Ansicht drehen.
- **Umschalt + mittlere Maustaste:** Ansicht verschieben.
- **Mausrad:** zoomen.
- **Taste N:** Seitenleiste ein- und ausblenden. Dort liegen die Reiter von Bonsai und Add-ons.
- **Ziffernblock 7 / 1 / 3:** Blick von oben, von vorn, von rechts.

Weiterführend: die [Dokumentation von Bonsai](https://docs.bonsaibim.org) und das [Handbuch von Blender](https://docs.blender.org/manual/). Fragen zu Bonsai beantwortet die Gemeinschaft im [OSArch-Forum](https://community.osarch.org) (englisch).

## 1 · Installation

Erprobt mit Blender 5.2.0 LTS, Bonsai 0.9.1 und IfcOpenShell 0.9.1a261106.

1. Blender und Bonsai installieren wie in Abschnitt 0 beschrieben.
2. In den Einstellungen von Bonsai den **Datenordner** nachsehen (*Data Dir*). Unter Windows ist es `%APPDATA%\bonsai\bonsai\data`.
3. `template/native_template.ifc` nach `<Datenordner>/templates/projects/` kopieren.
4. Den Zeichenstil installieren (Abschnitt 3).
5. Blender neu starten.

## 2 · Ein Projekt aus der Vorlage beginnen

In Bonsai *New Project* wählen und die Vorlage `native_template` auswählen. **Danach das Projekt speichern und neu öffnen.** In Bonsai 0.9.1 fehlen sonst den Stilen und Typen der Vorlage die Blender-Gegenstücke: Der Stileditor meldet einen Fehler, und Türen oder Fenster lassen sich nicht setzen ([#10134](https://github.com/IfcOpenShell/IfcOpenShell/issues/10134)).

## 3 · Pläne ableiten: der Zeichenstil

Bonsai zeichnet Grundriss, Schnitt und Ansicht aus dem Modell als SVG-Datei und gestaltet sie mit einer CSS-Datei. Der Zeichenstil in `style/` sorgt für Linienstärken, Schraffuren, Schrift und Planrahmen nach DIN 1356-1, gerechnet für **1:50**.

**Wichtig vorab:** Bonsai legt die Stildateien eines Projekts beim ersten Erzeugen einer Zeichnung an, im Ordner `drawings/assets/` neben der Projektdatei. Es kopiert sie dabei aus dem Datenordner. Wird der Stil im Datenordner installiert, gilt er für jedes Projekt, das noch keine Zeichnung hat. Für ein Projekt mit Zeichnungen installieren Sie ihn zusätzlich dort.

**Im Datenordner** (Eingabeaufforderung im Ordner des Repositorys):

```
python scripts/install_style.py --data-dir "%APPDATA%\bonsai\bonsai\data" --bonsai-assets <Bonsai>\bim\data\assets
```

Für `<Bonsai>` steht der Ordner, in dem Bonsai installiert ist. Einfacher geht es in Blender: `scripts/install_style.py` im Text-Editor öffnen, oben `import sys; sys.argv = ["", "--data-dir", r"C:\Users\…\AppData\Roaming\bonsai\bonsai\data"]` ergänzen und *Run Script* wählen. Dort findet das Skript Bonsais eigene Dateien selbst.

**In einem Projekt mit Zeichnungen:**

```
python scripts/install_style.py --project-assets <Projektordner>\drawings\assets
```

Danach die Zeichnungen in Bonsai neu erzeugen.

Das Skript **ersetzt Bonsais Dateien nicht**. Es hängt `din.css` an Bonsais `default.css` an und ergänzt die Muster in `patterns.svg`. Ein zweiter Lauf ersetzt den früheren Zusatz und ändert sonst nichts. Enthält eine Datei schon einen DIN-Zusatz anderer Herkunft, lässt das Skript sie unverändert und meldet das.

**Planrahmen:** Das Skript kopiert die Rahmen `DIN_A4_hoch` bis `DIN_A0_quer` in den Datenordner. Beim Anlegen eines Blatts stehen sie in der Auswahl. Vorhandene Rahmen ersetzt es nur mit `--overwrite`.

**Was diese Fassung noch nicht kann:** Schraffuren als echte Linien für den Druck, das Holzkreuz, das Band der Abdichtung, Maßzahlen in deutscher Schreibweise und Maßlinienmarker. Dafür braucht es eine Nachbearbeitung der Zeichnung; sie entsteht im Add-on [bonsai-btk](https://github.com/modelllogik/bonsai-btk). **Linienstärken und Musterabstände vor dem Einsatz an einem Ausdruck prüfen**, nicht am Bildschirm.

**Von v0.2.0 auf v0.3.0:** die neue `native_template.ifc` kopieren und `install_style.py` erneut ausführen, bei Projekten mit Zeichnungen auch mit `--project-assets`. Die Kategorie `Kies` heißt jetzt **`Schuettung`**; `Kies` steht für die Bodenart. Eigene Materialien mit der Kategorie `Kies`, die eingebauten Kies meinen (Dränschicht, Kiesbett), in Bonsai auf `Schuettung` umstellen.

## 4 · Eine Schraffur ergänzen

Schraffur und Linienstärke hängen an der **Kategorie** eines Materials (`IfcMaterial.Category`), nicht an seinem Namen. Bonsai schreibt die Kategorie jeder geschnittenen Schicht als Klasse `layer-material-category-…` in die Zeichnung.

**Fall A – ein neues Material mit vorhandener Darstellung** (zum Beispiel ein weiterer Mauerstein):

1. Das Material in Bonsai anlegen.
2. Als *Category* einen Wert aus Abschnitt 4 von `style/din.css` eintragen, genau so geschrieben, also `Daemmung` und nicht `Dämmung`. Bonsai übernimmt in Klassennamen nur Buchstaben a–z, A–Z und Ziffern. Welche Kategorie wofür steht, beschreibt die zweisprachige Liste [`docs/material-categories.md`](../material-categories.md), zum Beispiel `Bahnen` für Dampfbremsen und Folien, `Schuettung` für eingebauten Kies und die Bodenarten unter `Erdreich`.
3. Zeichnungen neu erzeugen. Am Stil ist nichts zu ändern.

**Fall B – eine neue Darstellung** (eine Kategorie, die es noch nicht gibt):

1. In `style/din.css`, Abschnitt 4, eine Zeile kopieren und darin ändern: den Namen der Kategorie, das Muster in `url(#…)`, die Linienstärke (`0.50` tragend, `0.25` sonst) und den Legendentext im Kommentar.
2. Braucht die Kategorie ein neues Muster: in `style/din-patterns.svg` einen `<pattern>`-Block kopieren, die `id` auf `din-NAME` ändern und die Linien anpassen. Maße sind Millimeter auf dem Blatt, Schraffurlinien 0,1 mm.
3. Kommentare in `din.css` **nur innerhalb der geschweiften Klammern** schreiben. Ein Kommentar zwischen zwei Regeln lässt Inkscape auf dem Blatt die folgende Regel verwerfen.
4. `install_style.py` erneut ausführen und die Zeichnungen neu erzeugen.

## 5 · Einen eigenen Plankopf einsetzen

Der mitgelieferte Plankopf enthält Platzhalter (Büro, Verfasser, Projekt, Kürzel). Tragen Sie Ihre Angaben in `style/titleblocks/parts/title_block.svg` ein, mit einem Texteditor oder mit Inkscape (Einheit mm). Danach `python scripts/build_titleblocks.py --overwrite` ausführen, das alle zehn Formate neu erzeugt, und `install_style.py` mit `--overwrite`. Die Regeln für eigene Planköpfe stehen im Kopf von `title_block.svg`. Planinhalt, Plan-Nr., Index und Datum füllt Bonsai aus den Angaben des Blatts.

Hat ein Projekt schon Blätter, liegen die Rahmen zusätzlich dort in `layouts/titleblocks/`. Bonsai nimmt dann diese Kopie.

## Noch nicht ausgeführt

- Wände, Decken und Öffnungen mit Typen aus der Vorlage
- Einen Schichtaufbau ergänzen
- Das Modell mit der IDS prüfen
- Einsatz im Unterricht: Bezug zu DIN 1356

## Lizenz

Diese Anleitung steht unter CC BY 4.0. Sie dürfen sie für Ihren Unterricht anpassen und weitergeben, mit Namensnennung.
