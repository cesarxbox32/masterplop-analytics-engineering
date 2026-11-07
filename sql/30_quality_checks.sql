CREATE OR REPLACE TABLE audit.dataset_profile AS
SELECT
    count(*)::BIGINT AS row_count,
    count(DISTINCT card_id)::BIGINT AS distinct_cards,
    count(*) FILTER (WHERE product_type = 'Crédito')::BIGINT AS credit_transactions,
    count(*) FILTER (WHERE product_type = 'Débito')::BIGINT AS debit_transactions,
    count(*) FILTER (WHERE product_type NOT IN ('Crédito', 'Débito') OR product_type IS NULL)::BIGINT
        AS unknown_product_type,
    count(*) FILTER (WHERE amt < 0)::BIGINT AS negative_transactions,
    count(*) FILTER (WHERE amt IS NULL)::BIGINT AS invalid_amounts,
    count(*) FILTER (WHERE prch_date IS NULL)::BIGINT AS invalid_dates,
    count(*) FILTER (WHERE prch_time IS NULL)::BIGINT AS invalid_times,
    count(*) FILTER (WHERE is_xb NOT IN (0, 1) OR is_xb IS NULL)::BIGINT AS invalid_is_xb,
    count(*) FILTER (WHERE is_contactless NOT IN (0, 1) OR is_contactless IS NULL)::BIGINT
        AS invalid_is_contactless,
    count(*) FILTER (WHERE mcg_id = 35)::BIGINT AS mcg_35_transactions,
    count(*) FILTER (WHERE NOT is_mcg_classified)::BIGINT AS unclassified_mcg_transactions,
    count(*) FILTER (WHERE is_xb_consistent = false)::BIGINT AS is_xb_country_discrepancies,
    count(*) FILTER (WHERE is_xb_consistent IS NULL)::BIGINT AS is_xb_not_comparable,
    min(prch_date) AS min_prch_date,
    max(prch_date) AS max_prch_date
FROM analytics.transactions_enriched;

CREATE OR REPLACE TABLE audit.duplicate_profile AS
SELECT coalesce(sum(duplicate_count - 1), 0)::BIGINT AS identical_duplicate_rows
FROM (
    SELECT count(*)::BIGINT AS duplicate_count
    FROM raw.transactions
    GROUP BY
        card_id_raw,
        product_name_raw,
        product_type_raw,
        amt_raw,
        is_xb_raw,
        is_contactless_raw,
        prch_date_raw,
        prch_time_raw,
        ctry_card_raw,
        ctry_mrch_raw,
        mrch_raw,
        mcg_id_raw
    HAVING count(*) > 1
) AS duplicates;

CREATE OR REPLACE TABLE audit.quality_checks (
    check_name VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    actual_value VARCHAR NOT NULL,
    expected_value VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details VARCHAR NOT NULL
);

INSERT INTO audit.quality_checks
SELECT
    'original_column_count', 'error',
    (SELECT count(*) - 1 FROM pragma_table_info('raw.transactions'))::VARCHAR,
    '12',
    CASE WHEN (SELECT count(*) - 1 FROM pragma_table_info('raw.transactions')) = 12 THEN 'PASS' ELSE 'FAIL' END,
    'Columnas originales, excluyendo source_row_number.';

INSERT INTO audit.quality_checks
SELECT 'transaction_count', 'error', row_count::VARCHAR, '2400000',
    CASE WHEN row_count = 2400000 THEN 'PASS' ELSE 'FAIL' END,
    'Filas de transacciones preservadas.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'distinct_cards', 'error', distinct_cards::VARCHAR, '59997',
    CASE WHEN distinct_cards = 59997 THEN 'PASS' ELSE 'FAIL' END,
    'card_id se cuenta como identificador VARCHAR.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'credit_transactions', 'error', credit_transactions::VARCHAR, '2040959',
    CASE WHEN credit_transactions = 2040959 THEN 'PASS' ELSE 'FAIL' END,
    'Credit/Credito/Crédito normalizados a Crédito.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'debit_transactions', 'error', debit_transactions::VARCHAR, '359041',
    CASE WHEN debit_transactions = 359041 THEN 'PASS' ELSE 'FAIL' END,
    'Debit/Debito/Débito normalizados a Débito.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'unknown_product_type', 'error', unknown_product_type::VARCHAR, '0',
    CASE WHEN unknown_product_type = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Tipos no incluidos en las reglas explícitas; no se imputan.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'negative_transactions', 'warning', negative_transactions::VARCHAR, '2400',
    CASE WHEN negative_transactions = 2400 THEN 'PASS' ELSE 'FAIL' END,
    'Montos negativos conservados en DECIMAL(18,2).'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'invalid_amounts', 'error', invalid_amounts::VARCHAR, '0',
    CASE WHEN invalid_amounts = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Valores amt que no convierten a DECIMAL(18,2).'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'date_range', 'error', concat(min_prch_date::VARCHAR, ' to ', max_prch_date::VARCHAR),
    '2024-01-01 to 2024-06-30',
    CASE WHEN min_prch_date = DATE '2024-01-01' AND max_prch_date = DATE '2024-06-30'
        THEN 'PASS' ELSE 'FAIL' END,
    'Cobertura temporal luego de parsear DD/MM/YYYY y DD-MM-YYYY.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'invalid_dates', 'error', invalid_dates::VARCHAR, '0',
    CASE WHEN invalid_dates = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Fechas que no convierten con los dos formatos permitidos.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'invalid_times', 'error', invalid_times::VARCHAR, '0',
    CASE WHEN invalid_times = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Horas que no convierten con HH:MM:SS o HH.MM.SS.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'invalid_is_xb', 'error', invalid_is_xb::VARCHAR, '0',
    CASE WHEN invalid_is_xb = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Flags is_xb fuera de 0/1 o nulos.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'invalid_is_contactless', 'error', invalid_is_contactless::VARCHAR, '0',
    CASE WHEN invalid_is_contactless = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Flags is_contactless fuera de 0/1 o nulos.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'mcg_35_transactions', 'warning', mcg_35_transactions::VARCHAR, '12000',
    CASE WHEN mcg_35_transactions = 12000 THEN 'PASS' ELSE 'FAIL' END,
    'Código original 35, ausente del maestro MCG.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'unclassified_mcg_transactions', 'warning', unclassified_mcg_transactions::VARCHAR, '12000',
    CASE WHEN unclassified_mcg_transactions = 12000 THEN 'PASS' ELSE 'FAIL' END,
    'LEFT JOIN preserva estas filas y asigna Sin clasificar.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'is_xb_country_discrepancies', 'warning', is_xb_country_discrepancies::VARCHAR, '1440451',
    CASE WHEN is_xb_country_discrepancies = 1440451 THEN 'PASS' ELSE 'FAIL' END,
    'Diferencias entre is_xb original y comparación de países normalizados. No define cashback.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'is_xb_not_comparable', 'error', is_xb_not_comparable::VARCHAR, '0',
    CASE WHEN is_xb_not_comparable = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Filas sin flag o países suficientes para validar is_xb.'
FROM audit.dataset_profile;

INSERT INTO audit.quality_checks
SELECT 'identical_duplicate_rows', 'error', identical_duplicate_rows::VARCHAR, '0',
    CASE WHEN identical_duplicate_rows = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Duplicados exactos sobre las 12 columnas originales.'
FROM audit.duplicate_profile;

INSERT INTO audit.quality_checks
SELECT 'row_preservation_after_left_join', 'error',
    (SELECT count(*) FROM analytics.transactions_enriched)::VARCHAR,
    (SELECT count(*) FROM raw.transactions)::VARCHAR,
    CASE
        WHEN (SELECT count(*) FROM analytics.transactions_enriched) = (SELECT count(*) FROM raw.transactions)
        THEN 'PASS' ELSE 'FAIL'
    END,
    'La capa analítica no elimina transacciones.';

INSERT INTO audit.quality_checks
SELECT 'mcg_master_unique_keys', 'error',
    (SELECT count(*) - count(DISTINCT mcg) FROM staging.mcg)::VARCHAR,
    '0',
    CASE WHEN (SELECT count(*) - count(DISTINCT mcg) FROM staging.mcg) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Claves duplicadas en el maestro provocarían multiplicación de filas.';
