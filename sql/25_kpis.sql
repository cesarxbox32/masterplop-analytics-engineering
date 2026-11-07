-- 1. Volumen: tarjetas activas distintas por año, trimestre y tipo normalizado.
CREATE OR REPLACE VIEW analytics.kpi_volume_quarterly AS
SELECT
    year(prch_date)::SMALLINT AS period_year,
    quarter(prch_date)::TINYINT AS period_quarter,
    date_trunc('quarter', prch_date)::DATE AS quarter_start_date,
    product_type,
    count(DISTINCT card_id)::BIGINT AS active_cards,
    count(*)::BIGINT AS transaction_count
FROM analytics.transactions_enriched
WHERE prch_date IS NOT NULL
  AND card_id IS NOT NULL
GROUP BY 1, 2, 3, 4;

COMMENT ON VIEW analytics.kpi_volume_quarterly IS
'Tarjetas distintas con al menos una transacción, separadas por año, trimestre real y tipo normalizado. active_cards usa COUNT(DISTINCT card_id), no COUNT(*).';


-- 2. Ticket trimestral: gasto neto de crédito por tarjeta de crédito activa.
CREATE OR REPLACE VIEW analytics.kpi_credit_ticket_quarterly AS
SELECT
    year(prch_date)::SMALLINT AS period_year,
    quarter(prch_date)::TINYINT AS period_quarter,
    date_trunc('quarter', prch_date)::DATE AS quarter_start_date,
    sum(amt)::DECIMAL(38,2) AS net_spend_usd,
    count(DISTINCT card_id)::BIGINT AS active_credit_cards,
    cast(
        sum(amt) / nullif(count(DISTINCT card_id), 0)
        AS DECIMAL(18,2)
    ) AS net_spend_per_active_card_usd
FROM analytics.transactions_enriched
WHERE product_type = 'Crédito'
  AND prch_date IS NOT NULL
  AND card_id IS NOT NULL
  AND amt IS NOT NULL
GROUP BY 1, 2, 3;

COMMENT ON VIEW analytics.kpi_credit_ticket_quarterly IS
'Gasto neto de crédito, incluidos ajustes negativos, dividido por tarjetas de crédito distintas activas en cada año y trimestre.';


-- 3. Ticket regional: promedio por transacción de crédito en mercados sudamericanos.
CREATE OR REPLACE VIEW analytics.kpi_credit_ticket_south_america AS
SELECT
    ctry_card AS issuer_country,
    product_name,
    count(*)::BIGINT AS transaction_count,
    sum(amt)::DECIMAL(38,2) AS net_spend_usd,
    cast(avg(amt) AS DECIMAL(18,2)) AS avg_transaction_amount_usd
FROM analytics.transactions_enriched
WHERE product_type = 'Crédito'
  AND ctry_card IN (
      'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Ecuador',
      'Guyana', 'Paraguay', 'Perú', 'Suriname', 'Uruguay', 'Venezuela'
  )
  AND amt IS NOT NULL
GROUP BY 1, 2;

COMMENT ON VIEW analytics.kpi_credit_ticket_south_america IS
'Monto promedio por transacción de crédito, agrupado por país emisor sudamericano y producto. ctry_card define el mercado emisor; no es un promedio por tarjeta.';


-- 4. Base completa por MCG. El total global incluye todas las transacciones,
-- también los códigos sin maestro que el LEFT JOIN marcó como Sin clasificar.
CREATE OR REPLACE VIEW analytics.kpi_mcg_spend_all AS
WITH global_spend AS (
    SELECT sum(amt)::DECIMAL(38,2) AS global_net_spend_usd
    FROM analytics.transactions_enriched
    WHERE amt IS NOT NULL
), category_spend AS (
    SELECT
        mcg_id AS mcg_code,
        mcg_code_original,
        mcg_name,
        count(*)::BIGINT AS transaction_count,
        sum(amt)::DECIMAL(38,2) AS net_spend_usd
    FROM analytics.transactions_enriched
    WHERE amt IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT
    row_number() OVER (
        ORDER BY category_spend.net_spend_usd DESC, category_spend.mcg_code
    )::INTEGER AS spend_rank,
    category_spend.mcg_code,
    category_spend.mcg_code_original,
    category_spend.mcg_name,
    category_spend.net_spend_usd,
    cast(
        category_spend.net_spend_usd * 100
        / nullif(global_spend.global_net_spend_usd, 0)
        AS DECIMAL(9,4)
    ) AS net_spend_share_pct,
    category_spend.transaction_count,
    global_spend.global_net_spend_usd
FROM category_spend
CROSS JOIN global_spend;

CREATE OR REPLACE VIEW analytics.kpi_top_10_mcg_spend AS
SELECT
    spend_rank,
    mcg_code,
    mcg_code_original,
    mcg_name,
    net_spend_usd,
    net_spend_share_pct,
    transaction_count,
    global_net_spend_usd
FROM analytics.kpi_mcg_spend_all
WHERE spend_rank <= 10;

COMMENT ON VIEW analytics.kpi_top_10_mcg_spend IS
'Diez categorías MCG con mayor gasto neto. La participación usa como denominador el gasto neto global, incluidos MCG sin referencia.';


-- 5. Adopción contactless por gasto neto y país emisor normalizado.
CREATE OR REPLACE VIEW analytics.kpi_contactless_adoption AS
SELECT
    ctry_card AS issuer_country,
    sum(
        CASE
            WHEN is_contactless = 1 THEN amt
            ELSE cast(0 AS DECIMAL(18,2))
        END
    )::DECIMAL(38,2) AS contactless_net_spend_usd,
    sum(amt)::DECIMAL(38,2) AS total_net_spend_usd,
    cast(
        sum(
            CASE
                WHEN is_contactless = 1 THEN amt
                ELSE cast(0 AS DECIMAL(18,2))
            END
        ) * 100
        / nullif(sum(amt), 0)
        AS DECIMAL(9,4)
    ) AS contactless_net_spend_pct,
    count(*) FILTER (WHERE is_contactless = 1)::BIGINT AS contactless_transaction_count,
    count(*)::BIGINT AS transaction_count
FROM analytics.transactions_enriched
WHERE ctry_card IS NOT NULL
  AND amt IS NOT NULL
GROUP BY 1
ORDER BY contactless_net_spend_pct DESC NULLS LAST, issuer_country;

COMMENT ON VIEW analytics.kpi_contactless_adoption IS
'Participación del gasto neto contactless sobre el gasto neto total por país emisor normalizado. NULLIF protege denominadores iguales a cero.';
