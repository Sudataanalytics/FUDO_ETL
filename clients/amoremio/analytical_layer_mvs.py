# ==============================================================================
# MATERIALIZED VIEWS CONFIGURATIONS (Gold Layer - DER)
# Version v4.0 - Standard Numeric Synthetic Keys {id_branch_nro}-{id_fudo}
# ==============================================================================

materialized_views_configs = [
    # ------------------ 1. BRANCHES ------------------
    ('mv_branches', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_branches CASCADE;
        CREATE MATERIALIZED VIEW public.mv_branches AS
        SELECT 
            id_branch_nro AS id_branch_nro,
            id_branch AS id_branch_text,
            branch_name AS branch,
            is_active
        FROM public.config_fudo_branches
        WHERE is_active = TRUE;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_branches_nro ON public.mv_branches (id_branch_nro);
    """),

    # ------------------ 2. PRODUCT CATEGORIES (RUBROS) ------------------
    ('mv_product_categories', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_product_categories CASCADE;
        CREATE MATERIALIZED VIEW public.mv_product_categories AS
        SELECT DISTINCT ON (pc.id_fudo, pc.id_sucursal_fuente)
            (pc.payload_json ->> 'id')::FLOAT::INTEGER AS id_product_category_fudo,
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (pc.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_category_key,
            COALESCE(
                (pc.payload_json -> 'attributes' ->> 'name'), 
                'Category ' || (pc.payload_json ->> 'id')
            )::VARCHAR(255) AS product_category_name,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_product_categories pc
        JOIN public.config_fudo_branches cb ON pc.id_sucursal_fuente = cb.id_branch
        WHERE pc.payload_json ->> 'id' IS NOT NULL
        ORDER BY pc.id_fudo, pc.id_sucursal_fuente, pc.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_cat_key ON public.mv_product_categories (product_category_key);
    """),

    # ------------------ 3. PAYMENT METHODS ------------------
    ('mv_payment_methods', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_payment_methods CASCADE;
        CREATE MATERIALIZED VIEW public.mv_payment_methods AS
        SELECT DISTINCT ON (pm.id_fudo, pm.id_sucursal_fuente)
            (pm.payload_json ->> 'id')::FLOAT::INTEGER AS id_payment_method_fudo,
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (pm.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS payment_method_key,
            (pm.payload_json -> 'attributes' ->> 'name')::VARCHAR(255) AS payment_method,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_payment_methods pm
        JOIN public.config_fudo_branches cb ON pm.id_sucursal_fuente = cb.id_branch
        WHERE pm.payload_json ->> 'id' IS NOT NULL AND pm.payload_json -> 'attributes' ->> 'name' IS NOT NULL
        ORDER BY pm.id_fudo, pm.id_sucursal_fuente, pm.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pay_method_key ON public.mv_payment_methods (payment_method_key);
    """),

    # ------------------ 4. PRODUCTS ------------------
    ('mv_products', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_products CASCADE;
        CREATE MATERIALIZED VIEW public.mv_products AS
        SELECT DISTINCT ON (p.id_fudo, p.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (p.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_key,
            (p.payload_json -> 'attributes' ->> 'name')::VARCHAR(255) AS product_name,
            (p.payload_json -> 'attributes' ->> 'code')::VARCHAR(50) AS code,
            (p.payload_json -> 'attributes' ->> 'active')::BOOLEAN AS active,
            (p.payload_json -> 'attributes' ->> 'cost')::FLOAT AS cost,
            (p.payload_json -> 'attributes' ->> 'description')::TEXT AS description,
            (p.payload_json -> 'attributes' ->> 'price')::FLOAT AS price,
            (p.payload_json -> 'attributes' ->> 'stock')::FLOAT AS stock,
            -- FK formatted as {category_id}-{branch_nro}
            (p.payload_json -> 'relationships' -> 'productCategory' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_category_key_fk,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_products p
        JOIN public.config_fudo_branches cb ON p.id_sucursal_fuente = cb.id_branch
        WHERE p.payload_json ->> 'id' IS NOT NULL
        ORDER BY p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_products_key ON public.mv_products (product_key);
    """),

    # ------------------ 5. SALES ORDERS ------------------
    ('mv_sales_orders', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_sales_orders CASCADE;
        CREATE MATERIALIZED VIEW public.mv_sales_orders AS
        SELECT DISTINCT ON (s.id_fudo, s.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (s.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS order_key,
            (s.payload_json -> 'attributes' ->> 'saleType') AS sale_type,
            (s.payload_json -> 'attributes' ->> 'saleState') AS sale_state,
            (s.payload_json -> 'attributes' ->> 'total')::FLOAT AS amount_total,
            (s.payload_json -> 'attributes' ->> 'createdAt')::TIMESTAMP WITH TIME ZONE AS date_order,
            (s.payload_json -> 'attributes' ->> 'closedAt')::TIMESTAMP WITH TIME ZONE AS closed_at,
            (s.payload_json -> 'attributes' ->> 'people')::FLOAT::INTEGER AS people,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_sales s
        JOIN public.config_fudo_branches cb ON s.id_sucursal_fuente = cb.id_branch
        WHERE s.payload_json ->> 'id' IS NOT NULL
        ORDER BY s.id_fudo, s.id_sucursal_fuente, s.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_order_key ON public.mv_sales_orders (order_key);
    """),

    # ------------------ 6. PAYMENTS ------------------
    ('mv_payments', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_payments CASCADE;
        CREATE MATERIALIZED VIEW public.mv_payments AS
        SELECT DISTINCT ON (p.id_fudo, p.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (p.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS payment_key,
            (p.payload_json -> 'relationships' -> 'paymentMethod' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS payment_method_key,
            (p.payload_json -> 'attributes' ->> 'amount')::FLOAT AS amount,
            -- FKs
            (p.payload_json -> 'relationships' -> 'sale' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS order_key_fk,
            (p.payload_json -> 'relationships' -> 'expense' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS expense_key_fk,
            CASE WHEN (p.payload_json -> 'relationships' -> 'expense' -> 'data' ->> 'id') IS NOT NULL THEN 'EXPENSE'
                 WHEN (p.payload_json -> 'relationships' -> 'sale' -> 'data' ->> 'id') IS NOT NULL THEN 'SALE'
                 ELSE 'OTHER' END AS transaction_type,
            CASE WHEN (p.payload_json -> 'relationships' -> 'expense' -> 'data' ->> 'id') IS NOT NULL THEN -((p.payload_json -> 'attributes' ->> 'amount')::FLOAT)
                 ELSE (p.payload_json -> 'attributes' ->> 'amount')::FLOAT END AS signed_amount,
            (p.payload_json -> 'attributes' ->> 'createdAt')::TIMESTAMP WITH TIME ZONE AS payment_date,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_payments p
        JOIN public.config_fudo_branches cb ON p.id_sucursal_fuente = cb.id_branch
        WHERE p.payload_json ->> 'id' IS NOT NULL
        ORDER BY p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_payments_key ON public.mv_payments (payment_key);
    """),

# ------------------ 7. EXPENSES (Facts) ------------------
    ('mv_expenses', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_expenses CASCADE;
        CREATE MATERIALIZED VIEW public.mv_expenses AS
        SELECT DISTINCT ON (e.id_fudo, e.id_sucursal_fuente)
            -- 1. Clave Primaria Sintética (ID-SUCURSAL)
            (e.payload_json ->> 'id') || '-' || e.id_sucursal_fuente AS expense_key,
            
            -- 2. Claves de Relación
            (e.payload_json -> 'relationships' -> 'paymentMethod' -> 'data' ->> 'id') || '-' || e.id_sucursal_fuente AS expense_payment_method_key,
            (e.payload_json -> 'relationships' -> 'provider' -> 'data' ->> 'id') || '-' || e.id_sucursal_fuente AS provider_key,
            (e.payload_json -> 'relationships' -> 'expenseCategory' -> 'data' ->> 'id') || '-' || e.id_sucursal_fuente AS expense_category_key,
            
            -- 3. Atributos
            (e.payload_json -> 'attributes' ->> 'amount')::FLOAT AS amount,
            (e.payload_json -> 'attributes' ->> 'description')::TEXT AS description,
            (e.payload_json -> 'attributes' ->> 'date')::TIMESTAMP WITH TIME ZONE AS expense_date,
            
            -- 4. ID Numérico
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_expenses e
        JOIN public.config_fudo_branches cb ON e.id_sucursal_fuente = cb.id_branch
        WHERE (e.payload_json ->> 'id') IS NOT NULL
          AND e.id_sucursal_fuente IS NOT NULL
          
          -- 🛡️ FILTRO DE CALIDAD DE DATOS (DATA QUALITY)
          -- Evita fechas defectuosas (ej: año 0001) que rompen Power BI
          -- Solo permitimos gastos entre el año 2000 y el 2100
          AND (e.payload_json -> 'attributes' ->> 'date')::TIMESTAMP WITH TIME ZONE >= '2000-01-01'
          AND (e.payload_json -> 'attributes' ->> 'date')::TIMESTAMP WITH TIME ZONE <= '2100-01-01'
          
        ORDER BY e.id_fudo, e.id_sucursal_fuente, e.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_expenses_key ON public.mv_expenses (expense_key);
    """),

    # ------------------ 8. PROVIDERS ------------------
    ('mv_providers', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_providers CASCADE;
        CREATE MATERIALIZED VIEW public.mv_providers AS
        SELECT DISTINCT ON (p.id_fudo, p.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (p.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS provider_key,
            (p.payload_json -> 'attributes' ->> 'name')::VARCHAR(255) AS name,
            (p.payload_json -> 'attributes' ->> 'email')::TEXT AS email,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_providers p
        JOIN public.config_fudo_branches cb ON p.id_sucursal_fuente = cb.id_branch
        WHERE p.payload_json ->> 'id' IS NOT NULL
        ORDER BY p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_providers_key ON public.mv_providers (provider_key);
    """),

    # ------------------ 9. SALES ORDER LINES ------------------
    ('mv_sales_order_lines', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_sales_order_lines CASCADE;
        CREATE MATERIALIZED VIEW public.mv_sales_order_lines AS
        SELECT DISTINCT ON (i.id_fudo, i.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (i.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS order_line_key,
            (i.payload_json -> 'relationships' -> 'sale' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS order_key_fk,
            (i.payload_json -> 'relationships' -> 'product' -> 'data' ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_key_fk,
            (i.payload_json -> 'attributes' ->> 'price')::FLOAT AS price_unit, 
            COALESCE(((i.payload_json -> 'attributes' ->> 'quantity')::FLOAT::INTEGER), 0) AS qty,
            ((i.payload_json -> 'attributes' ->> 'price')::FLOAT * (i.payload_json -> 'attributes' ->> 'quantity')::FLOAT)::FLOAT AS amount_total_line,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_items i
        JOIN public.config_fudo_branches cb ON i.id_sucursal_fuente = cb.id_branch
        WHERE i.payload_json ->> 'id' IS NOT NULL 
          AND COALESCE(((i.payload_json -> 'attributes' ->> 'quantity')::FLOAT), 0) > 0
        ORDER BY i.id_fudo, i.id_sucursal_fuente, i.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_order_line_key ON public.mv_sales_order_lines (order_line_key);
    """),

    # ------------------ 10. EXPENSE CATEGORIES ------------------
    ('mv_expense_categories', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_expense_categories CASCADE;
        CREATE MATERIALIZED VIEW public.mv_expense_categories AS
        SELECT DISTINCT ON (ec.id_fudo, ec.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (ec.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS expense_category_key,
            (ec.payload_json -> 'attributes' ->> 'name') AS expense_category_name,
            (ec.payload_json -> 'attributes' ->> 'financialCategory') AS financial_category,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_expense_categories ec
        JOIN public.config_fudo_branches cb ON ec.id_sucursal_fuente = cb.id_branch
        WHERE (ec.payload_json ->> 'id') IS NOT NULL
        ORDER BY ec.id_fudo, ec.id_sucursal_fuente, ec.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_exp_cat_key ON public.mv_expense_categories (expense_category_key);
    """),

    # ------------------ 11. PRODUCT CATEGORIES DETAILS ------------------
    ('mv_product_categories_details', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_product_categories_details CASCADE;
        CREATE MATERIALIZED VIEW public.mv_product_categories_details AS
        SELECT DISTINCT ON (pc.id_fudo, pc.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (pc.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_category_key,
            (pc.payload_json -> 'attributes' ->> 'name') AS product_category_name,
            (pc.payload_json -> 'attributes' ->> 'position')::FLOAT::INTEGER AS "position",
            (pc.payload_json -> 'attributes' ->> 'preparationTime')::FLOAT::INTEGER AS preparation_time,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_product_categories pc
        JOIN public.config_fudo_branches cb ON pc.id_sucursal_fuente = cb.id_branch
        WHERE (pc.payload_json ->> 'id') IS NOT NULL
        ORDER BY pc.id_fudo, pc.id_sucursal_fuente, pc.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_prod_cat_det_key ON public.mv_product_categories_details (product_category_key);
    """),

    # ------------------ 12. PRODUCT PRICES BY BRANCH ------------------
    ('mv_product_prices_by_branch', """
        DROP MATERIALIZED VIEW IF EXISTS public.mv_product_prices_by_branch CASCADE;
        CREATE MATERIALIZED VIEW public.mv_product_prices_by_branch AS
        SELECT DISTINCT ON (p.id_fudo, p.id_sucursal_fuente)
            -- FORMATO CORREGIDO: {id_fudo}-{branch_nro}
            (p.payload_json ->> 'id') || '-' || cb.id_branch_nro::TEXT AS product_branch_key,
            (p.payload_json -> 'attributes' ->> 'name')::VARCHAR(255) AS product_name,
            (p.payload_json -> 'attributes' ->> 'price')::FLOAT AS price,
            (p.payload_json -> 'attributes' ->> 'stock')::FLOAT AS stock,
            cb.id_branch_nro AS id_branch_nro
        FROM public.fudo_raw_products p
        JOIN public.config_fudo_branches cb ON p.id_sucursal_fuente = cb.id_branch
        WHERE p.payload_json ->> 'id' IS NOT NULL
        ORDER BY p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc DESC;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_prod_price_branch_key ON public.mv_product_prices_by_branch (product_branch_key);
    """),
]


# ==============================================================================
# RAW VIEW CONFIGURATIONS (Silver Layer - Standardized)
# ==============================================================================

raw_views_configs = [
    ('fudo_view_raw_customers', """
        DROP VIEW IF EXISTS public.fudo_view_raw_customers CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_customers AS
        SELECT
            c.id_fudo, c.id_sucursal_fuente, c.fecha_extraccion_utc, c.payload_checksum,
            (c.payload_json ->> 'id') AS customer_id, (c.payload_json -> 'attributes' ->> 'active')::BOOLEAN AS active,
            (c.payload_json -> 'attributes' ->> 'address') AS address,
            (c.payload_json -> 'attributes' ->> 'createdAt')::TIMESTAMP WITH TIME ZONE AS created_at,
            (c.payload_json -> 'attributes' ->> 'name') AS customer_name,
            c.payload_json AS original_payload
        FROM public.fudo_raw_customers c;
    """),
    ('fudo_view_raw_discounts', """
        DROP VIEW IF EXISTS public.fudo_view_raw_discounts CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_discounts AS
        SELECT
            d.id_fudo, d.id_sucursal_fuente, d.fecha_extraccion_utc, d.payload_checksum,
            (d.payload_json ->> 'id') AS discount_id, (d.payload_json -> 'attributes' ->> 'amount')::FLOAT AS amount,
            (d.payload_json -> 'relationships' -> 'sale' -> 'data' ->> 'id') AS sale_id,
            d.payload_json AS original_payload
        FROM public.fudo_raw_discounts d;
    """),
    ('fudo_view_raw_expenses', """
        DROP VIEW IF EXISTS public.fudo_view_raw_expenses CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_expenses AS
        SELECT
            e.id_fudo, e.id_sucursal_fuente, e.fecha_extraccion_utc, e.payload_checksum,
            (e.payload_json ->> 'id') AS expense_id, (e.payload_json -> 'attributes' ->> 'amount')::FLOAT AS amount,
            (e.payload_json -> 'attributes' ->> 'description') AS description,
            (e.payload_json -> 'attributes' ->> 'date')::TIMESTAMP WITH TIME ZONE AS expense_date,
            e.payload_json AS original_payload
        FROM public.fudo_raw_expenses e;
    """),
    ('fudo_view_raw_expense_categories', """
        DROP VIEW IF EXISTS public.fudo_view_raw_expense_categories CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_expense_categories AS
        SELECT
            ec.id_fudo, ec.id_sucursal_fuente, ec.fecha_extraccion_utc, ec.payload_checksum,
            (ec.payload_json ->> 'id') AS category_id, (ec.payload_json -> 'attributes' ->> 'name') AS category_name,
            ec.payload_json AS original_payload
        FROM public.fudo_raw_expense_categories ec;
    """),
    ('fudo_view_raw_ingredients', """
        DROP VIEW IF EXISTS public.fudo_view_raw_ingredients CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_ingredients AS
        SELECT
            i.id_fudo, i.id_sucursal_fuente, i.fecha_extraccion_utc, i.payload_checksum,
            (i.payload_json ->> 'id') AS ingredient_id, (i.payload_json -> 'attributes' ->> 'name') AS ingredient_name,
            (i.payload_json -> 'attributes' ->> 'cost')::FLOAT AS cost,
            i.payload_json AS original_payload
        FROM public.fudo_raw_ingredients i;
    """),
    ('fudo_view_raw_items', """
        DROP VIEW IF EXISTS public.fudo_view_raw_items CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_items AS
        SELECT
            i.id_fudo, i.id_sucursal_fuente, i.fecha_extraccion_utc, i.payload_checksum,
            (i.payload_json ->> 'id') AS item_id, (i.payload_json -> 'attributes' ->> 'price')::FLOAT AS price,
            (i.payload_json -> 'attributes' ->> 'quantity')::FLOAT AS quantity,
            (i.payload_json -> 'relationships' -> 'product' -> 'data' ->> 'id') AS product_id,
            i.payload_json AS original_payload
        FROM public.fudo_raw_items i;
    """),
    ('fudo_view_raw_kitchens', """
        DROP VIEW IF EXISTS public.fudo_view_raw_kitchens CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_kitchens AS
        SELECT
            k.id_fudo, k.id_sucursal_fuente, k.fecha_extraccion_utc, k.payload_checksum,
            (k.payload_json ->> 'id') AS kitchen_id, (k.payload_json -> 'attributes' ->> 'name') AS kitchen_name,
            k.payload_json AS original_payload
        FROM public.fudo_raw_kitchens k;
    """),
    ('fudo_view_raw_payments', """
        DROP VIEW IF EXISTS public.fudo_view_raw_payments CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_payments AS
        SELECT
            p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc, p.payload_checksum,
            (p.payload_json ->> 'id') AS payment_id, (p.payload_json -> 'attributes' ->> 'amount')::FLOAT AS amount,
            (p.payload_json -> 'relationships' -> 'sale' -> 'data' ->> 'id') AS sale_id,
            p.payload_json AS original_payload
        FROM public.fudo_raw_payments p;
    """),
    ('fudo_view_raw_payment_methods', """
        DROP VIEW IF EXISTS public.fudo_view_raw_payment_methods CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_payment_methods AS
        SELECT
            pm.id_fudo, pm.id_sucursal_fuente, pm.fecha_extraccion_utc, pm.payload_checksum,
            (pm.payload_json ->> 'id') AS method_id, (pm.payload_json -> 'attributes' ->> 'name') AS method_name,
            pm.payload_json AS original_payload
        FROM public.fudo_raw_payment_methods pm;
    """),
    ('fudo_view_raw_product_categories', """
        DROP VIEW IF EXISTS public.fudo_view_raw_product_categories CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_product_categories AS
        SELECT
            pc.id_fudo, pc.id_sucursal_fuente, pc.fecha_extraccion_utc, pc.payload_checksum,
            (pc.payload_json ->> 'id') AS category_id, (pc.payload_json -> 'attributes' ->> 'name') AS category_name,
            pc.payload_json AS original_payload
        FROM public.fudo_raw_product_categories pc;
    """),
    ('fudo_view_raw_product_modifiers', """
        DROP VIEW IF EXISTS public.fudo_view_raw_product_modifiers CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_product_modifiers AS
        SELECT
            pm.id_fudo, pm.id_sucursal_fuente, pm.fecha_extraccion_utc, pm.payload_checksum,
            (pm.payload_json ->> 'id') AS modifier_id, (pm.payload_json -> 'attributes' ->> 'price')::FLOAT AS price,
            pm.payload_json AS original_payload
        FROM public.fudo_raw_product_modifiers pm;
    """),
    ('fudo_view_raw_products', """
        DROP VIEW IF EXISTS public.fudo_view_raw_products CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_products AS
        SELECT
            p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc, p.payload_checksum,
            (p.payload_json ->> 'id') AS product_id, (p.payload_json -> 'attributes' ->> 'name') AS product_name,
            (p.payload_json -> 'attributes' ->> 'price')::FLOAT AS price,
            (p.payload_json -> 'attributes' ->> 'position')::FLOAT::INTEGER AS "position",
            (p.payload_json -> 'attributes' ->> 'preparationTime')::FLOAT::INTEGER AS preparation_time,
            p.payload_json AS original_payload
        FROM public.fudo_raw_products p;
    """),
    ('fudo_view_raw_roles', """
        DROP VIEW IF EXISTS public.fudo_view_raw_roles CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_roles AS
        SELECT
            r.id_fudo, r.id_sucursal_fuente, r.fecha_extraccion_utc, r.payload_checksum,
            (r.payload_json ->> 'id') AS role_id, (r.payload_json -> 'attributes' ->> 'name') AS role_name,
            r.payload_json AS original_payload
        FROM public.fudo_raw_roles r;
    """),
    ('fudo_view_raw_rooms', """
        DROP VIEW IF EXISTS public.fudo_view_raw_rooms CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_rooms AS
        SELECT
            r.id_fudo, r.id_sucursal_fuente, r.fecha_extraccion_utc, r.payload_checksum,
            (r.payload_json ->> 'id') AS room_id, (r.payload_json -> 'attributes' ->> 'name') AS room_name,
            r.payload_json AS original_payload
        FROM public.fudo_raw_rooms r;
    """),
    ('fudo_view_raw_tables', """
        DROP VIEW IF EXISTS public.fudo_view_raw_tables CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_tables AS
        SELECT
            t.id_fudo, t.id_sucursal_fuente, t.fecha_extraccion_utc, t.payload_checksum,
            (t.payload_json ->> 'id') AS table_id, (t.payload_json -> 'attributes' ->> 'number')::FLOAT::INTEGER AS table_number,
            (t.payload_json -> 'attributes' ->> 'column')::FLOAT::INTEGER AS "column",
            (t.payload_json -> 'attributes' ->> 'row')::FLOAT::INTEGER AS "row",
            t.payload_json AS original_payload
        FROM public.fudo_raw_tables t;
    """),
    ('fudo_view_raw_users', """
        DROP VIEW IF EXISTS public.fudo_view_raw_users CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_users AS
        SELECT
            u.id_fudo, u.id_sucursal_fuente, u.fecha_extraccion_utc, u.payload_checksum,
            (u.payload_json ->> 'id') AS user_id, (u.payload_json -> 'attributes' ->> 'name') AS user_name,
            u.payload_json AS original_payload
        FROM public.fudo_raw_users u;
    """),
    ('fudo_view_raw_sales', """
        DROP VIEW IF EXISTS public.fudo_view_raw_sales CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_sales AS
        SELECT
            s.id_fudo, s.id_sucursal_fuente, s.fecha_extraccion_utc, s.payload_checksum,
            (s.payload_json ->> 'id') AS sale_id, (s.payload_json -> 'attributes' ->> 'total')::FLOAT AS total,
            (s.payload_json -> 'attributes' ->> 'createdAt')::TIMESTAMP WITH TIME ZONE AS created_at,
            (s.payload_json -> 'attributes' ->> 'people')::FLOAT::INTEGER AS people,
            s.payload_json AS original_payload
        FROM public.fudo_raw_sales s;
    """),
    ('fudo_view_raw_providers', """
        DROP VIEW IF EXISTS public.fudo_view_raw_providers CASCADE;
        CREATE OR REPLACE VIEW public.fudo_view_raw_providers AS
        SELECT
            p.id_fudo, p.id_sucursal_fuente, p.fecha_extraccion_utc, p.payload_checksum,
            (p.payload_json ->> 'id') AS provider_id, (p.payload_json -> 'attributes' ->> 'name') AS name,
            (p.payload_json -> 'attributes' ->> 'email') AS email,
            p.payload_json AS original_payload
        FROM public.fudo_raw_providers p;
    """),
]