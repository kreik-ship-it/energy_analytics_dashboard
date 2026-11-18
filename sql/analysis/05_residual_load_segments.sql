-- Preisniveau nach Residuallast (Last minus Wind und Solar).
SELECT
    CASE
        WHEN residual_load < 0     THEN '1: negativ (< 0 GW)'
        WHEN residual_load < 15000 THEN '2: niedrig (0-15 GW)'
        WHEN residual_load < 30000 THEN '3: mittel (15-30 GW)'
        WHEN residual_load < 45000 THEN '4: hoch (30-45 GW)'
        ELSE                            '5: sehr hoch (> 45 GW)'
    END                                      AS residual_load_segment,
    COUNT(*)                                 AS hours,
    ROUND(AVG(price), 2)                     AS avg_price,
    MIN(price)                               AS min_price,
    MAX(price)                               AS max_price,
    ROUND(100.0 * AVG(price < 0), 1)         AS negative_share_pct
FROM energy_data
GROUP BY residual_load_segment
ORDER BY residual_load_segment;
