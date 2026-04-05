-- 1. Sucursales
CREATE TABLE IF NOT EXISTS public.Sucursales (
  id_sucursal_nro INTEGER PRIMARY KEY,
  id_sucursal_texto VARCHAR(255) NOT NULL,
  sucursal VARCHAR(255) NOT NULL,
  is_active BOOLEAN
);

-- 2. Rubros
CREATE TABLE IF NOT EXISTS public.Rubros (
  id_rubro_fudo INTEGER,
  id_sucursal INTEGER,
  rubro_key TEXT PRIMARY KEY,
  rubro_name VARCHAR(255) NOT NULL
);

-- 3. Medio de Pago
CREATE TABLE IF NOT EXISTS public.Medio_pago (
  id_payment_fudo INTEGER,
  id_sucursal INTEGER,
  payment_method_key TEXT PRIMARY KEY,
  payment_method VARCHAR(255) NOT NULL
);

-- 4. Productos
CREATE TABLE IF NOT EXISTS public.Productos (
  product_key TEXT PRIMARY KEY,
  product_name VARCHAR(255) NOT NULL,
  code VARCHAR(50),
  active BOOLEAN,
  cost FLOAT,
  description TEXT,
  price FLOAT,
  stock FLOAT,
  rubro_key_fk TEXT,
  id_sucursal INTEGER
);

-- 5. Órdenes de Venta
CREATE TABLE IF NOT EXISTS public.Sales_order (
  order_key TEXT PRIMARY KEY,
  sale_type VARCHAR(50),
  sale_state VARCHAR(50),
  amount_total FLOAT NOT NULL,
  date_order TIMESTAMP WITH TIME ZONE NOT NULL,
  closed_at TIMESTAMP WITH TIME ZONE,
  people INTEGER,
  id_sucursal INTEGER
);

-- 6. Pagos
CREATE TABLE IF NOT EXISTS public.Pagos (
  payment_key TEXT PRIMARY KEY,
  payment_method_key TEXT NOT NULL,
  amount FLOAT NOT NULL,
  order_key_fk TEXT,
  expense_key_fk TEXT,
  transaction_type VARCHAR(50),
  payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
  id_sucursal INTEGER
);

-- 7. Líneas de Venta
CREATE TABLE IF NOT EXISTS public.Sales_order_line (
  order_line_key TEXT PRIMARY KEY,
  order_key_fk TEXT NOT NULL,
  product_key_fk TEXT NOT NULL,
  price_unit FLOAT NOT NULL,
  qty INTEGER NOT NULL,
  amount_total_linea FLOAT NOT NULL,
  id_sucursal INTEGER
);

-- 8. Categorías de Gastos
CREATE TABLE IF NOT EXISTS public.Expense_categories (
  id_expense_category INTEGER,
  id_sucursal INTEGER,
  expense_category_key TEXT PRIMARY KEY,
  expense_category_name VARCHAR(255) NOT NULL,
  financial_category VARCHAR(255),
  active BOOLEAN,
  parent_category_id TEXT
);

-- 9. Gastos
CREATE TABLE IF NOT EXISTS public.Expenses (
  expense_key TEXT PRIMARY KEY,
  expense_payment_method_key TEXT,
  provider_key TEXT,
  expense_category_key TEXT NOT NULL,
  amount FLOAT NOT NULL,
  description TEXT,
  expense_date TIMESTAMP WITH TIME ZONE NOT NULL,
  id_sucursal INTEGER
);

-- 10. Product Categories (Detallada)
CREATE TABLE IF NOT EXISTS public.Product_categories (
  id_product_category INTEGER,
  product_category_name VARCHAR(255) NOT NULL,
  "position" INTEGER,
  preparation_time INTEGER,
  enable_online_menu BOOLEAN,
  kitchen_id TEXT,
  parent_category_id TEXT,
  id_sucursal INTEGER,
  product_category_key TEXT PRIMARY KEY
);

-- 11. Product Prices by Branch
CREATE TABLE IF NOT EXISTS public.Product_prices_by_branch (
  id_product_fudo TEXT NOT NULL,
  id_sucursal INTEGER NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  price FLOAT,
  stock FLOAT,
  is_active_in_branch BOOLEAN,
  product_branch_key TEXT PRIMARY KEY
);

-- 12. Providers
CREATE TABLE IF NOT EXISTS public.Providers (
  provider_key TEXT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email TEXT,
  id_sucursal INTEGER
);