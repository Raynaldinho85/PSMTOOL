# ruff: noqa: E501

from __future__ import annotations

from textwrap import dedent

from psm_tool.report.wording_policy import apply_wording_policy, competition_caveat_line


def _format_currency_snap(config_snapshot: dict) -> str:
    mapping = config_snapshot.get("default_currency_snap", {})
    if not isinstance(mapping, dict) or not mapping:
        return "- n/a"
    lines = [f"- {str(currency).upper()}: {value:g}" for currency, value in mapping.items()]
    return "\n".join(lines)


def _format_supported_files(sav_available: bool) -> str:
    _ = sav_available
    return (
        "- CSV, XLSX. SAV uploads are intentionally disabled in the app so uploaded files "
        "remain fully in-memory."
    )


def _format_intersection_statuses(config_snapshot: dict) -> str:
    statuses = config_snapshot.get("intersection_statuses", [])
    if not isinstance(statuses, list) or not statuses:
        return "- clean\n- interval\n- closest"
    lines = [f"- {str(status)}" for status in statuses]
    return "\n".join(lines)


def _indent_following_lines(text: str, *, spaces: int = 12) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    indent = " " * spaces
    return "\n".join([lines[0], *[f"{indent}{line}" for line in lines[1:]]])


def _pi_unit_behavior_line(config_snapshot: dict) -> str:
    normalized = bool(config_snapshot.get("pi_normalization_note_available", False))
    tiny_warning = bool(config_snapshot.get("pi_tiny_note_available", False))
    if normalized and tiny_warning:
        return (
            "PI unit handling: internal invariant is percent 0..100. "
            "If both PI columns look like coded scale 1..11, the tool maps them to percent with "
            "pct = 10 + (code - 1) * 9. "
            "If both PI columns look like 0..1 fractions with strong evidence, the tool normalizes to 0..100 and adds a warning. "
            "If both columns look like fractions but are extremely tiny, it does not auto-scale and warns. "
            "Mixed units across PI columns raise a validation error."
        )
    if normalized:
        return (
            "PI unit handling: internal invariant is percent 0..100. "
            "If both PI columns look like coded scale 1..11, the tool maps them to percent with pct = 10 + (code - 1) * 9. "
            "If both PI columns clearly look like 0..1 fractions, the tool normalizes to 0..100 and adds a warning."
        )
    return (
        "PI unit expectation: internal calculations assume percent 0..100. "
        "If source data is in 1..11 coded scale or 0..1 fractions and is not normalized, PI can look compressed."
    )


def get_knowledge_markdown_en(config_snapshot: dict, sav_available: bool) -> dict[str, str]:
    default_currency_snap = _indent_following_lines(_format_currency_snap(config_snapshot))
    supported_files = _format_supported_files(sav_available)
    ordering_rule = str(
        config_snapshot.get(
            "ordering_rule", "too_cheap < bargain < expensive_acceptable < too_expensive"
        )
    )
    statuses = _indent_following_lines(_format_intersection_statuses(config_snapshot))
    pi_unit_line = _pi_unit_behavior_line(config_snapshot)
    perception_example = apply_wording_policy(
        "Set price at the accepted range center.",
        lens="Perception",
    )
    demand_example = apply_wording_policy(
        "Use price where modeled trial is highest.",
        lens="Modeled demand",
    )
    economics_example = apply_wording_policy(
        "Optimal price is where turnover is highest.",
        lens="Economics proxy",
    )

    return {
        "Overview": dedent(
            f"""
            # Knowledge & Methodology

            This page documents exactly what this tool does in code. The logic is deterministic, rule-based, and reproducible.

            ## What this tool computes
            The tool combines two pricing lenses:

            - **PSM (perception boundaries):** derives PMI, OPP, IDP, PME and accepted range from four threshold questions.
            - **Purchase Intention + Turnover/Profit proxies:** derives PI-over-price and index curves from respondent PI anchors (or optional PI ladder input).

            ## Runtime workflow in this app
            1) Read file into a canonical DataFrame (`read_any`)
            2) Validate schema and numeric coercion (`validate_template`)
            3) Select product/segment in Results
            4) Build analysis base (plausibility filter toggle, then optional outlier filter)
            5) Build grid (`build_price_grid_details`)
            6) Compute PSM curves/KPIs
            7) Compute NMS/PI and turnover/profit proxies when PI exists
            8) Export PPTX/Excel from the same payload

            ### Supported file types (runtime)
            {supported_files}

            ### Quick glossary
            - **Threshold columns:** `too_cheap`, `bargain`, `expensive_acceptable`, `too_expensive`
            - **Accepted range:** `[PMI, PME]`
            - **Turnover index:** `price * PI`, normalized to max = 100

            ## Model Layers
            - **Perception layer (PSM):** price perception boundaries (PMI/OPP/IDP/PME).
            - **Modeled demand layer (NMS/PI):** modeled purchase-intention curves from anchor assumptions.
            - **Economics proxy layer:** turnover/profit proxies derived from modeled PI.

            PSM measures price perception boundaries, not observed market demand under competition.
            {competition_caveat_line()}

            ### Wording policy examples
            - `{perception_example}`
            - `{demand_example}`
            - `{economics_example}`
            """
        ).strip(),
        "PSM (Price Sensitivity Meter)": dedent(
            f"""
            # PSM (Price Sensitivity Meter)

            ## Inputs and validity rule
            PSM uses four threshold columns per respondent:
            - `too_cheap`
            - `bargain`
            - `expensive_acceptable`
            - `too_expensive`

            Strict ordering rule used by code:
            `{ordering_rule}`

            In Results, this plausibility filter is a user toggle:
            - ON (default): only ordered respondents enter PSM/NMS analysis
            - OFF: non-ordered respondents can remain in analysis and are explicitly reported in QC

            ## Curve construction (exact definitions)
            On each grid price `p`:
            - Too Cheap(p): share with `too_cheap >= p`
            - Bargain(p): share with `bargain >= p`
            - Expensive(p): share with `expensive_acceptable <= p`
            - Too Expensive(p): share with `too_expensive <= p`
            - Not Bargain(p) = `100 - Bargain(p)`
            - Not Expensive(p) = `100 - Expensive(p)`

            Weight behavior:
            - If `weight` exists and usable (sum of non-negative weights > 0), weighted shares are used.
            - If `weight` is missing/invalid/all-zero, the tool falls back to unweighted calculation (and reports this in UI/QC).

            ## KPI intersections
            Intersections are solved on the grid with linear interpolation:
            - PMI: Too Cheap x Not Bargain
            - OPP: Too Cheap x Too Expensive
            - IDP: Bargain x Expensive
            - PME: Too Expensive x Not Expensive

            Status values implemented:
            {statuses}

            Meaning:
            - `clean`: sign-change crossing found
            - `interval`: overlapping segment; tool reports midpoint and interval bounds
            - `closest`: no crossing; tool reports closest approach on grid

            Derived KPIs:
            - Accepted Range = `[min(PMI, PME), max(PMI, PME)]`
            - Price Stress = `OPP - IDP`
            """
        ).strip(),
        "NMS (Newton-Miller-Smith)": dedent(
            f"""
            # NMS (Newton-Miller-Smith)

            Purchase Intention & Turnover

            ## PI sources and priority
            The tool resolves PI curve source in this order:
            1) Explicit PI ladder (`price`, `purchase_intention_pct`) for selected segment/currency/product
            2) NMS modeled trial curve from respondent-level PI anchors

            ## Respondent-level NMS model (when no ladder is used)
            Required PI columns:
            - `pi_bargain_pct`
            - `pi_expensive_pct`

            Per respondent, the tool builds a piecewise-linear curve with four anchors:
            `(too_cheap, 0) -> (bargain, PI_bargain) -> (expensive_acceptable, PI_expensive) -> (too_expensive, 0)`
            Then it averages curves over the active analysis base (weighted if usable).

            Base population is the current Results analysis base, plus optional PUKI filter:
            - default: `puki <= 2` if `puki` exists
            - optional: `puki <= 3`
            - if `puki` missing: filter is not applied and this is reported

            ## PI unit invariant and guardrails
            Accepted PI input representations:
            - percent `0..100`
            - fraction `0..1` (normalized with guardrails when detected)
            - coded scale `1..11` (mapped as `pct = 10 + (code - 1) * 9`)

            {pi_unit_line}

            ## Turnover Index (0-100)
            - `revenue_raw(p) = price(p) * (PI(p)/100)`
            - `turnover_index(p) = revenue_raw(p) / max(revenue_raw) * 100` (or 0 if max is 0)
            - max-turnover price tie-break: lowest price among equal maxima

            Why turnover can look plausible while PI is wrong:
            - normalization to max=100 can preserve shape even when PI is scaled incorrectly.

            ## Optional Profit Proxy mode
            If unit cost is entered in Results:
            - `profit_proxy_per_100 = (price - cost) * (PI/100) * 100`
            - `profit_index = profit_proxy / max(profit_proxy) * 100` (or 0 if max <= 0)
            - max-profit tie-break: lowest price among equal maxima
            """
        ).strip(),
        "Quality & Grid": dedent(
            f"""
            # Quality & Grid

            ## QC fields reported by code
            QC includes:
            - total rows
            - PSM-valid rows
            - exclusions due to ordering or missing thresholds
            - PUKI pass/excluded counts (if `puki` exists)
            - outlier filter settings and excluded count
            - analysis N after outlier filtering
            - weighting fallback indicators

            ## Data validation rule: price inputs
            Rule: **Negative price values are treated as missing.**

            Description:
            - any threshold value `< 0` is converted to missing in preprocessing
            - negative values are excluded exactly like other missing values
            - no clamping and no transformation is applied

            Scope:
            - PSM calculations
            - Purchase Intention calculations
            - Turnover Index calculations
            - NMS Trial/Revenue calculations

            ## Outlier filter (Results control)
            Optional row-level exclusion using quantile bands per price column:
            - Mild: 0.5%..99.5%
            - Medium: 1%..99%
            - Strict: 5%..95%
            A row is excluded if at least one threshold is outside bounds.

            ## Auto grid algorithm (as implemented)
            The auto grid uses PSM-valid thresholds:
            1) flatten all threshold values
            2) compute p05 and p95 when enough values are available
            3) span = p95 - p05
            4) grid_min = max(0, p05 - 0.25 * span)
            5) grid_max fallback = p95 + 0.25 * span
            6) upper guardrail: if median(`expensive_acceptable`) is finite and >0, use `round_up_to_100(2 * median_expensive_acceptable)` as grid_max
            7) derive nice step, target about 100 points
            8) apply currency snap when enabled (floor min / ceil max, step aligned to increment)
            9) ensure sorted unique grid and include max
            10) fallback to legacy min/max logic if quantile path is not usable

            ## Manual grid override
            You can force `min`, `max`, `step` in Results.
            This is useful when outliers or unit issues stretch the axis.

            ### Currency snapping defaults
            {default_currency_snap}
            """
        ).strip(),
        "Exports & Privacy": dedent(
            """
            # Exports & Privacy

            ## Export outputs
            - PPTX with static chart images and KPI text
            - Excel with KPI summary and curve tables

            ## Static image rendering requirement
            PPTX export converts Plotly figures to PNG via Kaleido.
            A working Chrome/Chromium runtime is required.
            The app performs an export preflight and shows an actionable error if browser rendering is unavailable.

            ## Privacy posture
            - Uploaded files are processed in memory in normal app flow.
            - Public demo should only use synthetic/non-sensitive data.
            - Private client datasets should stay local and outside versioned paths.
            """
        ).strip(),
        "FAQ": dedent(
            """
            # FAQ / Troubleshooting

            ## Purchase Intention is unexpectedly low
            Check in this order:
            - PI units (`pi_bargain_pct`, `pi_expensive_pct`) are correctly interpreted:
              percent `0..100`, fraction `0..1`, or coded `1..11`
            - no mixed PI units across the two PI columns
            - expected PUKI threshold is selected
            - plausibility/outlier filters are intentionally set

            ## Axis is stretched and curves are compressed
            Common causes:
            - outliers in threshold columns
            - broad segment mix
            - manual grid not set for focused view

            Use:
            - outlier filter and/or
            - manual min/max/step override.

            ## Turnover index looks fine but PI does not
            This can happen because turnover is normalized to max=100.
            Verify PI units and PI source mode (ladder vs modeled NMS curve).

            ## PPTX export fails
            Reason is typically missing browser runtime for PNG rendering.
            Ensure Chrome/Chromium is available in the runtime environment and rerun export.

            ## closest/interval intersection status appears
            Interpretation:
            - `closest`: no crossing on current grid
            - `interval`: overlap over a range
            In both cases, read KPIs with caution and inspect curve shape/QC.
            """
        ).strip(),
    }


def get_knowledge_markdown_de(config_snapshot: dict, sav_available: bool) -> dict[str, str]:
    default_currency_snap = _indent_following_lines(_format_currency_snap(config_snapshot))
    supported_files = _format_supported_files(sav_available)
    ordering_rule = str(
        config_snapshot.get(
            "ordering_rule", "too_cheap < bargain < expensive_acceptable < too_expensive"
        )
    )
    statuses = _indent_following_lines(_format_intersection_statuses(config_snapshot))
    pi_unit_line = _pi_unit_behavior_line(config_snapshot)
    perception_example = apply_wording_policy(
        "Set price at the accepted range center.",
        lens="Perception",
    )
    demand_example = apply_wording_policy(
        "Use price where modeled trial is highest.",
        lens="Modeled demand",
    )
    economics_example = apply_wording_policy(
        "Optimal price is where turnover is highest.",
        lens="Economics proxy",
    )

    return {
        "Overview": dedent(
            f"""
            # Wissen & Methodik

            Diese Seite beschreibt exakt, was das Tool im Code tut. Die Logik ist deterministisch, regelbasiert und reproduzierbar.

            ## Was das Tool berechnet
            Das Tool kombiniert zwei Pricing-Perspektiven:
            - **PSM (Preiswahrnehmung):** PMI, OPP, IDP, PME und akzeptable Preisspanne aus vier Preis-Schwellen.
            - **Kaufwahrscheinlichkeit + Turnover/Profit-Proxies:** PI-Kurve und Index-Kurven aus PI-Ankern (oder optionaler Preisleiter).

            ## Ablauf im App-Code
            1) Datei in kanonisches DataFrame laden (`read_any`)
            2) Schema/Numerik validieren (`validate_template`)
            3) Produkt/Segment in Results waehlen
            4) Analysebasis bilden (Plausibilitaets-Filter, danach optionaler Ausreisserfilter)
            5) Preisgrid bauen (`build_price_grid_details`)
            6) PSM-Kurven/KPIs berechnen
            7) NMS/PI und Turnover/Profit berechnen (falls PI vorhanden)
            8) PPTX/Excel aus demselben Payload exportieren

            ### Unterstuetzte Dateitypen (Laufzeit)
            {supported_files}

            ### Kurzglossar
            - **Schwellen-Spalten:** `too_cheap`, `bargain`, `expensive_acceptable`, `too_expensive`
            - **Akzeptable Spanne:** `[PMI, PME]`
            - **Turnover-Index:** `Preis * PI`, normiert auf max = 100

            ## Model Layers
            - **Perception layer (PSM):** Wahrnehmungsgrenzen (PMI/OPP/IDP/PME).
            - **Modeled demand layer (NMS/PI):** modellierte Kaufwahrscheinlichkeitskurven aus PI-Ankern.
            - **Economics proxy layer:** Turnover/Profit-Proxies aus modellierter PI.

            PSM measures price perception boundaries, not observed market demand under competition.
            {competition_caveat_line()}

            ### Wording-Policy Beispiele
            - `{perception_example}`
            - `{demand_example}`
            - `{economics_example}`
            """
        ).strip(),
        "PSM (Price Sensitivity Meter)": dedent(
            f"""
            # PSM (Price Sensitivity Meter)

            ## Inputs und Plausi-Regel
            PSM nutzt vier Schwellen je Respondent:
            - `too_cheap`
            - `bargain`
            - `expensive_acceptable`
            - `too_expensive`

            Strenge Ordnungsregel im Code:
            `{ordering_rule}`

            In Results ist dies ein Schalter:
            - ON (Default): nur geordnete Respondents gehen in PSM/NMS
            - OFF: ungeordnete Respondents koennen enthalten sein; QC weist das explizit aus

            ## Kurvendefinitionen (exakt)
            Fuer jeden Grid-Preis `p`:
            - Too Cheap(p): Anteil mit `too_cheap >= p`
            - Bargain(p): Anteil mit `bargain >= p`
            - Expensive(p): Anteil mit `expensive_acceptable <= p`
            - Too Expensive(p): Anteil mit `too_expensive <= p`
            - Not Bargain(p) = `100 - Bargain(p)`
            - Not Expensive(p) = `100 - Expensive(p)`

            Gewichtung:
            - Wenn `weight` vorhanden und nutzbar ist (Summe nicht-negativer Gewichte > 0), wird gewichtet gerechnet.
            - Sonst faellt das Tool auf ungewichtete Berechnung zurueck (Hinweis in UI/QC).

            ## KPI-Schnittpunkte
            Schnittpunkte werden per linearer Interpolation auf dem Grid bestimmt:
            - PMI: Too Cheap x Not Bargain
            - OPP: Too Cheap x Too Expensive
            - IDP: Bargain x Expensive
            - PME: Too Expensive x Not Expensive

            Implementierte Status:
            {statuses}

            Bedeutung:
            - `clean`: klare Kreuzung per Vorzeichenwechsel
            - `interval`: Ueberlappung auf Intervall; Tool berichtet Mittelpunkt plus Bounds
            - `closest`: keine Kreuzung auf Grid; Tool berichtet naechste Annaeherung

            Abgeleitete KPIs:
            - Accepted Range = `[min(PMI, PME), max(PMI, PME)]`
            - Price Stress = `OPP - IDP`
            """
        ).strip(),
        "NMS (Newton-Miller-Smith)": dedent(
            f"""
            # NMS (Newton-Miller-Smith)

            Kaufwahrscheinlichkeit & Turnover

            ## PI-Quelle und Prioritaet
            Die PI-Kurve wird in dieser Reihenfolge bestimmt:
            1) Explizite Preisleiter (`price`, `purchase_intention_pct`) fuer Segment/Waehrung/Produkt
            2) NMS-Modellkurve aus Respondent-PI-Ankern

            ## NMS-Modell (wenn keine Preisleiter genutzt wird)
            Erforderliche PI-Spalten:
            - `pi_bargain_pct`
            - `pi_expensive_pct`

            Pro Respondent wird eine piecewise-lineare Kurve gebaut:
            `(too_cheap, 0) -> (bargain, PI_bargain) -> (expensive_acceptable, PI_expensive) -> (too_expensive, 0)`
            Danach Mittelung ueber die aktive Analysebasis (optional gewichtet).

            Analysebasis:
            - aktuelle Results-Basis (inkl. Plausi-/Ausreisser-Einstellungen)
            - optionaler PUKI-Filter:
              - Default `puki <= 2`
              - optional `puki <= 3`
              - ohne `puki`: kein Filter, wird ausgewiesen

            ## PI-Einheiten und Guardrails
            Unterstuetzte PI-Eingabedarstellungen:
            - Prozent `0..100`
            - Fraction `0..1` (wird bei Erkennung mit Guardrails normalisiert)
            - Code-Skala `1..11` (Mapping: `pct = 10 + (code - 1) * 9`)

            {pi_unit_line}

            ## Turnover-Index (0-100)
            - `revenue_raw(p) = price(p) * (PI(p)/100)`
            - `turnover_index(p) = revenue_raw(p) / max(revenue_raw) * 100` (oder 0 wenn max = 0)
            - Tie-break bei Maximum: niedrigster Preis bei Gleichstand

            Warum Turnover gut aussehen kann, obwohl PI falsch ist:
            - Normierung auf max=100 kann den Verlauf stabil wirken lassen, obwohl PI skaliert falsch ist.

            ## Optional: Profit-Proxy-Modus
            Wenn Unit Cost in Results gesetzt ist:
            - `profit_proxy_per_100 = (price - cost) * (PI/100) * 100`
            - `profit_index = profit_proxy / max(profit_proxy) * 100` (oder 0 bei max <= 0)
            - Tie-break Maximum Profit: niedrigster Preis bei Gleichstand
            """
        ).strip(),
        "Quality & Grid": dedent(
            f"""
            # Qualitaet & Grid

            ## QC-Felder aus dem Code
            QC weist aus:
            - Gesamtfaelle
            - PSM-valid N
            - Ausschluesse wegen Ordnung/Missingness
            - PUKI Pass/Excluded (wenn `puki` vorhanden)
            - Ausreisser-Settings und excluded N
            - Analysis N nach Ausreisserfilter
            - Weight-Fallback-Hinweise

            ## Datenvalidierungsregel: Preis-Inputs
            Regel: **Negative Preiswerte werden als Missing behandelt.**

            Beschreibung:
            - jeder Schwellenwert `< 0` wird im Preprocessing zu Missing
            - negative Werte werden identisch zu anderen Missing-Werten ausgeschlossen
            - kein Clamping und keine Transformation

            Scope:
            - PSM-Berechnungen
            - Purchase-Intention-Berechnungen
            - Turnover-Index-Berechnungen
            - NMS Trial/Revenue-Berechnungen

            ## Ausreisserfilter (Results)
            Optionales Zeilen-Excluding ueber Quantil-Baender je Preisspalte:
            - Mild: 0.5%..99.5%
            - Medium: 1%..99%
            - Strict: 5%..95%
            Zeile wird ausgeschlossen, wenn mindestens eine Schwelle ausserhalb liegt.

            ## Auto-Grid-Algorithmus (implementiert)
            Das Auto-Grid nutzt PSM-valide Schwellen:
            1) alle Schwellen flatten
            2) p05/p95 berechnen (bei ausreichender Datenlage)
            3) span = p95 - p05
            4) grid_min = max(0, p05 - 0.25 * span)
            5) grid_max fallback = p95 + 0.25 * span
            6) obere Guardrail: wenn median(`expensive_acceptable`) > 0, dann `round_up_to_100(2 * median_expensive_acceptable)` als grid_max
            7) nice step fuer ca. 100 Punkte
            8) optional Currency-Snap (min floor, max ceil, step aligned)
            9) sortiert/eindeutig, max enthalten
            10) legacy fallback falls Quantil-Pfad nicht nutzbar ist

            ## Manuelles Grid
            `min`, `max`, `step` koennen in Results ueberschrieben werden.

            ### Currency-Snapping Defaults
            {default_currency_snap}
            """
        ).strip(),
        "Exports & Privacy": dedent(
            """
            # Export & Datenschutz

            ## Exporte
            - PPTX mit statischen Chart-Bildern und KPI-Text
            - Excel mit KPI-Summary und Kurventabellen

            ## Voraussetzung fuer statisches Rendering
            PPTX-Export rendert Plotly-Charts als PNG ueber Kaleido.
            Dafuer wird eine funktionierende Chrome/Chromium-Runtime benoetigt.
            Vor Export gibt es einen Preflight mit konkreter Fehlermeldung.

            ## Datenschutz
            - Uploads werden im normalen App-Flow in-memory verarbeitet.
            - Oeffentliche Demo nur mit synthetischen/nicht-sensitiven Daten.
            - Vertrauliche Kundendaten lokal und ausserhalb versionierter Pfade halten.
            """
        ).strip(),
        "FAQ": dedent(
            """
            # FAQ / Troubleshooting

            ## Purchase Intention ist unerwartet niedrig
            In dieser Reihenfolge pruefen:
            - PI-Einheiten (`pi_bargain_pct`, `pi_expensive_pct`) korrekt interpretiert:
              Prozent `0..100`, Fraction `0..1` oder Code-Skala `1..11`
            - keine gemischten PI-Einheiten
            - erwarteter PUKI-Threshold gesetzt
            - Plausi-/Ausreisserfilter bewusst gesetzt

            ## Achse ist zu breit, Kurven wirken gequetscht
            Typische Ursachen:
            - Ausreisser in Preisspalten
            - breite Segmentmischung
            - fehlendes manuelles Grid fuer Fokusbereich

            Optionen:
            - Ausreisserfilter aktivieren und/oder
            - manuelles Grid setzen (`min`, `max`, `step`)

            ## Turnover sieht okay aus, PI nicht
            Kann durch Normierung auf max=100 passieren.
            PI-Einheiten und PI-Quelle (Preisleiter vs NMS-Modellkurve) pruefen.

            ## PPTX-Export faellt aus
            Meist fehlt Browser-Runtime fuer PNG-Rendering.
            Chrome/Chromium sicherstellen und Export erneut starten.

            ## closest/interval statt clean
            Bedeutung:
            - `closest`: keine Kreuzung auf aktuellem Grid
            - `interval`: Ueberlappung ueber Bereich
            KPIs dann vorsichtig interpretieren und Kurven/QC mitpruefen.
            """
        ).strip(),
    }
