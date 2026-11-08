# Protocolo de validación · Power BI Masterplop

Checklist técnico y funcional del paquete público. Los controles financieros proceden de los agregados conciliados por DuckDB; el reporte no contiene detalle por tarjeta.

**Fecha de preparación:** 7 de noviembre de 2026

**Canal:** GitHub, con PBIX descargable, PDF, capturas y PBIP portable

**Estado esperado del validador:** OK

## 1. Artefactos de entrega

- [x] Masterplop_Executive.pbix abre correctamente en Power BI Desktop.
- [x] Masterplop_Executive.pdf contiene las tres páginas exportadas.
- [x] Las tres capturas corresponden al reporte renderizado.
- [x] powerbi/source/Masterplop_Executive.pbip es el proyecto público canónico.
- [x] El PBIP contiene PBIR, TMDL, logo y 15 agregados.
- [x] La carpeta pública no contiene cachés .pbi ni cache.abf.
- [x] Las copias locales heredadas permanecen ignoradas.

GitHub no renderiza el PBIX de forma interactiva. El PDF y las capturas permiten revisarlo en el navegador; Power BI Desktop habilita filtros y visuales.

## 2. Estructura del modelo

| Control | Esperado |
|---|---:|
| Páginas | 3 |
| Visuales | 49 |
| Tablas agregadas | 15 |
| Medidas DAX | 39 |
| Consultas M embebidas | 15 |
| Extractos CSV seguros | 15 |

- [x] Todos los JSON, PBIR y PBIP son parseables.
- [x] Cada tabla usa Binary.FromText con BinaryEncoding.Base64.
- [x] Ninguna partición pública usa File.Contents.
- [x] No existen rutas absolutas C:\Users en la fuente pública.

## 3. Resumen Ejecutivo

- [x] Tarjetas activas: **59.997**.
- [x] Transacciones: **2.400.000**.
- [x] Gasto neto: **USD 430.124.709,40**.
- [x] Ticket promedio: **USD 179,22**.
- [x] Cashback mayo: **USD 178.471,62**.
- [x] Tarjetas beneficiadas: **4.029**.
- [x] Top 5 MCG y mercados contactless están ordenados de mayor a menor.
- [x] El estado de calidad aparece como **Conciliado**.

## 4. Análisis Transaccional

- [x] 2024 T1 Crédito: **46.747** tarjetas.
- [x] 2024 T1 Débito: **8.224** tarjetas.
- [x] 2024 T2 Crédito: **51.037** tarjetas.
- [x] 2024 T2 Débito: **8.960** tarjetas.
- [x] Ticket crédito 2024 T1: **USD 3.229,40**.
- [x] Ticket crédito 2024 T2: **USD 5.019,38**.
- [x] El ticket regional usa país emisor y promedio por transacción.
- [x] Top 10 MCG usa gasto neto global como denominador.
- [x] El código 35 permanece como Sin clasificar.
- [x] Contactless se ordena de mayor a menor y controla denominador cero.
- [x] No se presentan T3 ni T4 como datos observados.

## 5. Campaña Mayo 2024

- [x] Transacciones elegibles: **28.915**.
- [x] Transacciones positivas: **28.885**.
- [x] Transacciones negativas: **30**.
- [x] Gasto neto elegible: **USD 7.319.379,70**.
- [x] Tarjetas beneficiadas: **4.029**.
- [x] Tarjetas topadas: **2.676**.
- [x] Costo oficial: **USD 178.471,62**.
- [x] Escenario sin descontar devoluciones: **USD 178.608,88**.
- [x] Escenario incorrecto con is_xb: **USD 135.160,88**.
- [x] La página explica ctry_mrch, agregación por tarjeta, tope y redondeo individual.
- [x] Los filtros transaccionales no alteran el costo fijo de mayo.

## 6. Privacidad y portabilidad

- [x] No se expone card_id.
- [x] No existe tabla de detalle transaccional.
- [x] No se referencia db_transac.csv.
- [x] No hay credenciales, secretos ni tokens.
- [x] No hay rutas personales en PBIR, TMDL, CSV o PBIP.
- [x] El escaneo binario básico del PBIX no detecta card_id, fuente cruda ni C:\Users.
- [x] Solo el PBIX aprobado queda exceptuado del bloqueo global de archivos .pbix.
- [x] Las bases DuckDB, el CSV fuente y cualquier PBIT siguen ignorados.

## 7. Experiencia visual

- [x] Logo, color corporativo y jerarquía visual son consistentes.
- [x] Las tres páginas se renderizan sin visuales rotos.
- [x] Títulos, métricas y notas principales se leen completos en el PDF.
- [x] Los montos usan USD y los porcentajes son consistentes.
- [x] La página de campaña muestra el cálculo oficial y sus sensibilidades.
- [x] Las vistas previas son suficientemente nítidas para revisión en GitHub.

## 8. Validación automatizada

Ejecutar desde la raíz:

~~~powershell
node ".\powerbi\generate_masterplop_powerbi.js"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\powerbi\validate_powerbi.ps1"
& ".\.runtime\python\python.exe" -m pytest tests -q --basetemp tmp/pytest-powerbi -p no:cacheprovider
git diff --check
~~~

El validador PowerShell comprueba:

1. artefactos compilados, PDF y capturas;
2. estructura 3 / 49 / 15 / 39;
3. consultas M embebidas y portables;
4. cifras de KPIs y cashback;
5. ausencia de datos restringidos;
6. visibilidad Git de los artefactos aprobados;
7. protección Git de cachés y copias locales.

## 9. Verificación posterior al push

Después de publicar, comprobar:

~~~text
https://github.com/cesarxbox32/masterplop-analytics-engineering/tree/main/powerbi
https://cesarxbox32.github.io/masterplop-analytics-engineering/
https://cesarxbox32.github.io/masterplop-analytics-engineering/powerbi/Masterplop_Executive.pdf
https://cesarxbox32.github.io/masterplop-analytics-engineering/powerbi/Masterplop_Executive.pbix
~~~

La publicación queda conciliada cuando el pipeline de calidad y GitHub Pages finalizan correctamente y los cuatro enlaces responden sin autenticación.

## 10. Criterio de aprobación

El paquete es apto para entrega si:

1. el validador Power BI devuelve Status = OK;
2. pytest no presenta fallos;
3. git diff --check no reporta errores;
4. el commit no incluye CSV fuente, DuckDB, cachés ni IDs;
5. las URLs públicas responden después del despliegue.
