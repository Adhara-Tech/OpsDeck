# bcdr_export.py — BCDR Export (Disaster Recovery)

Script standalone que extrae **todos los datos** de la base de datos de OpsDeck y genera un directorio con un archivo Excel (`.xlsx`) por cada tipo de entidad. Pensado para backups offline, auditorías y recuperación de datos en caso de desastre.

## Requisitos

```bash
pip install sqlalchemy psycopg2-binary openpyxl
```

## Uso

```bash
# Conexión por DATABASE_URL (recomendado)
python scripts/bcdr_export.py --database-url postgresql://opsdeck:opsdeck@localhost:5432/opsdeck

# Conexión por parámetros individuales
python scripts/bcdr_export.py --host db.prod.internal --port 5432 --db opsdeck --user opsdeck --password opsdeck

# Directorio de salida personalizado
python scripts/bcdr_export.py --database-url $DATABASE_URL --output /backups/opsdeck_20260224

# Usar variable de entorno DATABASE_URL directamente
export DATABASE_URL=postgresql://opsdeck:opsdeck@localhost:5432/opsdeck
python scripts/bcdr_export.py
```

Si no se especifica `--output`, se crea un directorio `bcdr_opsdeck_YYYYMMDD_HHMM/` en el directorio actual.

## Ejecución dentro de Docker

El puerto de la BD no suele estar expuesto al host, así que es más sencillo ejecutar desde dentro del contenedor web:

```bash
# Copiar el script al contenedor y ejecutar
docker cp scripts/bcdr_export.py opsdeck-web-1:/tmp/bcdr_export.py

# Instalar openpyxl si no está (sqlalchemy y psycopg2 ya están en la imagen)
docker exec opsdeck-web-1 pip install openpyxl

# Ejecutar
docker exec opsdeck-web-1 python /tmp/bcdr_export.py \
  --database-url postgresql://opsdeck:opsdeck@db:5432/opsdeck \
  --output /tmp/bcdr_export

# Copiar el resultado al host
docker cp opsdeck-web-1:/tmp/bcdr_export/. ./export/
```

## Salida

Se genera un directorio con **57 archivos**:

| Categoría | Archivos |
|---|---|
| **Organización** | Users, Groups, Locations, Org_Settings |
| **Assets & Inventario** | Assets, Peripherals, Software, Licenses, Maintenance_Logs, Disposal_Records, Asset_Inventories |
| **Procurement & Vendors** | Suppliers, Contacts, Subscriptions, Contracts, Purchases, Budgets, Payment_Methods, Cost_Centers, Requirements, Opportunities |
| **Servicios & Credenciales** | Business_Services, Service_Components, Configurations, Credentials, Credential_Secrets, Certificates, Certificate_Versions |
| **Seguridad & Riesgos** | Risks, Threat_Types, Security_Activities, Activity_Executions, Security_Assessments, Risk_Assessments |
| **Incidentes & Cambios** | Incidents, Post-Incident_Reviews, Changes |
| **Compliance & Auditorías** | Frameworks, Framework_Controls, Compliance_Links, Compliance_Rules, Audits, Audit_Items, Policies, Policy_Versions |
| **BCDR & HR** | BCDR_Plans, BCDR_Tests, Onboarding, Offboarding, Onboarding_Packs |
| **Documentación & Comms** | Links, Documents, Tags, Attachments, Email_Templates, Campaigns |

Más un archivo `_Indice.xlsx` con el resumen de todos los archivos y conteos.

### Formato de cada archivo

- Título con nombre de entidad y fecha de exportación
- Cabeceras estilizadas (azul oscuro, texto blanco)
- Columnas de estado con colores condicionales (verde/amarillo/rojo)
- Columnas de texto largo con alineación izquierda y wrap
- Ancho de columnas auto-ajustado
- IDs incluidos para poder reconstruir relaciones entre entidades

## Notas

- Los **secrets de credenciales** se exportan enmascarados (tal como están en BD, nunca el valor real).
- Los **attachments** se exportan como metadatos (nombre, tipo, ID). Los archivos físicos se guardan aparte en el volumen de uploads.
- Funciona con PostgreSQL (producción) y con SQLite si se pasa una URL `sqlite:///`.
- Si una tabla no existe (por ejemplo en una versión antigua), la hoja se genera con un mensaje de error en lugar de fallar.
