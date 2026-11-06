# Anleitung für Ausbilder

*Deutsche Anleitung zu `native-ifc-template`. Stand: v0.2.0. Die Abschnitte zu Installation, Zeichenstil, Schraffur und Plankopf sind ausgeführt, die übrigen folgen mit späteren Releases.*

## Worum es geht

Die Vorlage ist eine IFC-Datei, in der direkt modelliert wird. Es gibt keinen Export aus einem Autorenformat und keine Rundreise. Die Pläne werden aus dem Modell abgeleitet und folgen den Darstellungsregeln der DIN 1356.

Für die Arbeit mit der Vorlage sind keine Programmierkenntnisse nötig. Für die Skripte genügt es, eine Zeile in der Eingabeaufforderung einzutippen oder eine Datei in Blender auszuführen.

## Abnahmekriterium dieser Anleitung

Sie ist gelungen, wenn Sie **ohne Rückfrage** eine eigene Schraffur oder einen eigenen Schichtaufbau ergänzen können.
Wenn das nicht klappt, ist die Anleitung unvollständig. Bitte melden Sie die Stelle als Issue, gern auf Deutsch.

## 1 · Installation

Erprobt mit Blender 5.2.0 LTS, Bonsai 0.9.1 und IfcOpenShell 0.9.1a261028.

1. Blender installieren, darin Bonsai über *Edit → Preferences → Get Extensions*.
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

**Was diese Fassung noch nicht kann:** Schraffuren als echte Linien für den Druck, das Holzkreuz, das Band der Abdichtung, Maßzahlen in deutscher Schreibweise und Maßlinienmarker. Dafür braucht es eine Nachbearbeitung der Zeichnung; sie folgt in einem späteren Release. **Linienstärken und Musterabstände vor dem Einsatz an einem Ausdruck prüfen**, nicht am Bildschirm.

## 4 · Eine Schraffur ergänzen

Schraffur und Linienstärke hängen an der **Kategorie** eines Materials (`IfcMaterial.Category`), nicht an seinem Namen. Bonsai schreibt die Kategorie jeder geschnittenen Schicht als Klasse `layer-material-category-…` in die Zeichnung.

**Fall A – ein neues Material mit vorhandener Darstellung** (zum Beispiel ein weiterer Mauerstein):

1. Das Material in Bonsai anlegen.
2. Als *Category* einen Wert aus Abschnitt 4 von `style/din.css` eintragen, genau so geschrieben, also `Daemmung` und nicht `Dämmung`. Bonsai übernimmt in Klassennamen nur Buchstaben a–z, A–Z und Ziffern.
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
