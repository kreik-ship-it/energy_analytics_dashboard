-- Monatlicher Preisverlauf mit gleitendem 3-Monats-Durchschnitt und Vorjahresvergleich.
WITH monthly AS (
    SELECT year, month, AVG(price) AS avg_price
    FROM energy_data
    GROUP BY year, month
)
SELECT
    printf('%04d-%02d', year, month)                                       AS year_month,
    ROUND(avg_price, 2)                                                    AS avg_price,
    ROUND(AVG(avg_price) OVER (
        ORDER BY year, month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3m,
    ROUND(avg_price - LAG(avg_price, 12) OVER (ORDER BY year, month), 2)  AS change_vs_prev_year
FROM monthly
ORDER BY year, month;
