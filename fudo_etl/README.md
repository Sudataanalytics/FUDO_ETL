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
Full Refresh: Para asegurar la integridad (especialmente en estados de ventas e ítems), se realiza un truncado y carga completa de las tablas RAW principales en cada ejecución.
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
Producción: En fudo_etl/modules/fudo_api_client.py, asegúrese de que max_pages sea -1.
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