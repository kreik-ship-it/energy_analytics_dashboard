-- Tagesprofil des Strompreises (Ortszeit) je Jahreszeit.
-- Zeigt die "Duck Curve": Mittagstief durch Solarstrom, Abendspitze nach Sonnenuntergang.
SELECT
    hour,
    ROUND(AVG(CASE WHEN season = 'Winter'   THEN price END), 2) AS winter,
    ROUND(AVG(CASE WHEN season = 'Frühling' THEN price END), 2) AS fruehling,
    ROUND(AVG(CASE WHEN season = 'Sommer'   THEN price END), 2) AS sommer,
    ROUND(AVG(CASE WHEN season = 'Herbst'   THEN price END), 2) AS herbst,
    ROUND(AVG(price), 2)                                        AS gesamt
FROM energy_data
GROUP BY hour
ORDER BY hour;
