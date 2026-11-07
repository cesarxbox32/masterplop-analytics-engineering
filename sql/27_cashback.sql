-- Política monetaria reutilizable. COALESCE permite probar explícitamente el caso
-- sin compras; en producción solo se invoca después de agregar por tarjeta.
CREATE OR REPLACE MACRO analytics.cashback_amount_usd(net_spend) AS
    cast(
        round(
            least(
                cast(50.00 AS DECIMAL(18,2)),
                greatest(
                    cast(0.00 AS DECIMAL(18,2)),
                    coalesce(net_spend, cast(0.00 AS DECIMAL(18,2)))
                        * cast(0.07 AS DECIMAL(4,2))
                )
            ),
            2
        )
        AS DECIMAL(18,2)
    );

CREATE OR REPLACE MACRO analytics.uncapped_cashback_amount_usd(net_spend) AS
    cast(
        round(
            greatest(
                cast(0.00 AS DECIMAL(18,2)),
                coalesce(net_spend, cast(0.00 AS DECIMAL(18,2)))
                    * cast(0.07 AS DECIMAL(4,2))
            ),
            2
        )
        AS DECIMAL(18,2)
    );


-- 1. Transacciones geográficamente elegibles según el PDF.
-- is_xb se conserva únicamente para diagnóstico y no participa en el filtro.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_eligible_transactions AS
SELECT
    source_row_number,
    card_id,
    product_type,
    prch_date,
    amt,
    is_xb,
    ctry_card,
    ctry_mrch
FROM analytics.transactions_enriched
WHERE prch_date >= DATE '2024-05-01'
  AND prch_date < DATE '2024-06-01'
  AND product_type = 'Crédito'
  AND ctry_card = 'Chile'
  AND ctry_mrch <> 'Chile';


-- 2. Gasto mensual neto por tarjeta. Las devoluciones y ajustes negativos
-- reducen el gasto antes de aplicar porcentaje, piso y tope.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_by_card AS
SELECT
    card_id,
    count(*)::BIGINT AS eligible_transaction_count,
    count(*) FILTER (WHERE amt > 0)::BIGINT AS positive_transaction_count,
    count(*) FILTER (WHERE amt < 0)::BIGINT AS negative_transaction_count,
    sum(amt)::DECIMAL(38,2) AS net_eligible_spend_usd
FROM analytics.cashback_may_2024_eligible_transactions
GROUP BY card_id;


-- 3. Cálculo individual. El redondeo ocurre por tarjeta antes de cualquier suma.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_individual AS
SELECT
    card_id,
    eligible_transaction_count,
    positive_transaction_count,
    negative_transaction_count,
    net_eligible_spend_usd,
    greatest(
        cast(0.00 AS DECIMAL(18,2)),
        net_eligible_spend_usd * cast(0.07 AS DECIMAL(4,2))
    )::DECIMAL(38,4) AS uncapped_cashback_raw_usd,
    analytics.uncapped_cashback_amount_usd(net_eligible_spend_usd)
        AS uncapped_cashback_rounded_usd,
    analytics.cashback_amount_usd(net_eligible_spend_usd) AS cashback_usd,
    (
        net_eligible_spend_usd * cast(0.07 AS DECIMAL(4,2))
        > cast(50.00 AS DECIMAL(18,2))
    ) AS is_capped
FROM analytics.cashback_may_2024_by_card;


-- 4. Resumen oficial agregado y seguro para publicación.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_summary AS
SELECT
    DATE '2024-05-01' AS campaign_month,
    sum(eligible_transaction_count)::BIGINT AS eligible_transaction_count,
    sum(positive_transaction_count)::BIGINT AS positive_eligible_transaction_count,
    sum(negative_transaction_count)::BIGINT AS negative_eligible_transaction_count,
    count(*)::BIGINT AS eligible_card_count,
    count(*) FILTER (WHERE cashback_usd > 0)::BIGINT AS beneficiary_card_count,
    count(*) FILTER (WHERE is_capped)::BIGINT AS capped_card_count,
    sum(net_eligible_spend_usd)::DECIMAL(38,2) AS net_eligible_spend_usd,
    sum(uncapped_cashback_rounded_usd)::DECIMAL(38,2)
        AS uncapped_cashback_rounded_usd,
    sum(cashback_usd)::DECIMAL(38,2) AS total_cashback_usd,
    (
        sum(uncapped_cashback_rounded_usd) - sum(cashback_usd)
    )::DECIMAL(38,2) AS cap_savings_usd,
    cast(
        round(
            sum(
                least(
                    cast(50.00 AS DECIMAL(18,2)),
                    greatest(
                        cast(0.00 AS DECIMAL(18,2)),
                        net_eligible_spend_usd * cast(0.07 AS DECIMAL(4,2))
                    )
                )
            ),
            2
        ) AS DECIMAL(38,2)
    ) AS cashback_if_rounded_after_sum_usd,
    (
        cast(
            round(
                sum(
                    least(
                        cast(50.00 AS DECIMAL(18,2)),
                        greatest(
                            cast(0.00 AS DECIMAL(18,2)),
                            net_eligible_spend_usd * cast(0.07 AS DECIMAL(4,2))
                        )
                    )
                ),
                2
            ) AS DECIMAL(38,2)
        ) - sum(cashback_usd)
    )::DECIMAL(38,2) AS rounding_timing_difference_usd,
    cast(
        round(
            greatest(
                cast(0.00 AS DECIMAL(18,2)),
                sum(net_eligible_spend_usd) * cast(0.07 AS DECIMAL(4,2))
            ),
            2
        ) AS DECIMAL(38,2)
    ) AS seven_pct_of_global_net_spend_usd
FROM analytics.cashback_may_2024_individual;

COMMENT ON VIEW analytics.cashback_may_2024_summary IS
'Resumen oficial de cashback de mayo 2024. Usa país del comercio, gasto mensual neto por tarjeta, piso cero, tope USD 50 y redondeo individual antes de sumar.';


-- 5. Sensibilidad: ignora las devoluciones en lugar de descontarlas.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_positive_only_by_card AS
SELECT
    card_id,
    count(*)::BIGINT AS positive_transaction_count,
    sum(amt)::DECIMAL(38,2) AS positive_eligible_spend_usd
FROM analytics.cashback_may_2024_eligible_transactions
WHERE amt > 0
GROUP BY card_id;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_positive_only_individual AS
SELECT
    card_id,
    positive_transaction_count,
    positive_eligible_spend_usd,
    analytics.cashback_amount_usd(positive_eligible_spend_usd) AS cashback_usd
FROM analytics.cashback_may_2024_positive_only_by_card;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_sensitivity_summary AS
SELECT
    count(*)::BIGINT AS eligible_card_count,
    count(*) FILTER (WHERE cashback_usd > 0)::BIGINT AS beneficiary_card_count,
    sum(positive_transaction_count)::BIGINT AS positive_eligible_transaction_count,
    sum(positive_eligible_spend_usd)::DECIMAL(38,2) AS positive_eligible_spend_usd,
    sum(cashback_usd)::DECIMAL(38,2) AS positive_only_cashback_usd,
    (
        sum(cashback_usd)
        - (SELECT total_cashback_usd FROM analytics.cashback_may_2024_summary)
    )::DECIMAL(38,2) AS incremental_cost_vs_net_usd
FROM analytics.cashback_may_2024_positive_only_individual;


-- 6. Error de usar is_xb=1 en reemplazo de la condición geográfica.
CREATE OR REPLACE VIEW analytics.cashback_may_2024_is_xb_transactions AS
SELECT
    source_row_number,
    card_id,
    product_type,
    prch_date,
    amt,
    is_xb,
    ctry_card,
    ctry_mrch
FROM analytics.transactions_enriched
WHERE prch_date >= DATE '2024-05-01'
  AND prch_date < DATE '2024-06-01'
  AND product_type = 'Crédito'
  AND ctry_card = 'Chile'
  AND is_xb = 1;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_is_xb_by_card AS
SELECT
    card_id,
    count(*)::BIGINT AS eligible_transaction_count,
    sum(amt)::DECIMAL(38,2) AS net_eligible_spend_usd
FROM analytics.cashback_may_2024_is_xb_transactions
GROUP BY card_id;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_is_xb_individual AS
SELECT
    card_id,
    eligible_transaction_count,
    net_eligible_spend_usd,
    analytics.cashback_amount_usd(net_eligible_spend_usd) AS cashback_usd
FROM analytics.cashback_may_2024_is_xb_by_card;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_is_xb_summary AS
SELECT
    sum(eligible_transaction_count)::BIGINT AS is_xb_eligible_transaction_count,
    count(*) FILTER (WHERE cashback_usd > 0)::BIGINT AS beneficiary_card_count,
    sum(net_eligible_spend_usd)::DECIMAL(38,2) AS net_eligible_spend_usd,
    sum(cashback_usd)::DECIMAL(38,2) AS incorrect_is_xb_cashback_usd,
    (
        sum(cashback_usd)
        - (SELECT total_cashback_usd FROM analytics.cashback_may_2024_summary)
    )::DECIMAL(38,2) AS difference_vs_official_usd
FROM analytics.cashback_may_2024_is_xb_individual;

CREATE OR REPLACE VIEW analytics.cashback_may_2024_eligibility_diagnostic AS
WITH may_credit_chile AS (
    SELECT
        amt,
        ctry_mrch <> 'Chile' AS eligible_by_geography,
        is_xb = 1 AS eligible_by_is_xb
    FROM analytics.transactions_enriched
    WHERE prch_date >= DATE '2024-05-01'
      AND prch_date < DATE '2024-06-01'
      AND product_type = 'Crédito'
      AND ctry_card = 'Chile'
)
SELECT
    CASE
        WHEN eligible_by_geography AND eligible_by_is_xb THEN 'Coincide: elegible por ambos'
        WHEN eligible_by_geography AND NOT eligible_by_is_xb THEN 'Omitida por is_xb'
        WHEN NOT eligible_by_geography AND eligible_by_is_xb THEN 'Incluida erróneamente por is_xb'
        ELSE 'No elegible por ambos'
    END AS diagnostic_status,
    count(*)::BIGINT AS transaction_count,
    sum(amt)::DECIMAL(38,2) AS net_spend_usd
FROM may_credit_chile
GROUP BY 1;
