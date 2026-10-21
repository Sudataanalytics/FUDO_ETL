INSERT INTO public.config_fudo_branches (
    id_branch, 
    fudo_branch_identifier, 
    branch_name, 
    secret_manager_apikey_name, 
    secret_manager_apisecret_name
) VALUES
('chale', 'MUAxNTk0MzM=', 'Chale', 'FUDO_CHALE_APIKEY', 'FUDO_CHALE_APISECRET'),
('quitobar', 'M0AyMjA0NDQ=', 'Quito Bar', 'FUDO_QUITO_BAR_APIKEY', 'FUDO_QUITO_BAR_APISECRET'),
('nebraska-sas', 'MjBAMTU1NjMy', 'Nebraska SAS', 'FUDO_NEBRASKA_SAS_APIKEY', 'FUDO_NEBRASKA_SAS_APISECRET'),
('puntocriollo-peron', 'MTVANDg2OTc=', 'Punto Criollo - Perón', 'FUDO_PUNTO_CRIOLLO_APIKEY', 'FUDO_PUNTO_CRIOLLO_APISECRET'),
('puntocriollo-guemes', 'MTZAMjc1MTM5', 'Punto Criollo - Güemes', 'FUDO_PUNTO_CRIOLLO_GUEMES_APIKEY', 'FUDO_PUNTO_CRIOLLO_GUEMES_APISECRET'),
('policastro', 'MTNAMzU2MjQ1', 'Policastro', 'FUDO_POLICASTRO_APIKEY', 'FUDO_POLICASTRO_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET 
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;
