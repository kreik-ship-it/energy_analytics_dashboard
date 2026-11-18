-- Merit-Order-Effekt: Wie hängt der Preis vom Anteil erneuerbarer Erzeugung ab?
WITH bucketed AS (
    SELECT
        price,
        MIN(CAST(renewable_share_pct / 10 AS INTEGER), 10) * 10 AS share_bucket
    FROM energy_data
)
SELECT
    CASE WHEN share_bucket = 100 THEN '>= 100 %'
         ELSE share_bucket || '-' || (share_bucket + 10) || ' %' END AS renewable_share,
    COUNT(*)                                 AS hours,
    ROUND(AVG(price), 2)                     AS avg_price,
    ROUND(100.0 * AVG(price < 0), 1)         AS negative_share_pct
FROM bucketed
GROUP BY share_bucket
ORDER BY share_bucket;
