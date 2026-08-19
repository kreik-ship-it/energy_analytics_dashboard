SELECT
    hour,
    AVG(price) AS average_price
FROM energy_data
GROUP BY hour
ORDER BY hour;