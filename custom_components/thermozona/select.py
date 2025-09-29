"""Select platform for Thermozona helper entities."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, CONF_HEAT_PUMP_MODE
from .heat_pump import HeatPumpController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermozona select entities."""
    domain_data = hass.data[DOMAIN]
    entry_config = domain_data[config_entry.entry_id]

    controllers = domain_data.setdefault("controllers", {})
    controller = controllers.get(config_entry.entry_id)
    if controller is None:
        controller = HeatPumpController(hass, entry_config)
    else:
        controller.refresh_entry_config(entry_config)
    controllers[config_entry.entry_id] = controller

    if entry_config.get(CONF_HEAT_PUMP_MODE):
        _LOGGER.debug(
            "%s: External heat pump mode entity configured; skipping internal select",
            DOMAIN,
        )
        return

    async_add_entities(
        [ThermozonaHeatPumpModeSelect(config_entry.entry_id, controller)]
    )


class ThermozonaHeatPumpModeSelect(SelectEntity):
    """Expose the heat pump mode as a selectable entity."""

    _attr_has_entity_name = True
    _attr_name = "Thermozona Heat Pump Mode"
    _attr_options = ["auto", "heat", "cool", "off"]
    _attr_icon = "mdi:hvac"
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        entry_id: str,
        controller: HeatPumpController,
    ) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry_id}_heat_pump_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "Thermozona",
        }
        self._attr_current_option = "auto"

    async def async_added_to_hass(self) -> None:
        """Register the select with the controller."""
        await super().async_added_to_hass()
        self.async_write_ha_state()
        self._controller.register_mode_select(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the select when removed."""
        self._controller.unregister_mode_select(self)
        await super().async_will_remove_from_hass()

    async def async_select_option(self, option: str) -> None:
        """Handle user mode selection."""
        if option not in self.options:
            raise ValueError(f"Unsupported option: {option}")
        self._controller.set_mode_value(option)

    def update_current_option(self, option: str) -> None:
        """Update the select option from the controller."""
        if option not in self.options:
            return
        self._attr_current_option = option
        self.async_write_ha_state()
