-- clients/amoremio/branches.sql

-- Limpiamos sucursales previas para este cliente
DELETE FROM public.config_fudo_branches;

INSERT INTO public.config_fudo_branches (id_sucursal, fudo_branch_identifier, sucursal_name, secret_manager_apikey_name, secret_manager_apisecret_name)
VALUES
    ('amoremio-guemes', 'MTRANzAwNTk=', 'Amore Mio Guemes', 'FUDO_AMOREMIO_GUEMES_APIKEY', 'FUDO_AMOREMIO_GUEMES_APISECRET'),
    ('amoremio-am2', 'N0AxNzU5NjE=', 'Amore Mio Roque Saenz Peña', 'FUDO_AMOREMIO_AM2_APIKEY', 'FUDO_AMOREMIO_AM2_APISECRET'),
    ('amoremio-peron', 'MTFANzc3NzE=', 'Amore Mio Peron', 'FUDO_AMOREMIO_PERON_APIKEY', 'FUDO_AMOREMIO_PERON_APISECRET'),
    ('amoremio-posadas', 'N0AxNjg3MTI=', 'Amore Mio Posadas 770', 'FUDO_AMOREMIO_POSADAS_APIKEY', 'FUDO_AMOREMIO_POSADAS_APISECRET'),
    ('amoremio-am6', 'MTBAMTI2NjQ2', 'Amore Mio Mitre 166', 'FUDO_AMOREMIO_AM6_APIKEY', 'FUDO_AMOREMIO_AM6_APISECRET'),
    ('amoremio-am7', 'NEAxODQwNjU=', 'Amore Mio H. Yrigoyen 199', 'FUDO_AMOREMIO_AM7_APIKEY', 'FUDO_AMOREMIO_AM7_APISECRET'),
    ('amoremio-am8', 'MUAyMTIxMTQ=', 'Amore Mio Av. Wilde 170', 'FUDO_AMOREMIO_AM8_APIKEY', 'FUDO_AMOREMIO_AM8_APISECRET'),
    ('amoremio-vedia', 'MUAyODkyMDM=', 'Amore Mio Vedia', 'FUDO_AMOREMIO_VEDIA_APIKEY', 'FUDO_AMOREMIO_VEDIA_APISECRET')
ON CONFLICT (id_sucursal) DO UPDATE SET
    fudo_branch_identifier = EXCLUDED.fudo_branch_identifier, 
    sucursal_name = EXCLUDED.sucursal_name,
    secret_manager_apikey_name = EXCLUDED.secret_manager_apikey_name, 
    secret_manager_apisecret_name = EXCLUDED.secret_manager_apisecret_name,
    updated_at = CURRENT_TIMESTAMP;