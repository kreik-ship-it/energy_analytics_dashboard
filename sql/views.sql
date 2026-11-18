-- Views für Power BI und Ad-hoc-Analysen.
-- Hinweis: Ein Stundenmittel in MW entspricht MWh; Summe / 1000 -> GWh.

CREATE VIEW IF NOT EXISTS v_daily_summary AS
SELECT
    date,
    year,
    month,
    COUNT(*)                                   AS hours,
    ROUND(AVG(price), 2)                       AS avg_price,
    MIN(price)                                 AS min_price,
    MAX(price)                                 AS max_price,
    ROUND(MAX(price) - MIN(price), 2)          AS price_spread,
    SUM(price < 0)                             AS negative_price_hours,
    ROUND(SUM(wind)  / 1000.0, 1)              AS wind_gwh,
    ROUND(SUM(solar) / 1000.0, 1)              AS solar_gwh,
    ROUND(SUM(load)  / 1000.0, 1)              AS load_gwh,
    ROUND(100.0 * SUM(renewable_generation) / SUM(load), 1) AS renewable_share_pct
FROM energy_data
GROUP BY date, year, month;

CREATE VIEW IF NOT EXISTS v_monthly_summary AS
SELECT
    year,
    month,
    printf('%04d-%02d', year, month)           AS year_month,
    ROUND(AVG(price), 2)                       AS avg_price,
    MIN(price)                                 AS min_price,
    MAX(price)                                 AS max_price,
    SUM(price < 0)                             AS negative_price_hours,
    ROUND(SUM(wind)  / 1000.0, 1)              AS wind_gwh,
    ROUND(SUM(solar) / 1000.0, 1)              AS solar_gwh,
    ROUND(SUM(load)  / 1000.0, 1)              AS load_gwh,
    ROUND(100.0 * SUM(renewable_generation) / SUM(load), 1) AS renewable_share_pct
FROM energy_data
GROUP BY year, month;
