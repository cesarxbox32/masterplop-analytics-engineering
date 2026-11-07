CREATE OR REPLACE TABLE audit.cashback_boundary_tests AS
WITH cases(test_name, net_spend_usd, expected_cashback_usd) AS (
    VALUES
        ('sin compras', NULL::DECIMAL(18,6), 0.00::DECIMAL(18,2)),
        ('saldo negativo', -100.00::DECIMAL(18,6), 0.00::DECIMAL(18,2)),
        ('compra pequeña', 10.00::DECIMAL(18,6), 0.70::DECIMAL(18,2)),
        ('gasto en umbral', 714.285714::DECIMAL(18,6), 50.00::DECIMAL(18,2)),
        ('gasto superior al tope', 1000.00::DECIMAL(18,6), 50.00::DECIMAL(18,2))
)
SELECT
    test_name,
    net_spend_usd,
    analytics.cashback_amount_usd(net_spend_usd) AS actual_cashback_usd,
    expected_cashback_usd,
    CASE
        WHEN analytics.cashback_amount_usd(net_spend_usd) = expected_cashback_usd
        THEN 'PASS' ELSE 'FAIL'
    END AS status
FROM cases;

CREATE OR REPLACE TABLE audit.cashback_checks (
    check_name VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    actual_value VARCHAR NOT NULL,
    expected_value VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details VARCHAR NOT NULL
);

INSERT INTO audit.cashback_checks
SELECT 'eligible_transactions', 'error', eligible_transaction_count::VARCHAR, '28915',
    CASE WHEN eligible_transaction_count = 28915 THEN 'PASS' ELSE 'FAIL' END,
    'Mayo 2024, crédito, emisor Chile y comercio fuera de Chile.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'positive_eligible_transactions', 'error', positive_eligible_transaction_count::VARCHAR, '28885',
    CASE WHEN positive_eligible_transaction_count = 28885 THEN 'PASS' ELSE 'FAIL' END,
    'Transacciones geográficamente elegibles con amt > 0.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'negative_eligible_transactions', 'error', negative_eligible_transaction_count::VARCHAR, '30',
    CASE WHEN negative_eligible_transaction_count = 30 THEN 'PASS' ELSE 'FAIL' END,
    'Ajustes o devoluciones elegibles con amt < 0, conservados en el escenario oficial.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'beneficiary_cards', 'error', beneficiary_card_count::VARCHAR, '4029',
    CASE WHEN beneficiary_card_count = 4029 THEN 'PASS' ELSE 'FAIL' END,
    'Tarjetas con cashback individual mayor que cero.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'net_eligible_spend', 'error', net_eligible_spend_usd::VARCHAR, '7319379.70',
    CASE WHEN net_eligible_spend_usd = 7319379.70 THEN 'PASS' ELSE 'FAIL' END,
    'Gasto mensual neto elegible después de descontar ajustes negativos.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'capped_cards', 'error', capped_card_count::VARCHAR, '2676',
    CASE WHEN capped_card_count = 2676 THEN 'PASS' ELSE 'FAIL' END,
    'Tarjetas cuyo 7% previo al redondeo supera USD 50.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'official_total_cashback', 'error', total_cashback_usd::VARCHAR, '178471.62',
    CASE WHEN total_cashback_usd = 178471.62 THEN 'PASS' ELSE 'FAIL' END,
    'Suma de cashback redondeado individualmente después de piso y tope.'
FROM analytics.cashback_may_2024_summary;

INSERT INTO audit.cashback_checks
SELECT 'positive_only_sensitivity', 'error', positive_only_cashback_usd::VARCHAR, '178608.88',
    CASE WHEN positive_only_cashback_usd = 178608.88 THEN 'PASS' ELSE 'FAIL' END,
    'Sensibilidad que excluye ajustes negativos en vez de descontarlos.'
FROM analytics.cashback_may_2024_sensitivity_summary;

INSERT INTO audit.cashback_checks
SELECT 'incorrect_is_xb_total', 'warning', incorrect_is_xb_cashback_usd::VARCHAR, '135160.88',
    CASE WHEN incorrect_is_xb_cashback_usd = 135160.88 THEN 'PASS' ELSE 'FAIL' END,
    'Costo erróneo al sustituir comercio fuera de Chile por is_xb=1.'
FROM analytics.cashback_may_2024_is_xb_summary;

INSERT INTO audit.cashback_checks
SELECT 'boundary_tests', 'error',
    count(*) FILTER (WHERE status = 'PASS')::VARCHAR,
    count(*)::VARCHAR,
    CASE WHEN count(*) = 5 AND count(*) FILTER (WHERE status = 'PASS') = 5
        THEN 'PASS' ELSE 'FAIL' END,
    'Casos sin compras, saldo negativo, compra pequeña, umbral y monto superior al tope.'
FROM audit.cashback_boundary_tests;

INSERT INTO audit.cashback_checks
SELECT 'individual_rounding_reconciliation', 'error',
    (SELECT sum(cashback_usd)::DECIMAL(38,2) FROM analytics.cashback_may_2024_individual)::VARCHAR,
    total_cashback_usd::VARCHAR,
    CASE
        WHEN (SELECT sum(cashback_usd)::DECIMAL(38,2) FROM analytics.cashback_may_2024_individual)
            = total_cashback_usd
        THEN 'PASS' ELSE 'FAIL'
    END,
    'El total oficial reconcilia con la suma de importes individuales ya redondeados.'
FROM analytics.cashback_may_2024_summary;
