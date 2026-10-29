🚀 Solución ETL Multicliente Fu.do (Grupo Ginesta & Sudata)
Este repositorio contiene la infraestructura Genérica y Dockerizada de Extracción, Transformación y Carga (ETL) diseñada para centralizar datos de múltiples clientes que utilizan el sistema gastronómico Fu.do.
Actualmente, el sistema gestiona de forma independiente a:
D-002-Miguitas (3 sucursales)
D-003-Amoremio (9 sucursales)
🏗️ Arquitectura Genérica (Mono-Repo)
La solución separa el Core del ETL (lógica de extracción y carga) de la Configuración por Cliente (reglas de negocio y sucursales), permitiendo escalar a nuevos clientes en minutos.
Componentes Clave:
Core Genérico (fudo_etl/): Código Python único que maneja la conexión a la API de Fudo y la persistencia en PostgreSQL.
Capa de Clientes (clients/): Archivos SQL y Python específicos que definen las sucursales y el modelo analítico de cada cliente.
Estrategia de Carga:
Full Refresh: Para asegurar la integridad (especialmente en estados de ventas e ítems), se descargan completas de Fudo las entidades principales en cada ejecución, pero en las tablas RAW solo se escriben las filas nuevas, cambiadas o eliminadas.
Claves Sintéticas: Los IDs se gestionan como ID_FUDO-ID_SUCURSAL (tipo TEXT) para evitar colisiones entre sucursales.
Infraestructura: Google Cloud Platform (Proyecto: dashestandar).
📁 Estructura del Proyecto
code
Text
FUDO/
├── fudo_etl/                # CORE GENÉRICO (No tocar para nuevos clientes)
│   ├── modules/             # Lógica de API, DB y Auth
│   ├── sql/
│   │   ├── base_raw_tables_and_metadata.sql  # Tablas fudo_raw_* comunes
│   │   └── initial_grants.sql               # Permisos de DB
│   └── main.py              # Orquestador dinámico
├── clients/                 # CONFIGURACIÓN POR CLIENTE
│   ├── miguitas/
│   │   ├── branches.sql            # Sucursales y Credenciales
│   │   ├── der_tables_ddl.sql      # Tablas lógicas del DER
│   │   └── analytical_layer_mvs.py  # Vistas Materializadas (Gold)
│   └── amoremio/            # (Misma estructura que miguitas)
├── Dockerfile               # Empaquetado genérico
├── cloudbuild.yaml          # Automatización de despliegue en GCP
├── requirements.txt         # Dependencias Python
└── .env                     # Variables locales (IGNORADO POR GIT)
⚙️ Configuración y Despliegue (Equipo Técnico)
1. Preparación Local
Entorno Virtual: python -m venv venv -> .\venv\Scripts\activate
Dependencias: pip install -r fudo_etl/requirements.txt
Funcionamiento de la carga:
- La API se lee página por página y cada página se carga apenas llega (la memoria no crece con la historia del cliente).
- Entidades full refresh: se cargan en una tabla staging (stg_fudo_raw_*) y luego se reemplazan los datos de la sucursal en una sola transacción. El reemplazo es diferencial por payload_checksum: se borran solo las filas que ya no existen o cambiaron y se insertan solo las nuevas o cambiadas (el [AUDIT] informa cuántas). Si algo falla, la tabla RAW queda como estaba.
- Las MVs se crean solo si no existen y luego se refrescan con REFRESH MATERIALIZED VIEW CONCURRENTLY. Si se cambia la definición de una MV, correr el job una vez con REBUILD_MVS=true.
- Antes de extraer se validan las credenciales de cada sucursal. Las que fallan (secreto inaccesible o 401 de Fudo) se omiten y no cuentan como error: quedan en el log con el prefijo [CREDENCIALES] (buscar ese texto en Cloud Logging para ver cuáles se saltearon). Si ninguna sucursal tiene credenciales válidas, el proceso termina con exit code 1.
- Si falla cualquier entidad/MV, el proceso termina con exit code 1 (el job queda como fallido en Cloud Run).
- La extracción corre en paralelo: ETL_BRANCH_WORKERS sucursales a la vez y, dentro de cada una, ETL_ENTITY_WORKERS entidades a la vez (cada hilo lee de la API y carga sus páginas). Los requests simultáneos a Fudo son el producto de ambos; si aparecen muchos 429, bajarlos.
- La base se accede con un pool de conexiones (por defecto una por hilo + 1). Una conexión caída se descarta y se abre otra; las ociosas por más de DB_POOL_PING_AFTER_IDLE_SECONDS se validan antes de usarse.
Variables opcionales (con sus valores por defecto):
- ETL_BRANCH_WORKERS=3, ETL_ENTITY_WORKERS=2
- DB_POOL_SIZE=ETL_BRANCH_WORKERS x ETL_ENTITY_WORKERS + 1, DB_POOL_PING_AFTER_IDLE_SECONDS=60
- DB_STATEMENT_TIMEOUT_MS=900000, DB_LOCK_TIMEOUT_MS=30000, DB_IDLE_IN_TX_TIMEOUT_MS=300000
- DB_SWAP_STATEMENT_TIMEOUT_MS=2700000 (timeout del reemplazo staging -> RAW de un Full Refresh, solo en esa transacción)
- DB_MAX_RETRIES=4, DB_RETRY_BASE_DELAY_SECONDS=2
- API_ENTITY_DEADLINE_SECONDS=1800 (tiempo máximo para extraer una entidad de una sucursal)
- API_INTER_PAGE_DELAY_SECONDS=0.15 (pausa entre páginas de la API de Fudo)
- FUDO_MAX_RETRY_AFTER_SECONDS=300 (tope de espera cuando Fudo responde con Retry-After; Fudo limita por ventanas de ~5 min, compartidas entre sucursales)
- FUDO_TOKEN_MIN_VALIDITY_MINUTES=60 (vigencia mínima para reusar un token guardado; ante un 401 se renueva solo)
- REBUILD_MVS=false
2. Automatización en GCP
Cada git push a la rama main dispara Cloud Build, el cual:
Construye la imagen Docker genérica.
Actualiza los Cloud Run Jobs: d-002-miguitas y d-003-amoremio.


📘 Manual de Replicación: Agregar un Nuevo Cliente
(Diseñado para equipo no técnico de Sudata)
Para agregar un cliente nuevo (ejemplo: D-004-Pepito), siga estos pasos:

Paso 1: Base de Datos (Donweb)
Ingrese a pgAdmin y conéctese al servidor de Donweb.
Cree una base de datos vacía llamada exactamente D-004-pepito.

Paso 2: Configuración en GitHub
En la carpeta clients/, cree una carpeta llamada pepito/.
Copie los archivos branches.sql, der_tables_ddl.sql y analytical_layer_mvs.py de la carpeta miguitas/.
Edite branches.sql: Reemplace los nombres e IDs por las credenciales de Fudo del nuevo cliente.

Paso 3: Secretos en GCP (Secret Manager)
Ingrese a Google Cloud (Proyecto dashestandar) -> Secret Manager.
Cree el secreto D-004-PEPITO-DB-CONN con el valor: postgresql://sudata_owner:6w3zAQa4sXs6z@vps-4657831-x.dattaweb.com:5432/D-004-pepito.
Cree los secretos para cada sucursal siguiendo el formato: FUDO_PEPITO_SUCURSAL_APIKEY y FUDO_PEPITO_SUCURSAL_APISECRET.
Permisos: Asegúrese de que la cuenta de servicio 481795797888-compute@developer... tenga el rol de Secret Manager Secret Accessor en estos nuevos secretos.

Paso 4: Actualizar Despliegue
Abra el archivo cloudbuild.yaml.
Copie el bloque de Amoremio (Step 4) y péguelo abajo.
Cambie d-003-amoremio por d-004-pepito y el secreto de la base de datos.
Haga Push a GitHub.

Paso 5: Programación
En Cloud Run, cree el Job inicial d-004-pepito con la variable CLIENT_NAME=pepito.
En Cloud Scheduler, cree una tarea para que el Job corra cada 2 horas (Frecuencia: 0 8-23/2 * * *).



📊 Integración con Power BI
Conexión: Use el On-premises Data Gateway conectado a la base de datos de Donweb del cliente.
Tablas Clave:
mv_sales_order: Cabecera de ventas (Usar order_key).
mv_sales_order_line: Detalle de ventas (Usar price_unit corregido para evitar picos).
mv_pagos: Flujo de caja (Usar signed_amount para neto de ingresos/gastos y transaction_type para filtrar).
mv_providers: Maestro de proveedores (Nuevo).
Mantenimiento: El modelo analítico utiliza claves tipo TEXT. Asegúrese de que las relaciones en Power BI usen los campos _key o _key_fk.
Soporte y Contacto
Desarrollado por el equipo de Ingeniería de Datos de Sudata Analytics.
Dudas técnicas: devops@sudata.co