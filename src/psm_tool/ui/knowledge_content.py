# ruff: noqa: E501

from __future__ import annotations

from textwrap import dedent


def _format_currency_snap(config_snapshot: dict) -> str:
    mapping = config_snapshot.get("default_currency_snap", {})
    if not isinstance(mapping, dict) or not mapping:
        return "- n/a"
    lines = [f"- {str(currency).upper()}: {value:g}" for currency, value in mapping.items()]
    return "\n".join(lines)


def get_knowledge_markdown_en(config_snapshot: dict, sav_available: bool) -> dict[str, str]:
    default_currency_snap = _format_currency_snap(config_snapshot)
    sav_text = (
        "CSV, XLSX, SAV (optional support is installed in this environment)."
        if sav_available
        else "CSV, XLSX. SAV support is optional; not installed in this environment."
    )

    return {
        "Overview": dedent(
            f"""
            # Knowledge & Methodology

            This section explains what the tool calculates, why it calculates it that way, and how to interpret the outputs. Everything here is deterministic and based on the tool’s implemented rules (no AI).

            ## What this tool does
            The tool supports two complementary views on pricing:

            - **Price perception (PSM / Van Westendorp):** derives an **acceptable price range** and key price points from four open price thresholds per respondent.
            - **Purchase intention (NMS-style extension):** derives a **purchase intention curve** and a **turnover index** from two purchase-intention questions anchored at each respondent’s “reasonable” and “expensive-but-acceptable” prices (or from an optional explicit price ladder, if provided).

            Use PSM to understand **perceived price boundaries**. Use Purchase Intention / Turnover to understand **reach vs. revenue trade-offs**.

            ## Typical workflow
            1) Upload a CSV/XLSX (optional SAV if enabled)
            2) Validate and review QC
            3) Inspect PSM chart and KPIs
            4) If PI data is present: inspect PI + Turnover (and optional profit proxy if enabled)
            5) Export PPTX / Excel for reporting

            ### Quick glossary
            - **Threshold questions:** “too cheap”, “reasonable”, “expensive but acceptable”, “too expensive”
            - **Accepted range:** the pricing window perceived as “fitting”
            - **Turnover index:** price × purchase intention, normalized to max = 100

            ### Supported file types (runtime)
            - {sav_text}
            """
        ).strip(),
        "PSM (Price Sensitivity Meter)": dedent(
            """
            # PSM (Price Sensitivity Meter)

            ## Inputs (per respondent)
            The PSM model uses four price thresholds:

            - **Too cheap:** below this price, the product may feel “too cheap” (quality doubt)
            - **Bargain / Reasonable:** up to this price, the product feels “good value”
            - **Expensive (still acceptable):** up to this price, the product feels expensive but still acceptable
            - **Too expensive:** above this price, the product is too expensive to consider

            ### Plausibility rule (strict)
            Respondents are considered valid for PSM only if:

            `too_cheap < bargain < expensive_acceptable < too_expensive`

            Invalid cases are excluded from PSM calculations and reported in the QC table.

            ## Curves (how the chart is built)
            On a price grid, the tool computes the share of respondents for each perception:

            - **Too Cheap(p):** share with `too_cheap >= p` (decreasing)
            - **Bargain(p):** share with `bargain >= p` (decreasing)
            - **Expensive(p):** share with `expensive_acceptable <= p` (increasing)
            - **Too Expensive(p):** share with `too_expensive <= p` (increasing)

            Derived:
            - **Not Bargain(p) = 100 − Bargain(p)**
            - **Not Expensive(p) = 100 − Expensive(p)**

            If a weight column is present, the tool uses weighted shares.

            ## Key points (intersections) and what they mean
            The tool finds intersections via linear interpolation:

            - **PMI (Point of Marginal Inexpensiveness):** Too Cheap × Not Bargain
              → lower acceptable price limit
            - **PME (Point of Marginal Expensiveness):** Too Expensive × Not Expensive
              → upper acceptable price limit
            - **OPP (Optimal Pricing Point):** Too Cheap × Too Expensive
              → minimal overall resistance (“too cheap” = “too expensive”)
            - **IDP (Indifference Pricing Point):** Bargain × Expensive
              → perceived “normal” / category-typical price center

            ### Accepted price range
            **Accepted Range = [PMI, PME]**

            A price inside this range is generally perceived as fitting.

            ### Price stress
            **Price Stress = OPP − IDP**

            Interpretation (rule of thumb):
            - Negative stress (OPP < IDP): weaker price image / higher resistance around “normal” prices
            - Positive stress (OPP > IDP): potential for premium positioning / acceptance of higher prices
            - Near zero: balanced and stable price image

            ## Intersection quality flags
            Intersections can have different statuses:

            - **clean:** curves cross (sign change) on the grid
            - **interval:** curves overlap for a price interval (the tool reports a range)
            - **closest:** curves do not cross on the grid (the tool reports the closest approach)

            If you see “interval” or “closest”, interpret KPIs with additional caution and review the curve shapes.
            """
        ).strip(),
        "Purchase Intention & Turnover": dedent(
            """
            # Purchase Intention & Turnover

            This section is available when purchase-intention data is present (either as respondent-level PI anchors or as an explicit price ladder).

            ## PI inputs (NMS-style, respondent level)
            Two PI questions are used:

            - PI at each respondent’s **bargain/reasonable** price: `pi_bargain_pct`
            - PI at each respondent’s **expensive acceptable** price: `pi_expensive_pct`

            Expected unit: **percent 0..100**.

            ### Base population and filters
            By default, purchase intention analysis uses:
            - **PSM-valid respondents only**, and
            - optionally a “high baseline interest” filter if available (e.g., `puki <= 2`; optionally `<= 3`)

            The QC section reports the resulting base sizes.

            ## Building a full PI (Trial) curve from two points
            To obtain a PI curve over a price grid, the tool uses a deterministic piecewise-linear model per respondent:

            (too_cheap, 0) → (bargain, PI_bargain) → (expensive_acceptable, PI_expensive) → (too_expensive, 0)

            These respondent-level curves are evaluated on the grid and averaged (weighted if weights are present).

            Important: This is a modeled curve, not a guarantee of real market demand.

            ## Turnover Index (0–100)
            Turnover is derived from price and purchase intention:

            - `revenue_raw(p) = price(p) × (PI(p)/100)`
            - `turnover_index(p) = revenue_raw(p) / max(revenue_raw) × 100`

            The maximum is marked as “Maximum Turnover”.

            ### Why Turnover Index can still look “fine” when PI looks wrong
            Because the turnover index is normalized to max=100, a PI scaling error (e.g., 0..1 instead of 0..100) can visually compress the PI curve while leaving the index curve shape mostly unchanged. If PI appears extremely small, check PI units.

            ## Optional: explicit price ladder PI
            If an explicit price ladder is provided (price → purchase_intention_pct), the tool will prioritize that curve instead of the NMS reconstruction, because it is directly measured across many price points.
            """
        ).strip(),
        "Quality & Grid": dedent(
            f"""
            # Quality & Grid

            ## Data quality checks (QC)
            The tool reports:
            - total respondents
            - PSM-valid count (strict ordering)
            - missingness per column
            - purchase intention base after filters (if applicable)
            - outlier and “suspicious units” warnings (if implemented)

            Recommended practice:
            - Segment results require adequate base sizes. Very small bases can produce unstable intersections.

            ## Price grid: auto vs manual
            PSM and PI curves are evaluated on a price grid.

            Auto grid behavior (default):
            - derive min/max from observed thresholds
            - choose a “nice” step size to create a smooth curve (roughly ~100 points)
            - apply currency snapping if enabled

            Manual override:
            - you can override min, max, and step to focus the chart on the relevant range (useful when outliers stretch the axis).

            ### Currency snapping (defaults)
            Default snap increments (from config):
            {default_currency_snap}

            Snapping makes axis labels and recommended prices easier to read and communicate.
            """
        ).strip(),
        "Exports & Privacy": dedent(
            """
            # Exports & Privacy

            ## Exports
            The tool can generate:
            - **PPTX** (charts embedded as images)
            - **Excel** (KPIs and curve tables for reproducibility)

            ### Static chart rendering requirement
            To embed charts into PPTX, the tool renders Plotly figures to PNG.
            This requires a working **Chrome/Chromium** environment. If missing, the export preflight will show an actionable error.

            ## Privacy posture
            - Uploaded files are processed **in-memory** by default.
            - The public demo should not be used for sensitive client data.
            - For client work, run the tool locally or on a controlled internal server.
            - The repository is configured to avoid committing private datasets (use `data_private/` locally).
            """
        ).strip(),
        "FAQ": dedent(
            """
            # FAQ / Troubleshooting

            ## “Purchase Intention is extremely low”
            Most common causes:
            - PI values are provided in **0..1** fractions instead of **0..100** percent
            - mixed units across PI columns (one percent, one fraction)
            - wrong base population (filters not intended for this analysis)

            ## “The chart axis is huge / most data is squeezed”
            - Outliers or unit mismatches can stretch the price grid.
            - Use manual grid overrides (min/max/step) to focus on the relevant range.
            - Check currency consistency within a segment.

            ## “Export to PPTX fails”
            - PNG rendering requires Chrome/Chromium.
            - Install Chrome/Chromium or use the documented helper command.
            - Re-run export after the preflight check succeeds.

            ## “Intersections show closest/interval instead of clean”
            - This can happen with small bases, noisy answers, or unusual distributions.
            - Review the curve shapes and QC counts.
            - Consider comparing segments or widening the grid range.
            """
        ).strip(),
    }


def get_knowledge_markdown_de(config_snapshot: dict, sav_available: bool) -> dict[str, str]:
    default_currency_snap = _format_currency_snap(config_snapshot)
    sav_text = (
        "CSV, XLSX, SAV (optionale SAV-Unterstützung ist in dieser Umgebung installiert)."
        if sav_available
        else "CSV, XLSX. SAV-Unterstützung ist optional und in dieser Umgebung nicht installiert."
    )

    return {
        "Overview": dedent(
            f"""
            # Wissen & Methodik

            Dieser Bereich erklärt, was das Tool berechnet, warum es so berechnet wird und wie die Ergebnisse zu lesen sind. Alles ist deterministisch und basiert auf den im Tool implementierten Regeln (keine KI).

            ## Was das Tool leistet
            Das Tool unterstützt zwei Blickwinkel auf Pricing:

            - **Preiswahrnehmung (PSM / Van Westendorp):** leitet eine **akzeptable Preisspanne** und zentrale Preiskennzahlen aus vier offenen Preis-Schwellen pro Befragtem ab.
            - **Kaufwahrscheinlichkeit (NMS-Extension):** leitet eine **Kaufwahrscheinlichkeitskurve** und einen **Turnover-Index** aus zwei Kaufwahrscheinlichkeitsfragen ab (verankert am individuell genannten „angemessenen“ und „teuer, aber akzeptablen“ Preis) – oder optional aus einer expliziten Preisleiter, falls vorhanden.

            PSM = Grenzen der Preiswahrnehmung.
            PI/Turnover = Trade-off zwischen Reichweite und Umsatz-Proxy.

            ## Typischer Ablauf
            1) Datei hochladen (CSV/XLSX, optional SAV falls installiert)
            2) Validierung und QC prüfen
            3) PSM-Chart + KPIs interpretieren
            4) Wenn PI vorhanden: PI + Turnover (und optional Profit-Proxy) interpretieren
            5) PPTX/Excel exportieren

            ### Kurzglossar
            - **Schwellenfragen:** „zu günstig“, „angemessen“, „teuer aber akzeptabel“, „zu teuer“
            - **Akzeptable Preisspanne:** Preisfenster, das insgesamt als passend empfunden wird
            - **Turnover-Index:** Preis × Kaufwahrscheinlichkeit, normiert auf max = 100

            ### Unterstützte Dateitypen (Laufzeit)
            - {sav_text}
            """
        ).strip(),
        "PSM (Price Sensitivity Meter)": dedent(
            """
            # PSM (Price Sensitivity Meter)

            ## Inputs (pro Befragtem)
            Vier Preis-Schwellen:

            - **Zu günstig:** darunter wirkt das Produkt ggf. „zu billig“ (Qualitätszweifel)
            - **Günstig/angemessen (Bargain):** bis dahin wirkt es als „gutes Preis-Leistungs-Verhältnis“
            - **Teuer, aber akzeptabel:** bis dahin ist es teuer, aber noch akzeptiert
            - **Zu teuer:** darüber wird es abgelehnt

            ### Plausi-Regel (streng)
            Ein Befragter gilt nur als PSM-valid, wenn:

            `zu_günstig < angemessen < teuer_akzeptabel < zu_teuer`

            Ungültige Fälle werden ausgeschlossen und im QC ausgewiesen.

            ## Kurven (so entsteht der Chart)
            Auf einem Preisgrid berechnet das Tool Anteile:

            - **Zu günstig(p):** Anteil mit `zu_günstig >= p` (fallend)
            - **Angemessen(p):** Anteil mit `angemessen >= p` (fallend)
            - **Teuer(p):** Anteil mit `teuer_akzeptabel <= p` (steigend)
            - **Zu teuer(p):** Anteil mit `zu_teuer <= p` (steigend)

            Abgeleitet:
            - **Nicht angemessen(p) = 100 − Angemessen(p)**
            - **Nicht teuer(p) = 100 − Teuer(p)**

            Falls Gewichte vorhanden sind, werden gewichtete Anteile verwendet.

            ## Schnittpunkte/KPIs und Bedeutung
            Schnittpunkte werden per linearer Interpolation bestimmt:

            - **PMI (Marginal Inexpensive):** Zu günstig × Nicht angemessen
              → Untergrenze akzeptabler Preise
            - **PME (Marginal Expensive):** Zu teuer × Nicht teuer
              → Obergrenze akzeptabler Preise
            - **OPP (Optimal):** Zu günstig × Zu teuer
              → minimaler Widerstand („zu günstig“ = „zu teuer“)
            - **IDP (Indifference):** Angemessen × Teuer
              → „Normalpreis“ / Preisimage-Mitte

            ### Akzeptable Preisspanne
            **Accepted Range = [PMI, PME]**

            Ein Preis in diesem Fenster wird insgesamt als passend wahrgenommen.

            ### Price Stress
            **Price Stress = OPP − IDP**

            Daumenregel:
            - negativ (OPP < IDP): eher schwächeres Preisimage / höhere Widerstände um „Normalpreis“
            - positiv (OPP > IDP): eher Premium-/Innovationspotenzial
            - nahe 0: stabil/balanciert

            ## Schnittpunkt-Qualität (Status)
            - **clean:** Kurven schneiden sich klar
            - **interval:** Überlappung über ein Intervall (Tool berichtet eine Range)
            - **closest:** kein Schnittpunkt auf dem Grid (Tool berichtet nächstbeste Annäherung)

            Bei interval/closest: KPIs mit zusätzlicher Vorsicht interpretieren.
            """
        ).strip(),
        "Purchase Intention & Turnover": dedent(
            """
            # Kaufwahrscheinlichkeit & Turnover

            Verfügbar, wenn PI-Daten vorhanden sind (Respondent-Level-Anker oder Preisleiter).

            ## PI-Inputs (NMS, Respondent-Level)
            Zwei Fragen:

            - PI am „angemessenen“ Preis: `pi_bargain_pct`
            - PI am „teuer, aber akzeptabel“-Preis: `pi_expensive_pct`

            Erwartete Einheit: **Prozent 0..100**.

            ### Grundgesamtheit / Filter
            Standard:
            - nur **PSM-valid**, plus
            - optional „hohes Basisinteresse“-Filter, falls vorhanden (z. B. `puki <= 2`, optional `<= 3`)

            QC zeigt die jeweiligen Bases.

            ## PI-Kurve aus zwei Punkten (deterministisch)
            Pro Befragtem wird eine piecewise-lineare Kurve gebaut:

            (zu_günstig, 0) → (angemessen, PI_angemessen) → (teuer_akzeptabel, PI_teuer) → (zu_teuer, 0)

            Diese Kurven werden auf dem Grid ausgewertet und gemittelt (optional gewichtet).

            Wichtig: Das ist ein Modell/Proxy – kein garantierter Marktabsatz.

            ## Turnover-Index (0–100)
            - `revenue_raw(p) = price(p) × (PI(p)/100)`
            - `turnover_index(p) = revenue_raw(p) / max(revenue_raw) × 100`

            Maximum wird als „Maximum Turnover“ markiert.

            ### Warum Turnover „gut“ aussehen kann, obwohl PI falsch skaliert ist
            Da der Turnover-Index auf max=100 normiert wird, kann ein PI-Skalierungsfehler
            (0..1 statt 0..100) PI visuell stark komprimieren, während der Indexverlauf
            ähnlich bleibt. Bei extrem niedriger PI: Einheiten prüfen.

            ## Optional: Preisleiter
            Wenn eine explizite Preisleiter (Preis → PI) vorhanden ist, wird diese bevorzugt
            verwendet, da sie direkt gemessen ist.
            """
        ).strip(),
        "Quality & Grid": dedent(
            f"""
            # Qualität & Grid

            ## QC
            Ausgewiesen werden:
            - Gesamtfälle
            - PSM-valid (strenge Ordnung)
            - Missingness je Variable
            - PI-Base nach Filtern (falls relevant)
            - Hinweise zu Ausreißern/Einheiten (falls implementiert)

            ## Preisgrid: Auto vs. Manuell
            Auto (Default):
            - min/max aus den beobachteten Schwellen
            - „nice“ step für glatte Kurven (~100 Punkte)
            - Currency snapping, wenn aktiviert

            Manuell:
            - min/max/step überschreiben, um den relevanten Bereich zu fokussieren
              (hilft bei Ausreißern).

            ### Currency snapping (Defaults)
            Default increments (aus config):
            {default_currency_snap}
            """
        ).strip(),
        "Exports & Privacy": dedent(
            """
            # Export & Datenschutz

            ## Export
            - PPTX (Charts als Bild)
            - Excel (KPIs + Kurvendaten)

            ### Voraussetzung für PPTX-Chart-Rendering
            Für PPTX werden Plotly-Charts als PNG gerendert.
            Dafür wird eine funktionierende Chrome/Chromium-Umgebung benötigt.
            Bei fehlendem Browser gibt es einen Preflight-Fehler mit konkreten Hinweisen.

            ## Datenschutz / Demo-Betrieb
            - Uploads werden standardmäßig in-memory verarbeitet.
            - Öffentliche Demo nicht für vertrauliche Kundendaten verwenden.
            - Für Kundenprojekte lokal oder in kontrollierter Umgebung betreiben.
            - Private Daten gehören in `data_private/` (Repo-Guardrails verhindern Commits).
            """
        ).strip(),
        "FAQ": dedent(
            """
            # FAQ / Troubleshooting

            ## “Purchase Intention ist extrem niedrig”
            Typische Ursachen:
            - PI liegt in 0..1 statt 0..100 vor
            - gemischte Einheiten über PI-Spalten
            - falsche Filter/Grundgesamtheit

            ## “Achse ist riesig / alles zusammengedrückt”
            - Ausreißer oder Einheitenmix strecken das Grid.
            - Manuelles Grid setzen (min/max/step).
            - Currency je Segment prüfen.

            ## “PPTX Export schlägt fehl”
            - PNG Rendering braucht Chrome/Chromium.
            - Browser installieren oder den im Tool beschriebenen Helper nutzen.
            - Export erneut ausführen.

            ## “Schnittpunkte sind closest/interval”
            - möglich bei kleinen Bases / Rauschen / ungewöhnlichen Verteilungen
            - Kurvenform + QC prüfen
            - Segmentvergleiche/robustere Einstellungen nutzen
            """
        ).strip(),
    }
