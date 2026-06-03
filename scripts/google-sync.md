# google-sync.py — OpsDeck to Google Workspace Sync

Script que lee onboardings/offboardings pendientes de OpsDeck y provisiona o suspende usuarios en Google Workspace vía la Admin Directory API.

## Requisitos

```bash
pip install requests google-auth google-api-python-client
```

## Variables de entorno

### Obligatorias

| Variable | Descripción | Ejemplo |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Ruta al JSON de service account | `/etc/opsdeck/sa.json` |
| `GOOGLE_DELEGATED_USER` | Email del admin para domain-wide delegation | `admin@tudominio.com` |
| `OPSDECK_URL` | URL base de OpsDeck | `https://opsdeck.internal` |
| `OPSDECK_API_TOKEN` | Bearer token (requiere rol admin) | `abc123...` |

### Opcionales

| Variable | Default | Descripción |
|---|---|---|
| `GOOGLE_ORG_UNIT` | `/` | OU path para nuevos usuarios |
| `GOOGLE_DOMAIN` | *(vacío)* | Dominio para validación (ej: `tudominio.com`) |

## Uso

```bash
# Configurar variables
export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
export GOOGLE_DELEGATED_USER=admin@tudominio.com
export OPSDECK_URL=https://opsdeck.internal
export OPSDECK_API_TOKEN=tu-token-opsdeck

# Preview provisioning (no crea nada en Google)
python scripts/google-sync.py provision --dry-run

# Ejecutar provisioning
python scripts/google-sync.py provision --execute

# Preview suspensiones
python scripts/google-sync.py suspend --dry-run

# Ejecutar suspensiones
python scripts/google-sync.py suspend --execute

# Todo junto (provision + suspend)
python scripts/google-sync.py all --dry-run
python scripts/google-sync.py all --execute
```

## Comandos

| Comando | Descripción |
|---|---|
| `provision` | Crea usuarios en Google desde onboardings pendientes en OpsDeck |
| `suspend` | Suspende usuarios en Google desde offboardings pendientes en OpsDeck |
| `all` | Ejecuta provision + suspend |

Siempre se requiere `--dry-run` o `--execute` para evitar ejecuciones accidentales.

## Flujo de provisioning

1. Lee onboardings pendientes de `GET /api/v1/onboardings/pending-provisioning`
2. Valida dominio del email (si `GOOGLE_DOMAIN` está configurado)
3. Crea el usuario en Google Workspace con:
   - Email, nombre (split en givenName/familyName)
   - Password temporal aleatorio (24 chars, cambio obligatorio en primer login)
   - OU path configurado
   - Department y job_title si están disponibles
4. Marca el onboarding como provisionado en OpsDeck via `POST /api/v1/onboardings/{id}/mark-provisioned`
5. Si el usuario ya existe en Google (409), lo marca como provisionado igualmente

## Flujo de suspensión

1. Lee offboardings pendientes de `GET /api/v1/offboardings/pending-suspension`
2. Suspende el usuario en Google usando `external_id` (Google ID) o email como fallback
3. Marca el offboarding como suspendido en OpsDeck via `POST /api/v1/offboardings/{id}/mark-suspended`
4. Si el usuario no existe en Google (404), lo marca como suspendido igualmente

## Configuración de Google Cloud

Para que el script funcione necesitas:

1. **Service Account** con domain-wide delegation habilitado
2. **Scope** autorizado en la consola de admin de Google: `https://www.googleapis.com/auth/admin.directory.user`
3. **JSON key** del service account descargado y referenciado en `GOOGLE_SERVICE_ACCOUNT_JSON`

## Notas

- Las credenciales de Google solo se requieren en modo `--execute`. El modo `--dry-run` solo necesita acceso a la API de OpsDeck.
- Los passwords temporales se generan con `secrets.choice()` y son de 24 caracteres alfanuméricos + símbolos.
- Si se configura `GOOGLE_DOMAIN`, los emails que no coincidan se saltan (skip) sin error.
