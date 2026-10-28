-- ######################################################################
-- #            SCRIPT DE TABLAS RAW Y METADATOS BASE (GENÉRICO)        #
-- ######################################################################

-- ----------------------------------------------------------------------
-- 1. TABLAS DE METADATOS Y CONFIGURACIÓN DEL ETL
-- ----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.etl_fudo_tokens (
    id_sucursal VARCHAR(255) PRIMARY KEY,
    access_token TEXT NOT NULL,
    token_expiration_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    last_updated_utc TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.etl_fudo_extraction_status (
    id_sucursal VARCHAR(255) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    last_successful_extraction_utc TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id_sucursal, entity_name)
);

CREATE TABLE IF NOT EXISTS public.config_fudo_branches (
    id_branch_nro SERIAL,            -- Antes id_sucursal_nro
    id_branch VARCHAR(255) PRIMARY KEY, -- Antes id_sucursal
    fudo_branch_identifier VARCHAR(255),
    branch_name VARCHAR(255),        -- Antes sucursal_name
    secret_manager_apikey_name VARCHAR(255) NOT NULL,
    secret_manager_apisecret_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------
-- 2. TABLAS PARA LA CAPA DE DATOS CRUDOS (RAW LAYER)
-- ----------------------------------------------------------------------
-- NOTA: Todas las PK incluyen payload_checksum para permitir el Full Refresh 
-- y evitar errores de "Duplicate Key" si la API manda basura en el mismo lote.

CREATE TABLE IF NOT EXISTS public.fudo_raw_customers (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL, 
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_discounts (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_expenses (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_expense_categories (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_ingredients (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_items (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_kitchens (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_payments (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_payment_methods (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_product_categories (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_product_modifiers (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_products ( 
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_roles (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_rooms (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_sales (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum) -- <--- CORREGIDO: Clave de 3 columnas
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_tables (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_users (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

CREATE TABLE IF NOT EXISTS public.fudo_raw_providers (
    id_fudo TEXT NOT NULL, id_sucursal_fuente VARCHAR(255) NOT NULL, 
    fecha_extraccion_utc TIMESTAMP WITH TIME ZONE NOT NULL, payload_json JSONB NOT NULL, 
    last_updated_at_fudo TIMESTAMP WITH TIME ZONE, payload_checksum TEXT NOT NULL,
    PRIMARY KEY (id_fudo, id_sucursal_fuente, payload_checksum)
);

-- ----------------------------------------------------------------------
-- 3. ÍNDICES POR SUCURSAL (RAW Y STAGING)
-- ----------------------------------------------------------------------
-- El Full Refresh borra/copia los datos de UNA sucursal (WHERE id_sucursal_fuente = ...).
-- La PK empieza por id_fudo y no sirve para ese filtro: sin este índice se recorre la tabla entera.
-- Las tablas staging nuevas lo heredan por el LIKE ... INCLUDING ALL; acá se cubren las que ya existían.

DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
          AND (tablename LIKE 'fudo\_raw\_%' OR tablename LIKE 'stg\_fudo\_raw\_%')
          -- Una staging creada con LIKE ya trae el índice copiado (con otro nombre): no duplicarlo
          AND NOT EXISTS (
              SELECT 1 FROM pg_indexes i
              WHERE i.schemaname = 'public' AND i.tablename = pg_tables.tablename
                AND i.indexdef LIKE '%(id_sucursal_fuente)'
          )
    LOOP
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON public.%I (id_sucursal_fuente);',
            'idx_' || t.tablename || '_sucursal', t.tablename
        );
    END LOOP;
END $$;