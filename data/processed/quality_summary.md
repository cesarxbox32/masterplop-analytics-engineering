# Resumen de calidad de datos

Este archivo se genera con `src/pipeline.py`. Contiene solo resultados agregados; no publica identificadores de tarjeta.

| Control | Severidad | Actual | Esperado | Estado | Detalle |
|---|---:|---:|---:|:---:|---|
| credit_transactions | error | 2040959 | 2040959 | PASS | Credit/Credito/Crédito normalizados a Crédito. |
| date_range | error | 2024-01-01 to 2024-06-30 | 2024-01-01 to 2024-06-30 | PASS | Cobertura temporal luego de parsear DD/MM/YYYY y DD-MM-YYYY. |
| debit_transactions | error | 359041 | 359041 | PASS | Debit/Debito/Débito normalizados a Débito. |
| distinct_cards | error | 59997 | 59997 | PASS | card_id se cuenta como identificador VARCHAR. |
| identical_duplicate_rows | error | 0 | 0 | PASS | Duplicados exactos sobre las 12 columnas originales. |
| invalid_amounts | error | 0 | 0 | PASS | Valores amt que no convierten a DECIMAL(18,2). |
| invalid_dates | error | 0 | 0 | PASS | Fechas que no convierten con los dos formatos permitidos. |
| invalid_is_contactless | error | 0 | 0 | PASS | Flags is_contactless fuera de 0/1 o nulos. |
| invalid_is_xb | error | 0 | 0 | PASS | Flags is_xb fuera de 0/1 o nulos. |
| invalid_times | error | 0 | 0 | PASS | Horas que no convierten con HH:MM:SS o HH.MM.SS. |
| is_xb_country_discrepancies | warning | 1440451 | 1440451 | PASS | Diferencias entre is_xb original y comparación de países normalizados. No define cashback. |
| is_xb_not_comparable | error | 0 | 0 | PASS | Filas sin flag o países suficientes para validar is_xb. |
| mcg_35_transactions | warning | 12000 | 12000 | PASS | Código original 35, ausente del maestro MCG. |
| mcg_master_unique_keys | error | 0 | 0 | PASS | Claves duplicadas en el maestro provocarían multiplicación de filas. |
| negative_transactions | warning | 2400 | 2400 | PASS | Montos negativos conservados en DECIMAL(18,2). |
| original_column_count | error | 12 | 12 | PASS | Columnas originales, excluyendo source_row_number. |
| row_preservation_after_left_join | error | 2400000 | 2400000 | PASS | La capa analítica no elimina transacciones. |
| transaction_count | error | 2400000 | 2400000 | PASS | Filas de transacciones preservadas. |
| unclassified_mcg_transactions | warning | 12000 | 12000 | PASS | LEFT JOIN preserva estas filas y asigna Sin clasificar. |
| unknown_product_type | error | 0 | 0 | PASS | Tipos no incluidos en las reglas explícitas; no se imputan. |

## Reglas aplicadas

- El CSV se ingiere inicialmente como texto UTF-8 y se tipa de forma explícita en `staging.transactions`.
- `card_id` permanece como `VARCHAR`.
- Los tipos Credit/Credito/Crédito y Debit/Debito/Débito se normalizan a Crédito y Débito.
- Se unifican las variantes indicadas de Brasil, México, Perú, Panamá y República Dominicana.
- Las fechas aceptan DD/MM/YYYY y DD-MM-YYYY. Las horas aceptan HH:MM:SS y HH.MM.SS.
- `amt` se convierte a `DECIMAL(18,2)` y se conservan los montos negativos.
- El maestro MCG se une con `LEFT JOIN`; las claves no encontradas quedan como `Sin clasificar` y conservan su código original.
- `is_xb` original se conserva. Su comparación con países normalizados es únicamente un control de calidad y no una regla de cashback.
