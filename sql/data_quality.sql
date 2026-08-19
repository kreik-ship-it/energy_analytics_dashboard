SELECT
    COUNT(*) AS total_rows,
    COUNT(price) AS price_available,
    COUNT(wind) AS wind_available,
    COUNT(solar) AS solar_available,
    COUNT(load) AS load_available
FROM energy_data;