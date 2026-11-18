# Power-BI-Dashboard: Bauanleitung

Diese Anleitung beschreibt, wie das bestehende Dashboard
(`dashboard/energy_market_dashboard.pbix`) zu einem mehrseitigen Report ausgebaut
wird. Inhaltlich entspricht er dem [Web-Dashboard](../../docs/index.html).
Geschätzter Aufwand: 3–5 Stunden.

| Datei | Zweck |
|---|---|
| [`energy_theme.json`](energy_theme.json) | Farb- und Formatvorlage (Farben identisch zum Web-Dashboard) |
| [`measures.dax`](measures.dax) | Alle berechneten Spalten und Measures zum Kopieren |

---

## 0. Vorbereitung

1. Daten aktualisieren, falls noch nicht geschehen. Der zweite Befehl legt die Prognosetabellen an:
   ```bash
   python -m energy_analytics.pipeline
   python -m energy_analytics.dashboard_export
   ```
2. Öffne die `.pbix`-Datei und klicke unter **Start → Aktualisieren**.
3. Unter **Start → Daten abrufen** lädst du zusätzlich die Tabellen
   `forecast_predictions` und `model_metrics` sowie die Views `v_daily_summary`
   und `v_monthly_summary`. Verwende dieselbe Datenquelle wie für `energy_data`.
4. Importiere das Theme über **Ansicht → Designs → Nach Designs suchen →
   `energy_theme.json`**.

## 1. Datenmodell

```
dim_date (1) ──< energy_data (n)              über date
dim_date (1) ──< forecast_predictions (n)     über date
```

* **Power Query:** `dim_date[date]`, `energy_data[date]` und `forecast_predictions[date]`
  auf Datentyp **Datum** setzen, `timestamp_local` auf **Datum/Uhrzeit**.
* `dim_date` markierst du unter **Tabellentools → Als Datumstabelle markieren** (Spalte `date`).
  Das ist Voraussetzung für die Vorjahres-Measures.
* **Sortierung:** `month_name_de` nach `month`, `day_name_de` nach `day_of_week`,
  `EE-Klasse` nach `EE-Klasse Sort`.
* Lege die Tabelle `_Measures = { BLANK() }` an. Füge dort alle Measures aus
  `measures.dax` ein und blende die Spalte `Value` aus.
* Technische Spalten (`timestamp`, `price_lag_*`, `*_rolling_*`) blendest du in
  der Berichtsansicht aus.

## 2. Seitenaufbau (16:9, 1280 × 720)

Auf jeder Seite gilt derselbe Kopfbereich:
* Links der dynamische Titel (Textfeld mit Wert `[Titel Seite 1]`)
* Rechts drei **Slicer** im Kachelstil: `dim_date[year]`, `energy_data[season]`
  und `energy_data[Tagtyp]`
* Unter **Ansicht → Slicer synchronisieren** verknüpfst du die Slicer auf allen Seiten.
* Für die Navigation fügst du eine **Seitennavigator**-Schaltfläche ein
  (Einfügen → Schaltflächen → Navigator → Seitennavigator).

### Seite 1 – Marktüberblick

| Visual | Felder | Hinweise |
|---|---|---|
| 8 × **Karte (neu)** | `Ø Preis`, `Peak-Preis`, `Höchster Preis`, `Niedrigster Preis`, `Negative Stunden`, `EE-Anteil`, `Solar Capture Rate`, `Ø Tagesspanne` | Als Referenzbeschriftung: `Δ Preis ggü. Vorjahr Text`, `Zeitpunkt Höchstpreis`, `Zeitpunkt Tiefstpreis`, `Off-Peak-Preis` |
| **Liniendiagramm** | X: `dim_date[date]`, Y: `Ø Preis`, `Ø Preis 30 Tage gleitend` | Zoom-Schieberegler einschalten (X-Achse → Zoomschieberegler) |
| **Flächendiagramm** darunter | X: `dim_date[date]`, Y: `Ø Residuallast GW` | Gleiche Breite und Position wie das Liniendiagramm, damit beide synchron lesbar sind. **Keine** zweite Y-Achse verwenden |
| **Gruppiertes Säulendiagramm** | X: `month_name_de`, Legende: `year`, Y: `Ø Preis` | |
| **Gestapeltes Säulendiagramm + Linie** | X: `year_month`, Säulen: `Wind onshore TWh`, `Wind offshore TWh`, `Solar TWh`, Linie: `Last TWh` | Sekundäre Y-Achse **ausschalten**, damit alle Werte auf derselben TWh-Skala liegen |

### Seite 2 – Preismuster

| Visual | Felder | Hinweise |
|---|---|---|
| **Liniendiagramm** „Duck Curve“ | X: `energy_data[hour]`, Legende: `season`, Y: `Ø Preis` | Farben: Winter Blau, Frühling Grün, Sommer Orange, Herbst Gelb |
| **Matrix** Stunde × Monat | Zeilen: `hour`, Spalten: `month_name_de`, Werte: `Ø Preis` | Bedingte Formatierung → Hintergrundfarbe → Farbskala (hell → dunkelblau); Schriftfarbe gleich der Hintergrundfarbe ergibt eine reine Heatmap |
| **Matrix** Stunde × Wochentag | Zeilen: `hour`, Spalten: `day_name_de` | wie oben |
| **Säulendiagramm** Preisverteilung | X: `Preisklasse` (Typ: kategorisch), Y: `Stunden` | Datenfarben → bedingt: Orange, wenn `Preisklasse` < 0 |

### Seite 3 – Erneuerbare & Merit-Order

| Visual | Felder | Hinweise |
|---|---|---|
| **Punktdiagramm** | X: `residual_load`, Y: `price`, Details: `timestamp_local` | Für die Merit-Order-Kurve **Analyse → Trendlinie** ein. Hohe Dichte bleibt eingeschaltet |
| **Balkendiagramm** | Y: `EE-Klasse`, X: `Ø Preis` | Datenbeschriftungen ein; Farbe bedingt: Orange bei negativen Werten. Tooltip: `Anteil negative Stunden` |
| **Liniendiagramm** Marktwerte | X: `year_month`, Y: `Ø Preis`, `Wind-Capture-Preis`, `Solar-Capture-Preis` | Zeigt den Kannibalisierungseffekt von PV im Sommer |
| **Tabelle** | `Residuallast-Segment`, `Stunden`, `Ø Preis`, `Anteil negative Stunden` | |

### Seite 4 – Negative Preise

| Visual | Felder | Hinweise |
|---|---|---|
| 3 × **Karte** | `Negative Stunden`, `Anteil negative Stunden`, `Tage mit negativen Preisen` | Referenzbeschriftung: `Negative Stunden Vorjahr` |
| **Matrix als Kalender** | Zeilen: `year`, `month_name_de`, Spalten: `dim_date[day]`, Werte: `Negative Stunden` | Hintergrund-Farbskala 0 = Hellgrau → Maximum = Dunkelblau. Ergibt eine Kalender-Heatmap |
| **Säulendiagramm** | X: `hour`, Y: `Negative Stunden` | |
| **Liniendiagramm** | X: `month_name_de`, Legende: `year`, Y: `Negative Stunden` | |
| **Tabelle** Top-Tage | `dim_date[date]`, `day_name_de`, `Negative Stunden`, `Niedrigster Preis`, `Ø Preis` | Filter: Top N = 10 nach `Negative Stunden` |

### Seite 5 – Preisprognose

| Visual | Felder | Hinweise |
|---|---|---|
| 4 × **Karte** | `MAE XGBoost`, `RMSE XGBoost`, `Verbesserung ggü. Naiv`, `MAE Naiv (Vortag)` | Format: `Verbesserung` als Prozent |
| **Liniendiagramm** | X: `forecast_predictions[timestamp_local]`, Y: `Ist-Preis`, `Prognose XGBoost` | Zoomschieberegler ein; Prognose als gestrichelte Linie |
| **Balkendiagramm** Modellvergleich | `model_metrics[model]`, `MAE` | XGBoost blau hervorheben, die übrigen grau |
| **Säulendiagramm** | X: `forecast_predictions[hour]`, Y: `MAE XGBoost` | Fehler nach Tageszeit |

Die Seiten-Slicer sollen hier nicht wirken: Bearbeite unter **Format →
Interaktionen bearbeiten** die Slicer und stelle für diese Visuals „Keine“ ein.

### Seite 6 – Drillthrough „Tagesdetail“ (versteckt)

* Drillthrough-Feld: `dim_date[date]`
* Inhalt:
  * Liniendiagramm mit `hour` × `Ø Preis`
  * Gestapeltes Flächendiagramm mit `hour` × Wind, Solar und Last in GW
  * Karten für Tagesmittel, Minimum, Maximum und negative Stunden
* Titel: `[Titel Tagesdetail]`
* **Effekt:** Ein Rechtsklick auf einen Tag in jedem Datumsvisual öffnet
  „Drillthrough → Tagesdetail“.

### Optional: Tooltip-Seite

Lege eine Seite mit Seitengröße **QuickInfo** an. Sie enthält ein kleines
Stundenprofil (`hour` × `Ø Preis`) und die Kennzahlen `EE-Anteil` und
`Negative Stunden`. Hinterlege sie in den Liniendiagrammen unter
**Format → QuickInfo → Seite**.

## 3. Feinschliff

* Abstände einheitlich halten: 16 px zwischen den Visuals, 24 px Seitenrand.
* Jedes Visual erhält einen Titel, der eine Frage beantwortet, z. B.
  „Wann wird Strom negativ bepreist?“.
* Unter **Datei → Optionen → Aktuelle Datei → Berichtseinstellungen** aktivierst du
  „Visual-Header ausblenden in Leseansicht“.
* Speichere je Seite einen Screenshot unter `docs/images/powerbi_<seite>.png`
  und verlinke ihn in der README.
