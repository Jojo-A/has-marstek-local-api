---
name: homeassistant-integration-patterns
description: Project-specific patterns for the Marstek integration (config flow, coordinator, scanner, entities, translations)
---

# Home Assistant Integration Patterns (Marstek)

This skill helps you make correct, repo-consistent changes to this Home Assistant custom integration.

## When to Use

- Adding/changing sensors
- Changing discovery/config flow behavior
- Updating coordinator error handling
- Working on translations or diagnostics
- Ensuring changes meet Home Assistant integration quality expectations

## Quick Map

| Task | File(s) |
|---|---|
| Setup / teardown / coordinator wiring | `custom_components/marstek/__init__.py` |
| Config flow (user, dhcp, integration discovery) | `custom_components/marstek/config_flow.py` |
| Central polling | `custom_components/marstek/coordinator.py` |
| IP-change scanner | `custom_components/marstek/scanner.py` |
| Entities (sensors) | `custom_components/marstek/sensor.py` |
| Device automation actions | `custom_components/marstek/device_action.py` |
| Text / translations | `custom_components/marstek/strings.json`, `custom_components/marstek/translations/en.json` |
| Local API reference | `docs/MarstekDeviceOpenApi.pdf` |

## Core Rules

1. **Coordinator-only I/O**
   - Never add per-entity UDP calls.
   - Read everything from `MarstekDataUpdateCoordinator.data`.
   - Use `_async_setup()` for one-time initialization during first refresh.
   - Set `always_update=False` if data supports `__eq__` comparison.

2. **Async-only**
   - Only do async I/O; never block the event loop.

### Coordinator Error Handling
```python
async def _async_update_data(self):
    try:
        return await self.api.fetch_data()
    except AuthError as err:
        # Triggers reauth flow automatically
        raise ConfigEntryAuthFailed from err
    except RateLimitError:
        # Backoff with retry_after
        raise UpdateFailed(retry_after=60)
    except ConnectionError as err:
        raise UpdateFailed(f"Connection failed: {err}")
```

3. **Avoid unavailable clutter**
   - Only create entities when there’s a corresponding data key in coordinator output.
   - Prefer explicit per-sensor classes or a description table keyed by coordinator data.

4. **Use translation-aware config-flow errors**
   - Config flow errors should use keys defined in `custom_components/marstek/strings.json`.
   - Reauth flows should ask only for the changed credential and update the existing entry.

5. **Stable identifiers**
   - Use BLE-MAC-based unique IDs for entities and devices; never pivot on IPs.
   - Keep `_attr_has_entity_name = True` and set `device_info` for grouping.

## Adding a new sensor

Steps:
1. Find the value on `coordinator.data` (a plain `dict[str, Any]` coming from `pymarstek`).
2. Add a new sensor entity in `custom_components/marstek/sensor.py`.
3. Keep the `unique_id` stable (BLE-MAC based + sensor key).
4. If user-facing, add translation in `custom_components/marstek/translations/en.json` (and keep `strings.json` in sync).
5. Only register entities for data keys that exist to avoid permanent `unavailable` noise.

### Entity Patterns (Mandatory for New Integrations)

```python
class MarstekSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True  # MANDATORY
    
    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.ble_mac}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.ble_mac)},
            name=coordinator.device_name,
            manufacturer="Marstek",
        )
```

### EntityDescription Pattern (Recommended)

```python
@dataclass(kw_only=True)
class MarstekSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict], StateType]
    exists_fn: Callable[[dict], bool] = lambda _: True

SENSORS: tuple[MarstekSensorEntityDescription, ...] = (
    MarstekSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("soc"),
    ),
    MarstekSensorEntityDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("power"),
    ),
)
```

### Icon Translations (Preferred over `icon` property)
Create `icons.json`:
```json
{
  "entity": {
    "sensor": {
      "battery_soc": {
        "default": "mdi:battery",
        "state": {
          "100": "mdi:battery",
          "50": "mdi:battery-50"
        }
      }
    }
  }
}
```

### Entity Categories
- `EntityCategory.DIAGNOSTIC` - RSSI, firmware version, temperature
- `EntityCategory.CONFIG` - Settings the user can change
- Set `entity_registry_enabled_default = False` for rarely-used sensors

### State Classes for Energy Sensors
- `SensorStateClass.MEASUREMENT` - Instantaneous values (power, temperature)
- `SensorStateClass.TOTAL` - Values that can increase/decrease (net energy)
- `SensorStateClass.TOTAL_INCREASING` - Only increases, resets to 0 (lifetime energy)
- Use `SensorDeviceClass.ENERGY_STORAGE` for battery capacity (stored Wh)

## Common pitfalls

- Polling/discovery storms (too many UDP requests too frequently).
- Doing IP discovery inside setup or coordinator updates (scanner already handles this).
- Sending control commands without pausing polling (causes concurrent UDP traffic and flaky results).
- Breaking unique IDs (must remain stable across upgrades and IP changes).
- Skipping options reload listeners or reauth handling in `config_flow.py`.
