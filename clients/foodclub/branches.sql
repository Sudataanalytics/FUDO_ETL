INSERT INTO public.config_fudo_branches (id_branch, fudo_branch_identifier, branch_name, secret_manager_apikey_name, secret_manager_apisecret_name)
VALUES 
('foodclub', 'NEA4Nzc3NQ==', 'Food Club', 'FUDO_FOODCLUB_APIKEY', 'FUDO_FOODCLUB_APISECRET'),
('pizzaclubma', 'NjkzMzlANjAyOA==', 'Pizza Club MA', 'FUDO_PIZZACLUBMA_APIKEY', 'FUDO_PIZZACLUBMA_APISECRET'),
('pizzaclubco', 'NDI5NjZAMjQyMDc=', 'Pizza Club CO', 'FUDO_PIZZACLUBCO_APIKEY', 'FUDO_PIZZACLUBCO_APISECRET'),
('pizzaclubpl', 'NUAzNDg0Nw==', 'Pizza Club PL', 'FUDO_PIZZACLUBPL_APIKEY', 'FUDO_PIZZACLUBPL_APISECRET'),
('burgerclubar', 'MTFANzQzNzM=', 'Burger Club AR', 'FUDO_BURGERCLUBAR_APIKEY', 'FUDO_BURGERCLUBAR_APISECRET'),
('milaclub', 'MTFAMjUyNzM4', 'Mila Club', 'FUDO_MILACLUB_APIKEY', 'FUDO_MILACLUB_APISECRET')
ON CONFLICT (id_branch) DO UPDATE SET 
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier,
    branch_name = EXCLUDED.branch_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name,
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;