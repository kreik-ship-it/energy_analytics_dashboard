-- Kennzahlen je Jahr: Preisniveau, Extremwerte, negative Preise, Anteil Erneuerbarer.
SELECT
    year,
    ROUND(AVG(price), 2)                                    AS avg_price,
    MIN(price)                                              AS min_price,
    MAX(price)                                              AS max_price,
    SUM(price < 0)                                          AS negative_hours,
    ROUND(100.0 * AVG(price < 0), 2)                        AS negative_share_pct,
    ROUND(100.0 * SUM(renewable_generation) / SUM(load), 1) AS renewable_share_pct,
    -- Veränderung des Durchschnittspreises gegenüber dem Vorjahr
    ROUND(AVG(price) - LAG(AVG(price)) OVER (ORDER BY year), 2) AS avg_price_change_vs_prev_year
FROM energy_data
GROUP BY year
ORDER BY year;
