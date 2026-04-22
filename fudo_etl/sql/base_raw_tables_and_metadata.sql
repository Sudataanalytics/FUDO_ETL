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