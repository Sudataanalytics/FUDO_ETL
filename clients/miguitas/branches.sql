-- clients/miguitas/branches.sql
-- DELETE FROM public.config_fudo_branches WHERE id_sucursal LIKE 'miguitas-%';

INSERT INTO public.config_fudo_branches (id_sucursal, fudo_branch_identifier, sucursal_name, secret_manager_apikey_name, secret_manager_apisecret_name)
VALUES
    ('miguitas-sanmartin', 'MzBAODI1OTQ=', 'Miguitas San Martin', 'FUDO_MIGUITAS_SANMARTIN_APIKEY', 'FUDO_MIGUITAS_SANMARTIN_APISECRET'),
    ('miguitas-alberdi', 'MzZAMjIwNzAx', 'Miguitas Alberdi', 'FUDO_MIGUITAS_ALBERDI_APIKEY', 'FUDO_MIGUITAS_ALBERDI_APISECRET'),
    ('miguitas-italia', 'MjBAMzIwNDM5', 'Miguitas Italia', 'FUDO_MIGUITAS_ITALIA_APIKEY', 'FUDO_MIGUITAS_ITALIA_APISECRET')
ON CONFLICT (id_sucursal) DO UPDATE SET
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier, sucursal_name = EXCLUDED.sucursal_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name, secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;