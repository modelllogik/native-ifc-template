# Material categories · Materialkategorien

*List of the material categories of `native-ifc-template` v0.3.0, German and English.*

Every material in the template carries a **category** in `IfcMaterial.Category`. The
drawing style hatches a cut layer by this category (`style/din.css`, section 4), not by
the material name. A new material therefore only needs one of the codes below.

**Principle:** the hatch follows the **material**, the line weight follows the
**construction** (structural or finishing). This list is ordered by material.
Hatches and line weights are not part of it; they stay in the drawing style.

**Per category:**
- **Code:** the word in `IfcMaterial.Category` and in the CSS class
  `layer-material-category-…`. Only a–z, A–Z and 0–9, because Bonsai removes everything
  else from class names. A code does not change once released.
- **Name** in German and English.
- **Description** in German and English, in our own words. Standards (DIN 1356-1 for the
  drawing, soil standards for the soil types) are referred to, not quoted.
- **Parent:** for subcategories. CSS knows no parents, so every subcategory has its own
  rule in `din.css`.
- **In the template:** the materials of `template/native_template.ifc` with this category.

The English names and descriptions are proposals, not official translations. Reviews by
native speakers are welcome as an issue or pull request.

**Changed in v0.3.0:** new `Bahnen` (vapour control layer, roof underlay and PE film were
under `Abdichtung`); soil types below `Erdreich`; **the former `Kies` is now
`Schuettung`**, and `Kies` is the soil type. Own materials with category `Kies` that
mean placed gravel should be changed to `Schuettung`.

## Materials of the structure · Baustoffe der Konstruktion

### `Mauerwerk` · Mauerwerk · Masonry
- **de:** Bauteil aus einzelnen Steinen, die im Verband mit Mörtel oder Kleber gefügt sind, etwa Ziegel, Kalksandstein, Porenbeton oder Leichtbeton.
- **en:** Element built from individual units laid in a bond with mortar or adhesive, such as clay brick, calcium silicate, aerated concrete or lightweight concrete blocks.
- **In the template:** Hochlochziegel_Mat, Kalksandstein

### `Beton` · Beton, unbewehrt · Plain concrete
- **de:** Beton ohne Bewehrung, etwa für Sauberkeitsschichten, Unterbeton oder einfache Fundamente.
- **en:** Concrete without reinforcement, for example blinding layers, sub-base concrete or simple footings.
- **In the template:** Beton C25/30

### `Stahlbeton` · Stahlbeton · Reinforced concrete
- **de:** Beton mit eingelegter Bewehrung aus Betonstahl, der Zug- und Druckkräfte gemeinsam aufnimmt; Ortbeton und Fertigteile.
- **en:** Concrete with embedded steel reinforcement that carries tension and compression together; cast in place or precast.
- **In the template:** Stahlbeton

### `Holz` · Holz · Timber
- **de:** Vollholz und verklebtes Bauholz wie Brettschichtholz, als tragendes Bauteil oder als Schalung, Rahmen und Blatt von Türen und Fenstern.
- **en:** Solid and glued structural timber such as glulam, used for load-bearing members or as boarding, frames and leaves of doors and windows.
- **In the template:** Sichtschalung, Nadelholz C24, Brettschichtholz GL24h, Holz Rahmen, Holz Blatt

### `Stahl` · Stahl · Steel
- **de:** Baustahl in Profilen, Rohren und Blechen, auch verzinkt.
- **en:** Structural steel as sections, tubes and plates, also galvanised.
- **In the template:** Baustahl S235, Stahl verzinkt

## Boards, layers and finishes · Platten, Schichten und Bekleidungen

### `Holzwerkstoff` · Holzwerkstoff · Wood-based panel
- **de:** Platten aus zerkleinertem oder geschichtetem Holz mit Bindemittel, etwa OSB, Spanplatte, Sperrholz oder Faserplatte.
- **en:** Panels made from chipped, stranded or layered wood with a binder, such as OSB, particleboard, plywood or fibreboard.
- **In the template:** OSB-Platte

### `Trockenbau` · Trockenbau · Drywall
- **de:** Platten für Wände, Vorsatzschalen und Decken im Trockenbau, etwa Gipskarton- und Gipsfaserplatten.
- **en:** Boards for partitions, linings and ceilings in dry construction, such as gypsum plasterboard and gypsum fibreboard.
- **In the template:** Gipskartonplatte

### `Putz` · Putz, Mörtel · Plaster, render, mortar
- **de:** Auf Wand oder Decke aufgetragene Beschichtung aus mineralischem oder organischem Mörtel, innen und außen, einschließlich Sockelputz.
- **en:** Coating of mineral or organic mortar applied to walls or ceilings, inside and outside, including plinth render.
- **In the template:** Kalkzementputz, Außenputz, Sockelputz

### `Estrich` · Estrich · Screed
- **de:** Auf dem Rohboden oder auf einer Dämmschicht eingebrachte Schicht, die Lasten verteilt und den Untergrund für den Belag bildet.
- **en:** Layer laid on the structural floor or on an insulation layer that spreads loads and forms the base for the floor finish.
- **In the template:** Zementestrich

### `Belag` · Belag · Floor and paving finish
- **de:** Oberste, begangene oder befahrene Schicht einer Fläche, innen wie Parkett und Fliesen, außen wie Pflaster und Platten.
- **en:** Top layer of a surface that is walked or driven on: inside such as parquet and tiles, outside such as paving blocks and slabs.
- **In the template:** Parkett, Fliesen, Betonpflaster

### `Dachdeckung` · Dachdeckung · Roofing
- **de:** Wasserführende äußere Schicht geneigter Dächer aus einzelnen Elementen, etwa Dachziegel, Dachsteine oder Schiefer.
- **en:** Water-shedding outer layer of pitched roofs made of individual units, such as clay tiles, concrete tiles or slate.
- **In the template:** Dachziegel

## Insulation, waterproofing, membranes · Dämmung, Abdichtung, Bahnen

### `Daemmung` · Dämmung · Insulation
- **de:** Dämmstoffe gegen Wärme- und Schallübertragung in Wand, Dach und Boden, etwa Mineralwolle, Holzfaser, EPS und die Dämmplatten eines WDVS.
- **en:** Materials that reduce heat and sound transmission in walls, roofs and floors, such as mineral wool, wood fibre, EPS and the boards of an ETICS.
- **In the template:** WDVS, Holzfaserplatte, Mineralwolle, EPS Ausgleichsdämmung, Trittschalldämmung

### `Perimeterdaemmung` · Perimeterdämmung · Perimeter insulation
- **Parent:** `Daemmung`
- **de:** Druckfeste, feuchteunempfindliche Dämmung auf der Außenseite erdberührter Bauteile, etwa XPS oder Schaumglas.
- **en:** Compression-resistant, moisture-resistant insulation on the outside of elements in contact with the ground, such as XPS or cellular glass.
- **In the template:** XPS Perimeter

### `Abdichtung` · Abdichtung · Waterproofing
- **de:** Schicht, die ein Bauteil dauerhaft gegen Wasser und Bodenfeuchte schützt, etwa Bitumen- oder Kunststoffbahnen und flüssig aufgebrachte Abdichtungen.
- **en:** Layer that permanently protects an element against water and ground moisture, such as bituminous or synthetic sheets and liquid-applied waterproofing.
- **In the template:** Bitumenbahn

### `Bahnen` · Bahnen und Folien · Membranes and foils
- **de:** Dünne Bahnen und Folien, die keine Abdichtung sind, sondern Dampf, Luft oder Wind bremsen, Schichten trennen oder als Unterdeckung dienen, etwa Dampfbremsen, Unterdeckbahnen und Trennfolien.
- **en:** Thin sheets and foils that are not waterproofing but control vapour, air or wind, separate layers or serve as roof underlay, such as vapour control layers, roof underlays and separating foils.
- **In the template:** Dampfbremse, Unterdeckbahn, PE-Folie

## Other materials · Weitere Baustoffe

### `Glas` · Glas · Glass
- **de:** Flachglas in Fenstern, Türen und Verglasungen, einfach oder als Mehrscheiben-Isolierglas.
- **en:** Flat glass in windows, doors and glazing, single or as insulating glass units.
- **In the template:** Floatglas

### `Metall` · Metall (NE, Blech) · Non-ferrous metal, sheet metal
- **de:** Nichteisenmetalle wie Aluminium, Kupfer und Zink, meist als Blech oder Profil, etwa für Dachentwässerung, Anschlüsse und Rahmen.
- **en:** Non-ferrous metals such as aluminium, copper and zinc, mostly as sheet or profile, for example for roof drainage, flashings and frames.
- **In the template:** Aluminium, Kupfer

### `Kunststoff` · Kunststoff · Plastics
- **de:** Bauteile und Profile aus Kunststoff, etwa Fenster- und Türrahmen aus PVC oder Kunststoffplatten.
- **en:** Components and profiles made of plastics, such as PVC window and door frames or plastic sheets.
- **In the template:** Kunststoff (PVC), Kunststoff Rahmen, Kunststoff Blatt

## Ground · Gelände

### `Schuettung` · Schüttung, Kies · Granular fill, gravel
- **de:** Eingebaute lose Schüttung aus Kies oder Splitt, etwa als Dränschicht, Kiesbett oder Auflast auf Flachdächern. Gewachsener Kies ist die Bodenart `Kies`.
- **en:** Placed loose fill of gravel or chippings, for example as drainage layer, gravel bed or ballast on flat roofs. Natural gravel is the soil type `Kies`.
- **In the template:** Kies 16/32
- *Code until v0.2.0: `Kies`.*

### `Erdreich` · Erdreich, Boden · Soil
- **de:** Gewachsener oder angefüllter Boden am und unter dem Bauwerk. Oberbegriff für die Bodenarten unten; wo die Bodenart unbekannt ist, bleibt es bei `Erdreich`.
- **en:** Natural or backfilled ground next to and below the building. Parent of the soil types below; where the soil type is unknown, `Erdreich` is used.
- **In the template:** Erdreich

#### `Oberboden` · Oberboden, Mutterboden · Topsoil
- **Parent:** `Erdreich`
- **de:** Oberste, humose und belebte Bodenschicht, die vor dem Bauen gesondert abgetragen, gelagert und wieder eingebaut wird.
- **en:** Uppermost humus-rich, biologically active soil layer that is stripped, stored and reused separately before construction.
- **In the template:** Oberboden

#### `BindigerBoden` · Bindiger Boden · Cohesive soil
- **Parent:** `Erdreich`
- **de:** Boden, dessen Verhalten vom feinkörnigen Anteil (Ton, Schluff) bestimmt wird; formbar, wenig durchlässig, empfindlich gegen Wasser und Frost.
- **en:** Soil whose behaviour is governed by its fine-grained share (clay, silt); plastic, of low permeability, sensitive to water and frost.
- **In the template:** Bindiger Boden

##### `Lehm` · Lehm · Loam
- **Parent:** `BindigerBoden`
- **de:** Gemisch aus Sand, Schluff und Ton.
- **en:** Mixture of sand, silt and clay.
- **In the template:** Lehm

##### `Ton` · Ton · Clay
- **Parent:** `BindigerBoden`
- **de:** Sehr feinkörniger, plastischer Boden, im feuchten Zustand knetbar und nahezu wasserundurchlässig.
- **en:** Very fine-grained, plastic soil, mouldable when moist and almost impermeable.
- **In the template:** Ton

##### `Schluff` · Schluff · Silt
- **Parent:** `BindigerBoden`
- **de:** Feinkörniger Boden zwischen Ton und Sand, wenig plastisch, stark frost- und wasserempfindlich.
- **en:** Fine-grained soil between clay and sand, of low plasticity, highly sensitive to frost and water.
- **In the template:** Schluff

#### `NichtbindigerBoden` · Nichtbindiger Boden · Non-cohesive soil
- **Parent:** `Erdreich`
- **de:** Körniger Boden ohne Zusammenhalt zwischen den Körnern, gut durchlässig und wenig wasserempfindlich.
- **en:** Granular soil without cohesion between the grains, permeable and of low sensitivity to water.
- **In the template:** Nichtbindiger Boden

##### `Sand` · Sand · Sand
- **Parent:** `NichtbindigerBoden`
- **de:** Nichtbindiger Boden aus Körnern im Sandbereich, fein bis grob.
- **en:** Non-cohesive soil of sand-sized grains, fine to coarse.
- **In the template:** Sand

##### `Kies` · Kies (Bodenart) · Gravel (soil type)
- **Parent:** `NichtbindigerBoden`
- **de:** Gewachsener nichtbindiger Boden aus Körnern im Kiesbereich. Eingebauter Kies als Schüttung ist `Schuettung`.
- **en:** Natural non-cohesive soil of gravel-sized grains. Placed gravel as fill is `Schuettung`.
- **In the template:** Kies, gewachsen

---

**28 categories** (20 for building materials, 8 soil types and groups).
In IFC 4.3 the soil types can also classify an `IfcGeotechnicalStratum`; the template is
IFC4 and does not use that yet.
