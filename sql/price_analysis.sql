SELECT
    year,
    AVG(price) AS average_price,
    MIN(price) AS minimum_price,
    MAX(price) AS maximum_price
FROM energy_data
GROUP BY year
ORDER BY year;