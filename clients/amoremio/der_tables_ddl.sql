-- ==============================================================================
-- LOGICAL TABLES FOR THE DER (Analytic Layer - Gold)
-- Generic Multi-client Version v3.0 (English Standard)
-- ==============================================================================

-- 1. Branches (Formerly Sucursales)
CREATE TABLE IF NOT EXISTS public.Branches (
  id_branch_nro INTEGER PRIMARY KEY,
  id_branch_text VARCHAR(255) NOT NULL, -- Logical ID (e.g., 'miguitas-italia')
  branch VARCHAR(255) NOT NULL,
  is_active BOOLEAN
);

-- 2. Product_categories (Formerly Rubros)
CREATE TABLE IF NOT EXISTS public.Product_categories (
  id_product_category_fudo TEXT,
  id_branch_nro INTEGER,
  product_category_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  product_category_name VARCHAR(255) NOT NULL
);

-- 3. Payment_methods (Formerly Medio_pago)
CREATE TABLE IF NOT EXISTS public.Payment_methods (
  id_payment_method_fudo TEXT,
  id_branch_nro INTEGER,
  payment_method_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  payment_method VARCHAR(255) NOT NULL
);

-- 4. Products (Formerly Productos)
CREATE TABLE IF NOT EXISTS public.Products (
  product_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  product_name VARCHAR(255) NOT NULL,
  code VARCHAR(50),
  active BOOLEAN,
  cost FLOAT,
  description TEXT,
  price FLOAT,
  stock FLOAT,
  product_category_key_fk TEXT, -- Link to Product_categories.product_category_key
  id_branch_nro INTEGER
);

-- 5. Sales_orders (Formerly Órdenes de Venta)
CREATE TABLE IF NOT EXISTS public.Sales_orders (
  order_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  sale_type VARCHAR(50),
  sale_state VARCHAR(50),
  amount_total FLOAT NOT NULL,
  date_order TIMESTAMP WITH TIME ZONE NOT NULL,
  closed_at TIMESTAMP WITH TIME ZONE,
  people INTEGER,
  id_branch_nro INTEGER
);

-- 6. Payments (Formerly Pagos)
CREATE TABLE IF NOT EXISTS public.Payments (
  payment_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  payment_method_key TEXT NOT NULL, -- Link to Payment_methods
  amount FLOAT NOT NULL,
  order_key_fk TEXT, -- Link to Sales_orders
  expense_key_fk TEXT, -- Link to Expenses
  transaction_type VARCHAR(50), -- SALE / EXPENSE
  payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
  id_branch_nro INTEGER
);

-- 7. Sales_order_lines (Formerly Líneas de Venta)
CREATE TABLE IF NOT EXISTS public.Sales_order_lines (
  order_line_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  order_key_fk TEXT NOT NULL,
  product_key_fk TEXT NOT NULL,
  price_unit FLOAT NOT NULL,
  qty INTEGER NOT NULL,
  amount_total_line FLOAT NOT NULL,
  id_branch_nro INTEGER
);

-- 8. Expense_categories
CREATE TABLE IF NOT EXISTS public.Expense_categories (
  id_expense_category_fudo TEXT,
  id_branch_nro INTEGER,
  expense_category_key TEXT PRIMARY KEY, -- Synthetic Key
  expense_category_name VARCHAR(255) NOT NULL,
  financial_category VARCHAR(255),
  active BOOLEAN,
  parent_category_id TEXT
);

-- 9. Expenses (Formerly Gastos)
CREATE TABLE IF NOT EXISTS public.Expenses (
  expense_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  expense_payment_method_key TEXT,
  provider_key TEXT,
  expense_category_key TEXT NOT NULL,
  amount FLOAT NOT NULL,
  description TEXT,
  expense_date TIMESTAMP WITH TIME ZONE NOT NULL,
  id_branch_nro INTEGER
);

-- 10. Product_categories_details (Formerly Detailed categories)
CREATE TABLE IF NOT EXISTS public.Product_categories_details (
  id_product_category_fudo TEXT,
  product_category_name VARCHAR(255) NOT NULL,
  "position" INTEGER,
  preparation_time INTEGER,
  enable_online_menu BOOLEAN,
  kitchen_id TEXT,
  parent_category_id TEXT,
  id_branch_nro INTEGER,
  product_category_key TEXT PRIMARY KEY
);

-- 11. Product_prices_by_branch
CREATE TABLE IF NOT EXISTS public.Product_prices_by_branch (
  id_product_fudo TEXT NOT NULL,
  id_branch_nro INTEGER NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  price FLOAT,
  stock FLOAT,
  is_active_in_branch BOOLEAN,
  product_branch_key TEXT PRIMARY KEY
);

-- 12. Providers
CREATE TABLE IF NOT EXISTS public.Providers (
  provider_key TEXT PRIMARY KEY, -- Synthetic Key: ID-BRANCH
  name VARCHAR(255) NOT NULL,
  email TEXT,
  id_branch_nro INTEGER
);