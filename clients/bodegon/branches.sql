INSERT INTO public.config_fudo_branches (
    id_branch, 
    fudo_branch_identifier, 
    branch_name, 
    secret_manager_apikey_name, 
    secret_manager_apisecret_name
) VALUES
    ('elbodegoncba', 'NTdAMTA2Mzkw', 'El Bod - Cba', 'FUDO_ELBODEGONCORDOBA_APIKEY', 'FUDO_ELBODEGONCORDOBA_APISECRET'),
    ('elbodegonplacido', 'OTFAODEwMDK=', 'El Bod - Plácido', 'FUDO_ELBODEGONPLACIDO_APIKEY', 'FUDO_ELBODEGONPLACIDO_APISECRET'),
    ('rost25', 'MjZAMjl5OTUx', 'Rost 25', 'FUDO_ROST25_APIKEY', 'FUDO_ROST25_APISECRET'),
    ('masssamor', 'MTZAMTkyMjAw', 'Masssamor', 'FUDO_MASSSAMOR_APIKEY', 'FUDO_MASSSAMOR_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;