# Timezone Helper - Guía de Uso

Este módulo resuelve los problemas de horario de verano (DST) y gestión de timezones en RenewalGuard.

## El Problema

Antes de implementar este módulo:
- Se usaba `datetime.now()` y `datetime.utcnow()` sin timezone awareness
- Los horarios funcionaban correctamente 6 meses al año (horario de invierno)
- Durante el horario de verano (DST), los timestamps eran incorrectos por 1 hora
- Comparaciones de fechas/horas eran imprecisas

## La Solución

El módulo `timezone_helper` proporciona funciones timezone-aware que:
- Respetan el timezone configurado en `.env` (`TIMEZONE='Europe/Madrid'`)
- Manejan automáticamente las transiciones DST
- Proporcionan conversiones entre timezones

## Configuración

En tu archivo `.env`:

```env
# Timezone configuration
TIMEZONE='Europe/Madrid'
```

Timezones válidos: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

Ejemplos:
- `'Europe/Madrid'` - España (UTC+1, UTC+2 en verano)
- `'America/New_York'` - New York (UTC-5, UTC-4 en verano)
- `'UTC'` - Tiempo universal coordinado
- `'Asia/Tokyo'` - Japón (UTC+9)

## Uso Básico

### ❌ ANTES (Incorrecto)

```python
from datetime import datetime, date

# Problemas con DST
current_time = datetime.now()  # Naive, sin timezone
current_date = date.today()    # Puede diferir del servidor
utc_time = datetime.utcnow()  # Naive, requiere conversión manual
```

### ✅ AHORA (Correcto)

```python
from src.utils.timezone_helper import now, today, to_local, to_utc

# Timezone-aware, maneja DST automáticamente
current_time = now()          # datetime con tzinfo='Europe/Madrid'
current_date = today()        # date en timezone local
utc_time = to_utc(now())     # Conversión explícita a UTC
```

## Funciones Principales

### `now()` - Datetime actual

```python
from src.utils.timezone_helper import now

current = now()
# 2026-02-05 14:30:45.123456+01:00 (invierno)
# 2026-07-05 14:30:45.123456+02:00 (verano - DST activo)

print(f"Hora actual: {current}")
print(f"¿DST activo?: {current.dst()}")
```

### `today()` - Fecha actual

```python
from src.utils.timezone_helper import today

current_date = today()
# 2026-02-05

# Usar en queries de base de datos
subscriptions = Subscription.query.filter(
    Subscription.renewal_date <= today()
).all()
```

### `current_time()` - Hora actual

```python
from src.utils.timezone_helper import current_time

current_t = current_time()
# 14:30:45.123456
```

### `to_local()` - Convertir a timezone local

```python
from src.utils.timezone_helper import to_local
from datetime import datetime

# Desde UTC (naive)
utc_dt = datetime(2026, 2, 5, 13, 0, 0)
local_dt = to_local(utc_dt, from_tz='UTC')
# 2026-02-05 14:00:00+01:00 (UTC+1 en invierno)

# En verano
utc_dt = datetime(2026, 7, 5, 13, 0, 0)
local_dt = to_local(utc_dt, from_tz='UTC')
# 2026-07-05 15:00:00+02:00 (UTC+2 en verano)

# Desde otro timezone
ny_dt = datetime(2026, 2, 5, 12, 0, 0)
local_dt = to_local(ny_dt, from_tz='America/New_York')
# 2026-02-05 18:00:00+01:00
```

### `to_utc()` - Convertir a UTC

```python
from src.utils.timezone_helper import to_utc, now

# Convertir datetime local a UTC
local_dt = now()
utc_dt = to_utc(local_dt)

# Para almacenar en base de datos (si usas UTC)
subscription.created_at = to_utc(now())
```

### Conversiones naive/aware

```python
from src.utils.timezone_helper import naive_to_aware, aware_to_naive
from datetime import datetime

# Naive → Aware
naive = datetime(2026, 2, 5, 14, 30)
aware = naive_to_aware(naive)
# 2026-02-05 14:30:00+01:00

# Aware → Naive (útil para almacenamiento)
aware = now()
naive = aware_to_naive(aware)
# 2026-02-05 14:30:00 (sin tzinfo)
```

## Casos de Uso Comunes

### 1. Verificar renovaciones próximas

```python
from src.utils.timezone_helper import now, today
from datetime import timedelta

# Suscripciones que renuevan en los próximos 7 días
seven_days = today() + timedelta(days=7)

subscriptions = Subscription.query.filter(
    Subscription.renewal_date.between(today(), seven_days)
).all()
```

### 2. Programar tareas (APScheduler)

```python
from src.utils.timezone_helper import now
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# Programar tarea a las 9:00 AM en timezone local
scheduler.add_job(
    func=send_notifications,
    trigger='cron',
    hour=9,
    minute=0,
    timezone='Europe/Madrid'  # Respeta DST automáticamente
)
```

### 3. Comparar timestamps

```python
from src.utils.timezone_helper import now

# Timestamp de base de datos (puede ser naive o aware)
db_timestamp = subscription.created_at

# Convertir a aware si es naive
if db_timestamp.tzinfo is None:
    db_timestamp = naive_to_aware(db_timestamp)

# Comparar con hora actual
elapsed = now() - db_timestamp
if elapsed.days > 30:
    print("Suscripción creada hace más de 30 días")
```

### 4. Mostrar timestamps al usuario

```python
from src.utils.timezone_helper import to_local

# Timestamp en UTC desde API externa
utc_timestamp = api_response['created_at']

# Convertir a timezone local para mostrar
local_timestamp = to_local(utc_timestamp, from_tz='UTC')

# Formatear para el usuario
display = local_timestamp.strftime('%d/%m/%Y %H:%M:%S %Z')
# "05/02/2026 14:30:45 CET" (invierno)
# "05/07/2026 15:30:45 CEST" (verano)
```

### 5. Auditoría y logs

```python
from src.utils.timezone_helper import now, get_timezone_name, get_timezone_offset

# Crear log con timezone info
log_entry = {
    'timestamp': now().isoformat(),
    'timezone': get_timezone_name(),
    'offset': get_timezone_offset(),
    'action': 'subscription_created',
    'user_id': user.id
}

# Output:
# {
#   'timestamp': '2026-02-05T14:30:45.123456+01:00',
#   'timezone': 'Europe/Madrid',
#   'offset': '+01:00',
#   'action': 'subscription_created',
#   'user_id': 123
# }
```

## Funciones Auxiliares

### `get_timezone_name()` - Obtener nombre del timezone

```python
from src.utils.timezone_helper import get_timezone_name

tz_name = get_timezone_name()
# 'Europe/Madrid'
```

### `get_timezone_offset()` - Obtener offset actual

```python
from src.utils.timezone_helper import get_timezone_offset

offset = get_timezone_offset()
# '+01:00' (invierno)
# '+02:00' (verano - DST)
```

### `is_dst()` - Verificar si DST está activo

```python
from src.utils.timezone_helper import is_dst

if is_dst():
    print("Horario de verano activo")
else:
    print("Horario de invierno")
```

## Migración de Código Existente

### Paso 1: Importar el módulo

```python
from src.utils.timezone_helper import now, today, to_local, to_utc
```

### Paso 2: Reemplazar llamadas

| ❌ Antes | ✅ Ahora |
|---------|---------|
| `datetime.now()` | `now()` |
| `date.today()` | `today()` |
| `datetime.utcnow()` | `to_utc(now())` |

### Paso 3: Actualizar comparaciones

```python
# ❌ ANTES
if subscription.renewal_date < date.today():
    # ...

# ✅ AHORA
from src.utils.timezone_helper import today

if subscription.renewal_date < today():
    # ...
```

### Paso 4: Actualizar scheduled jobs

```python
# ❌ ANTES
scheduler.add_job(func, 'cron', hour=9)  # Usa UTC por defecto

# ✅ AHORA
scheduler.add_job(
    func, 'cron', hour=9,
    timezone='Europe/Madrid'  # Especifica timezone explícitamente
)
```

## Testing con Timezones

```python
import pytest
from src.utils.timezone_helper import now, to_local

def test_renewal_date_in_winter():
    """Test renewal date calculation in winter (UTC+1)."""
    utc_time = datetime(2026, 1, 15, 8, 0)  # 8:00 AM UTC
    local_time = to_local(utc_time, from_tz='UTC')

    assert local_time.hour == 9  # 9:00 AM Madrid (UTC+1)

def test_renewal_date_in_summer():
    """Test renewal date calculation in summer (UTC+2 - DST)."""
    utc_time = datetime(2026, 7, 15, 8, 0)  # 8:00 AM UTC
    local_time = to_local(utc_time, from_tz='UTC')

    assert local_time.hour == 10  # 10:00 AM Madrid (UTC+2)
```

## Best Practices

1. **Siempre usa `now()` en vez de `datetime.now()`**
   - Garantiza timezone awareness
   - Maneja DST automáticamente

2. **Almacena timestamps en UTC cuando sea posible**
   ```python
   subscription.created_at = to_utc(now())
   ```

3. **Convierte a local solo para display**
   ```python
   display_time = to_local(subscription.created_at)
   ```

4. **Especifica timezone en scheduled jobs**
   ```python
   scheduler.add_job(func, 'cron', hour=9, timezone='Europe/Madrid')
   ```

5. **Usa `today()` para comparaciones de fechas**
   ```python
   if subscription.renewal_date <= today():
       send_renewal_notification()
   ```

## Troubleshooting

### Problema: "TypeError: can't compare offset-naive and offset-aware datetimes"

**Solución**: Convierte ambos datetimes a aware:

```python
from src.utils.timezone_helper import naive_to_aware

if db_timestamp.tzinfo is None:
    db_timestamp = naive_to_aware(db_timestamp)

if db_timestamp < now():
    # ...
```

### Problema: Los timestamps son 1 hora incorrectos

**Causa**: Probablemente usando `datetime.now()` en vez de `now()`

**Solución**: Reemplaza todas las llamadas a `datetime.now()` por `now()`

### Problema: Scheduled jobs ejecutan a hora incorrecta

**Causa**: APScheduler usa UTC por defecto

**Solución**: Especifica timezone explícitamente:

```python
scheduler.add_job(
    func=my_task,
    trigger='cron',
    hour=9,
    timezone='Europe/Madrid'  # ← Agregar esto
)
```

## Referencias

- [pytz Documentation](https://pythonhosted.org/pytz/)
- [Python datetime with timezone](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects)
- [TZ Database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
