-- clients/miguitas/branches.sql

-- No borramos, solo actualizamos (Upsert)
INSERT INTO public.config_fudo_branches (
    id_branch, 
    fudo_branch_identifier, 
    branch_name, 
    secret_manager_apikey_name, 
    secret_manager_apisecret_name
)
VALUES
    ('miguitas-sanmartin', 'MzBAODI1OTQ=', 'San Martin', 'FUDO_MIGUITAS_SANMARTIN_APIKEY', 'FUDO_MIGUITAS_SANMARTIN_APISECRET'),
    ('miguitas-alberdi', 'MzZAMjIwNzAx', 'Alberdi', 'FUDO_MIGUITAS_ALBERDI_APIKEY', 'FUDO_MIGUITAS_ALBERDI_APISECRET'),
    ('miguitas-italia', 'MjBAMzIwNDM5', 'Italia', 'FUDO_MIGUITAS_ITALIA_APIKEY', 'FUDO_MIGUITAS_ITALIA_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;