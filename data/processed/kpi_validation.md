# Validación de indicadores

Los valores esperados se usan únicamente como pruebas; no forman parte de las fórmulas de los KPIs.

| Control | Actual | Esperado | Estado | Detalle |
|---|---:|---:|:---:|---|
| contactless_zero_denominator_guard | 0 | 0 | PASS | Si el gasto total de un país es cero, el porcentaje debe ser NULL. |
| global_net_spend | 430124709.40 | 430124709.40 | PASS | SUM(amt) de todas las transacciones, incluidos ajustes negativos y MCG sin maestro. |
| mcg_35_preserved_in_category_base | 1 | 1 | PASS | El código original 35 permanece como Sin clasificar en la base completa de categorías. |
| mcg_category_total_reconciles | 430124709.40 | 430124709.40 | PASS | La suma de todas las categorías, incluida Sin clasificar, reconcilia con el gasto neto global. |
| mcg_transaction_count_reconciles | 2400000 | 2400000 | PASS | Las categorías, incluido el código 35 sin maestro, cubren todas las transacciones. |
| no_invented_prepaid_rows | 0 | 0 | PASS | La vista de volumen no agrega tipos de producto inexistentes. |
| regional_only_south_america | 0 | 0 | PASS | La salida regional contiene solo países emisores sudamericanos. |
| ticket_2024_q1 | 3229.40 | 3229.40 | PASS | SUM(amt) neto de crédito / COUNT(DISTINCT card_id), 2024 T1. |
| ticket_2024_q2 | 5019.38 | 5019.38 | PASS | SUM(amt) neto de crédito / COUNT(DISTINCT card_id), 2024 T2. |
| top_10_row_count | 10 | 10 | PASS | El ranking final contiene exactamente diez categorías. |
| top_share_entertainment | 13.4029 | approximately 13.40 | PASS | Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales. |
| top_share_groceries | 22.1646 | approximately 22.16 | PASS | Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales. |
| top_share_restaurants | 17.1222 | approximately 17.12 | PASS | Participación porcentual sobre gasto neto global; tolerancia 0,02 puntos porcentuales. |
| volume_2024_q1_credit | 46747 | 46747 | PASS | COUNT(DISTINCT card_id), Crédito, 2024 T1. |
| volume_2024_q1_debit | 8224 | 8224 | PASS | COUNT(DISTINCT card_id), Débito, 2024 T1. |
| volume_2024_q2_credit | 51037 | 51037 | PASS | COUNT(DISTINCT card_id), Crédito, 2024 T2. |
| volume_2024_q2_debit | 8960 | 8960 | PASS | COUNT(DISTINCT card_id), Débito, 2024 T2. |
