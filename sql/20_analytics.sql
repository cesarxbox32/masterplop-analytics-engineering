CREATE OR REPLACE VIEW analytics.transactions_enriched AS
SELECT
    t.*,
    t.mcg_id_raw AS mcg_code_original,
    m.mcg_name_raw,
    coalesce(m.mcg_name, 'Sin clasificar') AS mcg_name,
    m.mcg IS NOT NULL AS is_mcg_classified
FROM staging.transactions AS t
LEFT JOIN staging.mcg AS m
    ON t.mcg_id = m.mcg;

COMMENT ON VIEW analytics.transactions_enriched IS
'Capa analítica a nivel transacción. Conserva campos brutos, campos tipados/normalizados y el código MCG original. is_xb_derived se usa solo para control de calidad; no define elegibilidad de cashback.';
