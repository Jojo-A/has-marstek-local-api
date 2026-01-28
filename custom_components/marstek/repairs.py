"""Repair flows for Marstek integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


class CannotConnectRepairFlow(RepairsFlow):
    """Handler for cannot connect repair flow."""

    def __init__(self, entry_id: str) -> None:
        """Initialize the repair flow."""
        super().__init__()
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            # User clicked confirm - start reconfigure flow
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_RECONFIGURE,
                    "entry_id": entry.entry_id,
                },
            )
            # Delete the issue since user is addressing it
            ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": entry.data.get("host", "unknown"),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str] | None,
) -> RepairsFlow:
    """Create flow."""
    entry_id = data.get("entry_id") if data else None
    if entry_id is None:
        raise ValueError("No entry_id in issue data")
    return CannotConnectRepairFlow(entry_id)
