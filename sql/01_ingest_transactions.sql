CREATE TABLE raw.transactions AS
SELECT
    row_number() OVER ()::BIGINT AS source_row_number,
    card_id AS card_id_raw,
    product_name AS product_name_raw,
    product_type AS product_type_raw,
    amt AS amt_raw,
    is_xb AS is_xb_raw,
    is_contactless AS is_contactless_raw,
    prch_date AS prch_date_raw,
    prch_time AS prch_time_raw,
    ctry_card AS ctry_card_raw,
    ctry_mrch AS ctry_mrch_raw,
    mrch AS mrch_raw,
    mcg_id AS mcg_id_raw
FROM read_csv(
    '{{DB_TRANSAC_PATH}}',
    header = true,
    all_varchar = true,
    encoding = 'utf-8',
    strict_mode = true,
    null_padding = false,
    ignore_errors = false
);
