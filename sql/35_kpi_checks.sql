CREATE OR REPLACE TABLE audit.kpi_checks (
    check_name VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    actual_value VARCHAR NOT NULL,
    expected_value VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details VARCHAR NOT NULL
);

INSERT INTO audit.kpi_checks
SELECT 'volume_2024_q1_credit', 'error', active_cards::VARCHAR, '46747',
    CASE WHEN active_cards = 46747 THEN 'PASS' ELSE 'FAIL' END,
    'COUNT(DISTINCT card_id), Crédito, 2024 T1.'
FROM analytics.kpi_volume_quarterly
WHERE period_year = 2024 AND period_quarter = 1 AND product_type = 'Crédito';

INSERT INTO audit.kpi_checks
SELECT 'volume_2024_q1_debit', 'error', active_cards::VARCHAR, '8224',
    CASE WHEN active_cards = 8224 THEN 'PASS' ELSE 'FAIL' END,
    'COUNT(DISTINCT card_id), Débito, 2024 T1.'
FROM analytics.kpi_volume_quarterly
WHERE period_year = 2024 AND period_quarter = 1 AND product_type = 'Débito';

INSERT INTO audit.kpi_checks
SELECT 'volume_2024_q2_credit', 'error', active_cards::VARCHAR, '51037',
    CASE WHEN active_cards = 51037 THEN 'PASS' ELSE 'FAIL' END,
    'COUNT(DISTINCT card_id), Crédito, 2024 T2.'
FROM analytics.kpi_volume_quarterly
WHERE period_year = 2024 AND period_quarter = 2 AND product_type = 'Crédito';

INSERT INTO audit.kpi_checks
SELECT 'volume_2024_q2_debit', 'error', active_cards::VARCHAR, '8960',
    CASE WHEN active_cards = 8960 THEN 'PASS' ELSE 'FAIL' END,
    'COUNT(DISTINCT card_id), Débito, 2024 T2.'
FROM analytics.kpi_volume_quarterly
WHERE period_year = 2024 AND period_quarter = 2 AND product_type = 'Débito';

INSERT INTO audit.kpi_checks
SELECT 'ticket_2024_q1', 'error', net_spend_per_active_card_usd::VARCHAR, '3229.40',
    CASE WHEN net_spend_per_active_card_usd = 3229.40 THEN 'PASS' ELSE 'FAIL' END,
    'SUM(amt) neto de crédito / COUNT(DISTINCT card_id), 2024 T1.'
FROM analytics.kpi_credit_ticket_quarterly
WHERE period_year = 2024 AND period_quarter = 1;

INSERT INTO audit.kpi_checks
SELECT 'ticket_2024_q2', 'error', net_spend_per_active_card_usd::VARCHAR, '5019.38',
    CASE WHEN net_spend_per_active_card_usd = 5019.38 THEN 'PASS' ELSE 'FAIL' END,
    'SUM(amt) neto de crédito / COUNT(DISTINCT card_id), 2024 T2.'
FROM analytics.kpi_credit_ticket_quarterly
WHERE period_year = 2024 AND period_quarter = 2;

INSERT INTO audit.kpi_checks
SELECT 'global_net_spend', 'error', sum(amt)::DECIMAL(38,2)::VARCHAR, '430124709.40',
    CASE WHEN sum(amt)::DECIMAL(38,2) = 430124709.40 THEN 'PASS' ELSE 'FAIL' END,
    'SUM(amt) de todas las transacciones, incluidos ajustes negativos y MCG sin maestro.'
FROM analytics.transactions_enriched;

INSERT INTO audit.kpi_checks
SELECT 'top_share_groceries', 'error', net_spend_share_pct::VARCHAR, 'approximately 22.16',
    CASE WHEN abs(net_spend_share_pct - 22.16) <= 0.02 THEN 'PASS' ELSE 'FAIL' END,
    'Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales.'
FROM analytics.kpi_mcg_spend_all
WHERE mcg_name = 'Groceries and Supermarkets';

INSERT INTO audit.kpi_checks
SELECT 'top_share_restaurants', 'error', net_spend_share_pct::VARCHAR, 'approximately 17.12',
    CASE WHEN abs(net_spend_share_pct - 17.12) <= 0.02 THEN 'PASS' ELSE 'FAIL' END,
    'Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales.'
FROM analytics.kpi_mcg_spend_all
WHERE mcg_name = 'Restaurants and Dining';

INSERT INTO audit.kpi_checks
SELECT 'top_share_entertainment', 'error', net_spend_share_pct::VARCHAR, 'approximately 13.40',
    CASE WHEN abs(net_spend_share_pct - 13.40) <= 0.02 THEN 'PASS' ELSE 'FAIL' END,
    'Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales.'
FROM analytics.kpi_mcg_spend_all
WHERE mcg_name = 'Entertainment';

INSERT INTO audit.kpi_checks
SELECT 'top_10_row_count', 'error', count(*)::VARCHAR, '10',
    CASE WHEN count(*) = 10 THEN 'PASS' ELSE 'FAIL' END,
    'El ranking final contiene exactamente diez categorías.'
FROM analytics.kpi_top_10_mcg_spend;

INSERT INTO audit.kpi_checks
SELECT 'mcg_35_preserved_in_category_base', 'error', count(*)::VARCHAR, '1',
    CASE WHEN count(*) = 1 THEN 'PASS' ELSE 'FAIL' END,
    'El código original 35 permanece como Sin clasificar en la base completa de categorías.'
FROM analytics.kpi_mcg_spend_all
WHERE mcg_code = 35
  AND mcg_code_original = '35'
  AND mcg_name = 'Sin clasificar'
  AND transaction_count = 12000;

INSERT INTO audit.kpi_checks
SELECT 'mcg_category_total_reconciles', 'error',
    sum(net_spend_usd)::DECIMAL(38,2)::VARCHAR,
    max(global_net_spend_usd)::DECIMAL(38,2)::VARCHAR,
    CASE
        WHEN sum(net_spend_usd)::DECIMAL(38,2) = max(global_net_spend_usd)::DECIMAL(38,2)
        THEN 'PASS' ELSE 'FAIL'
    END,
    'La suma de todas las categorías, incluida Sin clasificar, reconcilia con el gasto neto global.'
FROM analytics.kpi_mcg_spend_all;

INSERT INTO audit.kpi_checks
SELECT 'mcg_transaction_count_reconciles', 'error',
    sum(transaction_count)::VARCHAR,
    '2400000',
    CASE WHEN sum(transaction_count) = 2400000 THEN 'PASS' ELSE 'FAIL' END,
    'Las categorías, incluido el código 35 sin maestro, cubren todas las transacciones.'
FROM analytics.kpi_mcg_spend_all;

INSERT INTO audit.kpi_checks
SELECT 'no_invented_prepaid_rows', 'error', count(*)::VARCHAR, '0',
    CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'La vista de volumen no agrega tipos de producto inexistentes.'
FROM analytics.kpi_volume_quarterly
WHERE lower(product_type) IN ('prepago', 'prepaid');

INSERT INTO audit.kpi_checks
SELECT 'contactless_zero_denominator_guard', 'error', count(*)::VARCHAR, '0',
    CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Si el gasto total de un país es cero, el porcentaje debe ser NULL.'
FROM analytics.kpi_contactless_adoption
WHERE total_net_spend_usd = 0
  AND contactless_net_spend_pct IS NOT NULL;

INSERT INTO audit.kpi_checks
SELECT 'regional_only_south_america', 'error', count(*)::VARCHAR, '0',
    CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'La salida regional contiene solo países emisores sudamericanos.'
FROM analytics.kpi_credit_ticket_south_america
WHERE issuer_country NOT IN (
    'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Ecuador',
    'Guyana', 'Paraguay', 'Perú', 'Suriname', 'Uruguay', 'Venezuela'
);
