CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE OR REPLACE TABLE dashboard.executive_summary AS
SELECT
    count(DISTINCT t.card_id)::BIGINT AS active_cards,
    count(*)::BIGINT AS transaction_count,
    sum(t.amt)::DECIMAL(38,2) AS total_net_spend_usd,
    cast(avg(t.amt) AS DECIMAL(18,2)) AS avg_transaction_amount_usd,
    c.total_cashback_usd,
    c.beneficiary_card_count,
    min(t.prch_date) AS min_transaction_date,
    max(t.prch_date) AS max_transaction_date
FROM analytics.transactions_enriched AS t
CROSS JOIN analytics.cashback_may_2024_summary AS c
GROUP BY c.total_cashback_usd, c.beneficiary_card_count;

CREATE OR REPLACE TABLE dashboard.volume_quarterly AS
SELECT * FROM analytics.kpi_volume_quarterly;

CREATE OR REPLACE TABLE dashboard.credit_ticket_quarterly AS
SELECT * FROM analytics.kpi_credit_ticket_quarterly;

CREATE OR REPLACE TABLE dashboard.credit_ticket_south_america AS
SELECT * FROM analytics.kpi_credit_ticket_south_america;

CREATE OR REPLACE TABLE dashboard.top_10_mcg_spend AS
SELECT * FROM analytics.kpi_top_10_mcg_spend;

CREATE OR REPLACE TABLE dashboard.contactless_adoption AS
SELECT * FROM analytics.kpi_contactless_adoption;

CREATE OR REPLACE TABLE dashboard.cashback_summary AS
SELECT * FROM analytics.cashback_may_2024_summary;

CREATE OR REPLACE TABLE dashboard.cashback_sensitivity AS
SELECT * FROM analytics.cashback_may_2024_sensitivity_summary;

CREATE OR REPLACE TABLE dashboard.cashback_is_xb_diagnostic AS
SELECT * FROM analytics.cashback_may_2024_is_xb_summary;

CREATE OR REPLACE TABLE dashboard.cashback_eligibility_diagnostic AS
SELECT * FROM analytics.cashback_may_2024_eligibility_diagnostic;

CREATE OR REPLACE TABLE dashboard.data_quality_summary AS
SELECT
    p.row_count,
    p.invalid_amounts,
    p.invalid_dates,
    p.invalid_times,
    p.unclassified_mcg_transactions,
    p.is_xb_country_discrepancies,
    (SELECT count(*) FROM audit.quality_checks WHERE status = 'FAIL')::BIGINT
        AS failed_data_quality_checks,
    (SELECT count(*) FROM audit.kpi_checks WHERE status = 'FAIL')::BIGINT
        AS failed_kpi_checks,
    (SELECT count(*) FROM audit.cashback_checks WHERE status = 'FAIL')::BIGINT
        AS failed_cashback_checks
FROM audit.dataset_profile AS p;

-- La capa dashboard es física, agregada y segura para Streamlit.
-- No contiene card_id ni filas transaccionales individuales.
