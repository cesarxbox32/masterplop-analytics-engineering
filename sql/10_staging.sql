CREATE OR REPLACE VIEW staging.transactions AS
WITH parsed AS (
    SELECT
        source_row_number,
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
        mcg_id_raw,
        nullif(trim(card_id_raw), '') AS card_id,
        nullif(trim(product_name_raw), '') AS product_name,
        CASE
            WHEN lower(trim(product_type_raw)) IN ('credit', 'credito', 'crédito') THEN 'Crédito'
            WHEN lower(trim(product_type_raw)) IN ('debit', 'debito', 'débito') THEN 'Débito'
            ELSE nullif(trim(product_type_raw), '')
        END AS product_type,
        try_cast(trim(amt_raw) AS DECIMAL(18,2)) AS amt,
        try_cast(trim(is_xb_raw) AS TINYINT) AS is_xb,
        try_cast(trim(is_contactless_raw) AS TINYINT) AS is_contactless,
        coalesce(
            try_strptime(trim(prch_date_raw), '%d/%m/%Y')::DATE,
            try_strptime(trim(prch_date_raw), '%d-%m-%Y')::DATE
        ) AS prch_date,
        coalesce(
            try_strptime(trim(prch_time_raw), '%H:%M:%S')::TIME,
            try_strptime(trim(prch_time_raw), '%H.%M.%S')::TIME
        ) AS prch_time,
        CASE
            WHEN lower(trim(ctry_card_raw)) IN ('brasil', 'brazil') THEN 'Brasil'
            WHEN lower(trim(ctry_card_raw)) IN ('mexico', 'méxico') THEN 'México'
            WHEN lower(trim(ctry_card_raw)) IN ('peru', 'perú') THEN 'Perú'
            WHEN lower(trim(ctry_card_raw)) IN ('panama', 'panamá') THEN 'Panamá'
            WHEN lower(trim(ctry_card_raw)) IN ('republica dominicana', 'república dominicana')
                THEN 'República Dominicana'
            ELSE nullif(trim(ctry_card_raw), '')
        END AS ctry_card,
        CASE
            WHEN lower(trim(ctry_mrch_raw)) IN ('brasil', 'brazil') THEN 'Brasil'
            WHEN lower(trim(ctry_mrch_raw)) IN ('mexico', 'méxico') THEN 'México'
            WHEN lower(trim(ctry_mrch_raw)) IN ('peru', 'perú') THEN 'Perú'
            WHEN lower(trim(ctry_mrch_raw)) IN ('panama', 'panamá') THEN 'Panamá'
            WHEN lower(trim(ctry_mrch_raw)) IN ('republica dominicana', 'república dominicana')
                THEN 'República Dominicana'
            ELSE nullif(trim(ctry_mrch_raw), '')
        END AS ctry_mrch,
        nullif(trim(mrch_raw), '') AS mrch,
        try_cast(trim(mcg_id_raw) AS INTEGER) AS mcg_id
    FROM raw.transactions
)
SELECT
    *,
    prch_date + prch_time AS prch_timestamp,
    CASE
        WHEN ctry_card IS NULL OR ctry_mrch IS NULL THEN NULL
        ELSE (ctry_card <> ctry_mrch)::TINYINT
    END AS is_xb_derived,
    CASE
        WHEN is_xb NOT IN (0, 1) OR ctry_card IS NULL OR ctry_mrch IS NULL THEN NULL
        ELSE is_xb = (ctry_card <> ctry_mrch)::TINYINT
    END AS is_xb_consistent,
    card_id IS NOT NULL AS is_valid_card_id,
    amt IS NOT NULL AS is_valid_amt,
    is_xb IN (0, 1) AS is_valid_is_xb,
    is_contactless IN (0, 1) AS is_valid_is_contactless,
    prch_date IS NOT NULL AS is_valid_prch_date,
    prch_time IS NOT NULL AS is_valid_prch_time,
    mcg_id IS NOT NULL AS is_valid_mcg_id
FROM parsed;

CREATE OR REPLACE VIEW staging.mcg AS
SELECT
    source_row_number,
    mcg_raw,
    mcg_name_raw,
    try_cast(trim(mcg_raw) AS INTEGER) AS mcg,
    nullif(trim(mcg_name_raw), '') AS mcg_name,
    try_cast(trim(mcg_raw) AS INTEGER) IS NOT NULL AS is_valid_mcg,
    nullif(trim(mcg_name_raw), '') IS NOT NULL AS is_valid_mcg_name
FROM raw.mcg;
