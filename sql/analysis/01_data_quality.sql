-- Datenqualität: Vollständigkeit, Duplikate und Lücken in der Stundenreihe.
WITH ordered AS (
    SELECT
        (julianday(timestamp) - julianday(LAG(timestamp) OVER (ORDER BY timestamp))) * 24
            AS hours_since_previous
    FROM energy_data
)
SELECT
    (SELECT COUNT(*) FROM energy_data)                         AS total_rows,
    (SELECT COUNT(DISTINCT timestamp) FROM energy_data)        AS distinct_timestamps,
    (SELECT MIN(timestamp_local) FROM energy_data)             AS first_hour_local,
    (SELECT MAX(timestamp_local) FROM energy_data)             AS last_hour_local,
    (SELECT SUM(price IS NULL) + SUM(wind IS NULL) + SUM(solar IS NULL) + SUM(load IS NULL)
       FROM energy_data)                                       AS missing_values,
    SUM(ROUND(hours_since_previous) > 1)                       AS gaps
FROM ordered;
