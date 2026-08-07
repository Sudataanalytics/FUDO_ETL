INSERT INTO public.config_fudo_branches (
    id_branch,
    fudo_branch_identifier,
    branch_name,
    secret_manager_apikey_name,
    secret_manager_apisecret_name
)
VALUES
('sanjuan','NzFAODA1NTE=','San Juan','FUDO_LODEPEPE_SANJUAN_APIKEY','FUDO_LODEPEPE_SANJUAN_APISECRET'),
('rioja','NTZAMTA1NTE5','Rioja','FUDO_LODEPEPE_RIOJA_APIKEY','FUDO_LODEPEPE_RIOJA_APISECRET'),
('uniplaza','MTlAMzE0MTE0','Uniplaza','FUDO_LODEPEPE_UNIPLAZA_APIKEY','FUDO_LODEPEPE_UNIPLAZA_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;