-- Tage mit den meisten Stunden negativer Preise und deren Rahmenbedingungen.
WITH daily AS (
    SELECT
        date(date)                               AS day,
        SUM(price < 0)                           AS negative_hours,
        ROUND(MIN(price), 2)                     AS min_price,
        ROUND(AVG(price), 2)                     AS avg_price,
        ROUND(AVG(solar) / 1000.0, 1)            AS avg_solar_gw,
        ROUND(AVG(wind) / 1000.0, 1)             AS avg_wind_gw,
        MAX(is_weekend)                          AS is_weekend
    FROM energy_data
    GROUP BY date
)
SELECT
    RANK() OVER (ORDER BY negative_hours DESC, min_price) AS rank,
    *
FROM daily
WHERE negative_hours > 0
ORDER BY rank
LIMIT 15;
