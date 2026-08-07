INSERT INTO public.config_fudo_branches (
    id_branch, 
    fudo_branch_identifier, 
    branch_name, 
    secret_manager_apikey_name, 
    secret_manager_apisecret_name
) VALUES
('meso_unidad', 'OUAzMzk5MjI=', 'Meso - Unidad', 'FUDO_MESO_UNIDAD_APIKEY', 'FUDO_MESO_UNIDAD_APISECRET'),
('meso_tallerpan', 'MzRAMTA1ODQ2', 'Meso - Taller Pan', 'FUDO_MESO_TALLERPAN_APIKEY', 'FUDO_MESO_TALLERPAN_APISECRET'),
('meso_catamarca', 'MThAMjk2MjA2', 'Meso - Catamarca', 'FUDO_MESO_CATAMARCA_APIKEY', 'FUDO_MESO_CATAMARCA_APISECRET'),
('meso_tallerpizzas', 'MjFAMjQ3NjU3', 'Meso - Taller Pizzas', 'FUDO_MESO_TALLERPIZZAS_APIKEY', 'FUDO_MESO_TALLERPIZZAS_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET 
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;