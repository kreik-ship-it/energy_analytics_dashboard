-- Werktag vs. Wochenende: Nachfrage, Solarerzeugung und Preis je Tageshälfte.
SELECT
    CASE WHEN is_weekend THEN 'Wochenende' ELSE 'Werktag' END              AS day_type,
    CASE WHEN hour BETWEEN 8 AND 19 THEN 'Tag (8-20 Uhr)' ELSE 'Nacht' END AS day_part,
    ROUND(AVG(price), 2)            AS avg_price,
    ROUND(AVG(load) / 1000.0, 1)    AS avg_load_gw,
    ROUND(AVG(solar) / 1000.0, 1)   AS avg_solar_gw
FROM energy_data
GROUP BY day_type, day_part
ORDER BY day_type DESC, day_part;
