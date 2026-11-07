-- Foto de las filas RAW de sales/items/payments/expenses de una sucursal creadas desde una fecha.
-- Sirve para comparar una corrida con ventana móvil contra una con FORCE_FULL_REFRESH=true.
-- Uso (dentro del contenedor db):
--   psql -U etl -d fudo_local -v snap=snap_ventana -v branch=amoremio-guemes -v desde=2026-08-31 -f /tools/window_snapshot.sql
DROP TABLE IF EXISTS public.:"snap";
CREATE TABLE public.:"snap" AS
          SELECT 'sales'    AS entity, id_fudo, payload_checksum FROM public.fudo_raw_sales
           WHERE id_sucursal_fuente = :'branch' AND last_updated_at_fudo >= :'desde'::timestamptz
UNION ALL SELECT 'items',    id_fudo, payload_checksum FROM public.fudo_raw_items
           WHERE id_sucursal_fuente = :'branch' AND last_updated_at_fudo >= :'desde'::timestamptz
UNION ALL SELECT 'payments', id_fudo, payload_checksum FROM public.fudo_raw_payments
           WHERE id_sucursal_fuente = :'branch' AND last_updated_at_fudo >= :'desde'::timestamptz
UNION ALL SELECT 'expenses', id_fudo, payload_checksum FROM public.fudo_raw_expenses
           WHERE id_sucursal_fuente = :'branch' AND last_updated_at_fudo >= :'desde'::timestamptz;
SELECT entity, count(*) AS filas FROM public.:"snap" GROUP BY entity ORDER BY entity;
