# Cashback Masterplop — mayo 2024

Este reporte contiene solo resultados agregados. Los cálculos individuales permanecen dentro de DuckDB.

## Resultado oficial

- Transacciones elegibles: 28915
- Transacciones positivas: 28885
- Transacciones negativas: 30
- Tarjetas beneficiadas: 4029
- Tarjetas topadas: 2676
- Gasto neto elegible (USD): 7319379.70
- Cashback sin tope, redondeado por tarjeta (USD): 512358.63
- Ahorro por tope (USD): 333887.01
- Costo total oficial (USD): 178471.62

## Sensibilidades

- Sin descontar devoluciones (USD): 178608.88
- Incremento frente al escenario neto (USD): 137.26
- Uso incorrecto de is_xb (USD): 135160.88
- Diferencia is_xb frente al oficial (USD): -43310.74

## Controles

| Control | Actual | Esperado | Estado |
|---|---:|---:|:---:|
| beneficiary_cards | 4029 | 4029 | PASS |
| boundary_tests | 5 | 5 | PASS |
| capped_cards | 2676 | 2676 | PASS |
| eligible_transactions | 28915 | 28915 | PASS |
| incorrect_is_xb_total | 135160.88 | 135160.88 | PASS |
| individual_rounding_reconciliation | 178471.62 | 178471.62 | PASS |
| negative_eligible_transactions | 30 | 30 | PASS |
| net_eligible_spend | 7319379.70 | 7319379.70 | PASS |
| official_total_cashback | 178471.62 | 178471.62 | PASS |
| positive_eligible_transactions | 28885 | 28885 | PASS |
| positive_only_sensitivity | 178608.88 | 178608.88 | PASS |
