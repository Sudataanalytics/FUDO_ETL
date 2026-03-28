-- ==============================================================================
-- TABLAS LÓGICAS DEL DER (Capa Analítica)
-- Versión Genérica Multicliente v2.0
-- ==============================================================================

-- 1. Sucursales
CREATE TABLE IF NOT EXISTS public.Sucursales (
  id_sucursal VARCHAR(255) PRIMARY KEY,
  sucursal VARCHAR(255) NOT NULL
);

-- 2. Rubros (Categorías de Producto Básicas)
CREATE TABLE IF NOT EXISTS public.Rubros (
  id_rubro_fudo TEXT,
  id_sucursal VARCHAR(255),
  rubro_key TEXT PRIMARY KEY, 
  rubro_name VARCHAR(255) NOT NULL
);

-- 3. Medio de Pago
CREATE TABLE IF NOT EXISTS public.Medio_pago (
  id_payment_fudo TEXT,
  id_sucursal VARCHAR(255),
  payment_method_key TEXT PRIMARY KEY, 
  payment_method VARCHAR(255) NOT NULL
);

-- 4. Productos (Dimensión Principal)
CREATE TABLE IF NOT EXISTS public.Productos (
  id_product_fudo TEXT,
  id_sucursal VARCHAR(255),
  product_key TEXT PRIMARY KEY,
  product_name VARCHAR(255) NOT NULL,
  code VARCHAR(50),      
  active BOOLEAN,        
  cost FLOAT,            
  description TEXT,      
  price FLOAT,           
  stock FLOAT,           
  id_rubro_fudo TEXT,
  rubro_key_fk TEXT      
);

-- 5. Órdenes de Venta (Cabecera)
CREATE TABLE IF NOT EXISTS public.Sales_order (
  id_order TEXT,
  id_sucursal VARCHAR(255),
  order_key TEXT PRIMARY KEY, 
  amount_tax FLOAT,
  amount_total FLOAT NOT NULL,
  date_order TIMESTAMP WITH TIME ZONE NOT NULL,
  sale_type VARCHAR(50),
  sale_state VARCHAR(50),     
  table_id TEXT,
  waiter_id TEXT,
  customer_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE, 
  closed_at TIMESTAMP WITH TIME ZONE,  
  people INTEGER                       
);

-- 6. Pagos (Transacciones)
CREATE TABLE IF NOT EXISTS public.Pagos (
  id TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  payment_key TEXT PRIMARY KEY,      
  payment_method_key TEXT NOT NULL,  
  pos_order_id TEXT,
  id_payment TEXT,
  amount FLOAT NOT NULL,
  payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
  transaction_type VARCHAR(50),      
  signed_amount FLOAT,               
  expense_id TEXT,
  order_key_fk TEXT                  
);

-- 7. Líneas de Orden de Venta (Detalle)
CREATE TABLE IF NOT EXISTS public.Sales_order_line (
  id_order_line TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  order_line_key TEXT PRIMARY KEY, 
  id_order_fudo TEXT NOT NULL,
  order_key_fk TEXT NOT NULL,      
  id_product_fudo TEXT NOT NULL,
  product_key_fk TEXT NOT NULL,    
  date_order_time TIMESTAMP WITH TIME ZONE NOT NULL,
  date_order DATE NOT NULL,
  qty_from_api FLOAT,
  price_from_api FLOAT,
  price_unit FLOAT NOT NULL,
  qty INTEGER NOT NULL,
  amount_total FLOAT NOT NULL
);

-- 8. Categorías de Gastos
CREATE TABLE IF NOT EXISTS public.Expense_categories (
  id_expense_category TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  expense_category_key TEXT PRIMARY KEY, 
  expense_category_name VARCHAR(255) NOT NULL,
  financial_category VARCHAR(255),
  active BOOLEAN,
  parent_category_id TEXT
);

-- 9. Gastos (Cabecera)
CREATE TABLE IF NOT EXISTS public.Expenses (
  id_expense_fudo TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  expense_key TEXT PRIMARY KEY,      
  expense_payment_method_key TEXT,   
  amount FLOAT NOT NULL,
  description TEXT,
  expense_date TIMESTAMP WITH TIME ZONE NOT NULL,
  status VARCHAR(50),
  due_date TIMESTAMP WITH TIME ZONE,
  canceled BOOLEAN,
  created_at TIMESTAMP WITH TIME ZONE,
  payment_date TIMESTAMP WITH TIME ZONE,
  receipt_number TEXT,
  use_in_cash_count BOOLEAN,
  user_id TEXT,
  provider_id TEXT,
  receipt_type_id TEXT,
  cash_register_id TEXT,
  payment_method_id TEXT,
  expense_category_id TEXT,
  expense_category_key TEXT NOT NULL
);

-- 10. Categorías de Producto (Detallada)
CREATE TABLE IF NOT EXISTS public.Product_categories (
  id_product_category TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  product_category_key TEXT PRIMARY KEY, 
  product_category_name VARCHAR(255) NOT NULL,
  "position" INTEGER,
  preparation_time INTEGER,
  enable_online_menu BOOLEAN,
  kitchen_id TEXT,
  parent_category_id TEXT
);

-- 11. Precios de Productos por Sucursal
CREATE TABLE IF NOT EXISTS public.Product_prices_by_branch (
  id_product_fudo TEXT NOT NULL,
  id_sucursal VARCHAR(255) NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  price FLOAT,
  stock FLOAT,
  is_active_in_branch BOOLEAN,
  product_branch_key TEXT PRIMARY KEY
);

-- 12. Proveedores (Providers)
CREATE TABLE IF NOT EXISTS public.Providers (
  id_provider TEXT,
  id_sucursal VARCHAR(255) NOT NULL,
  provider_key TEXT PRIMARY KEY, 
  name VARCHAR(255) NOT NULL,
  email TEXT,
  address TEXT,
  phone TEXT,
  comment TEXT,
  active BOOLEAN,
  internal BOOLEAN,
  provider_house_account_balance FLOAT,
  fiscal_number TEXT
);