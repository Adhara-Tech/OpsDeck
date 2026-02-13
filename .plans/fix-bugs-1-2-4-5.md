# Plan: Corregir Bugs 1, 2, 4 y 5

## Contexto

La revisión de OpsDeck identificó 4 bugs que afectan la **precisión de cálculos financieros**. Todos violan la regla crítica documentada en CLAUDE.md: "Any code that calculates future renewals MUST check `subscription.auto_renew` first". El bug 2 es un caso de seguridad defensiva (infinite loop potencial).

---

## Bug 1: `Budget.remaining` no filtra por `auto_renew`

**Archivo:** `src/models/procurement.py` — linea 244
**Problema:** El loop en `remaining` itera todas las subscriptions y proyecta renewals sin verificar `auto_renew`. Subscriptions no-renovables inflan el gasto calculado.

**Cambio:** Añadir `if not subscription.auto_renew: continue` después del check de `is_archived` en linea 246. Para subscriptions con `auto_renew=False`, contar solo UNA vez si `renewal_date` cae dentro del periodo del budget.

```python
# linea 244-259, después del check is_archived:
for subscription in self.subscriptions:
    if subscription.is_archived:
        continue

    rate = get_conversion_rate(subscription.currency)
    cost_in_budget_currency = subscription.cost * rate

    if not subscription.auto_renew:
        # Non-renewable: count only once if renewal_date falls within budget period
        if self.valid_from <= subscription.renewal_date <= self.valid_until:
            spent += cost_in_budget_currency
        continue

    # Auto-renewable: count all renewals within budget period
    renewal_count = self._count_renewals_in_period(...)
    spent += cost_in_budget_currency * renewal_count
```

---

## Bug 2: Loop infinito en `_count_renewals_in_period` si `renewal_period_value=0`

**Archivo:** `src/models/procurement.py` — linea 263 y 372
**Problema:** Si `period_value=0`, `relativedelta(months=+0)` no avanza la fecha y el `while` loop nunca termina.

**Cambio:** Añadir un `@validates('renewal_period_value')` en el modelo `Subscription` y un guard clause al inicio de `_count_renewals_in_period`.

```python
# En Subscription (después del validate_cost existente en linea 423):
@validates('renewal_period_value')
def validate_renewal_period_value(self, key, value):
    if value is not None and value <= 0:
        raise ValueError(f"Renewal period value must be greater than 0, got {value}")
    return value

# En _count_renewals_in_period (linea 263), añadir al inicio:
if not period_value or period_value <= 0:
    return 0
```

---

## Bug 4: Forecasts financieros no respetan `auto_renew`

**Archivos y ubicaciones exactas:**

### 4a. `src/routes/reports.py` — 3 loops (lineas 30, 71, 102)

**Loop 1 (linea 30):** Spending by Supplier — proyecta renewals en el año seleccionado
**Loop 2 (linea 71):** Historical Spending — proyecta renewals históricos
**Loop 3 (linea 102):** Forecast Chart — proyecta renewals futuros 13 meses

**Cambio:** En los 3 loops, añadir `if not subscription.auto_renew: continue` como primera linea del `for`.

### 4b. `src/routes/main.py` — 1 loop (linea 1001)

**Loop (linea 1001):** Ops Finance Dashboard Forecast — proyecta renewals futuros 13 meses

**Cambio:** Añadir `if not subscription.auto_renew: continue` como primera linea del `for`.

**Nota:** El loop de lineas 977-985 en main.py ya usa `subscription.next_renewal_date` que retorna `None` para `auto_renew=False`, así que está correcto. Solo el forecast de linea 1001 necesita fix.

---

## Bug 5: `CostHistory.total_cost` devuelve base cost con 0 usuarios

**Archivo:** `src/models/procurement.py` — linea 310
**Problema:** Si `pricing_model='per_user'` y `user_count=0`, la condición `self.user_count` evalúa `False` (0 es falsy), cayendo al fallback `self.cost or 0` que devuelve el coste base.

**Cambio:** Separar la lógica para que `per_user` con 0 usuarios devuelva 0 explícitamente.

```python
@property
def total_cost(self):
    if self.pricing_model == 'per_user' and self.cost_per_user is not None:
        return self.cost_per_user * (self.user_count or 0)
    return self.cost or 0
```

---

## Tests

Añadir tests en `tests/test_finance.py` (archivo existente con tests de budget):

1. **`test_budget_remaining_ignores_non_renewable_subscriptions`** — Budget con subscription `auto_renew=False`, verificar que `remaining` no cuenta renewals proyectadas
2. **`test_budget_remaining_counts_renewable_subscriptions`** — Budget con subscription `auto_renew=True`, verificar que `remaining` cuenta renewals dentro del periodo
3. **`test_budget_remaining_non_renewable_counts_once_if_in_period`** — Subscription no-renovable con `renewal_date` dentro del budget period se cuenta exactamente una vez
4. **`test_count_renewals_zero_period_value`** — Verificar que `_count_renewals_in_period` retorna 0 con `period_value=0`
5. **`test_subscription_renewal_period_value_validation`** — Verificar que `renewal_period_value <= 0` lanza `ValueError`
6. **`test_cost_history_per_user_zero_users`** — CostHistory con `per_user` model y `user_count=0` retorna 0

---

## Orden de ejecución

1. Bug 2 (guard clause defensivo — previene crash)
2. Bug 1 (Budget.remaining — depende del guard del bug 2 para seguridad)
3. Bug 5 (CostHistory — cambio aislado)
4. Bug 4 (forecasts en routes — cambios en 4 loops)
5. Tests
6. Ejecutar `pytest` para verificar que nada se rompe

---

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `src/models/procurement.py` | Bugs 1, 2, 5 |
| `src/routes/reports.py` | Bug 4 (3 loops) |
| `src/routes/main.py` | Bug 4 (1 loop) |
| `tests/test_finance.py` | 6 tests nuevos |
