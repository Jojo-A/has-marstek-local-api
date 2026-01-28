"""Tests for the Marstek repairs module."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.marstek.const import DOMAIN
from custom_components.marstek.repairs import (
    CannotConnectRepairFlow,
    async_create_fix_flow,
)


async def test_async_create_fix_flow(hass: HomeAssistant) -> None:
    """Test creating a fix flow."""
    entry_id = "test_entry_id"
    data = {"entry_id": entry_id}

    flow = await async_create_fix_flow(hass, "cannot_connect_test", data)

    assert isinstance(flow, CannotConnectRepairFlow)
    assert flow._entry_id == entry_id


async def test_async_create_fix_flow_no_entry_id() -> None:
    """Test creating a fix flow without entry_id raises error."""
    hass = MagicMock(spec=HomeAssistant)

    with pytest.raises(ValueError, match="No entry_id in issue data"):
        await async_create_fix_flow(hass, "cannot_connect_test", {})


async def test_async_create_fix_flow_none_data() -> None:
    """Test creating a fix flow with None data raises error."""
    hass = MagicMock(spec=HomeAssistant)

    with pytest.raises(ValueError, match="No entry_id in issue data"):
        await async_create_fix_flow(hass, "cannot_connect_test", None)


async def test_repair_flow_abort_entry_not_found(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test repair flow aborts when entry not found."""
    flow = CannotConnectRepairFlow("nonexistent_entry_id")
    flow.hass = hass
    flow.issue_id = "cannot_connect_nonexistent"

    result = await flow.async_step_init()

    assert result["type"] == "abort"
    assert result["reason"] == "entry_not_found"


async def test_repair_flow_shows_form(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test repair flow shows form with entry data."""
    mock_config_entry.add_to_hass(hass)

    flow = CannotConnectRepairFlow(mock_config_entry.entry_id)
    flow.hass = hass
    flow.issue_id = f"cannot_connect_{mock_config_entry.entry_id}"

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert result["description_placeholders"]["host"] == mock_config_entry.data["host"]


async def test_repair_flow_submit_starts_reconfigure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test submitting repair flow starts reconfigure and clears issue."""
    mock_config_entry.add_to_hass(hass)
    
    # Create the issue first
    issue_id = f"cannot_connect_{mock_config_entry.entry_id}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="cannot_connect",
        translation_placeholders={"host": "1.2.3.4", "error": "timeout"},
        data={"entry_id": mock_config_entry.entry_id},
    )
    
    # Verify issue exists
    issue_registry = ir.async_get(hass)
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    flow = CannotConnectRepairFlow(mock_config_entry.entry_id)
    flow.hass = hass
    flow.issue_id = issue_id

    with patch.object(
        hass.config_entries.flow, "async_init", return_value={"type": "form"}
    ) as mock_init:
        result = await flow.async_step_init({})

    # Verify reconfigure flow was started
    mock_init.assert_called_once()
    call_args = mock_init.call_args
    assert call_args[0][0] == DOMAIN
    assert call_args[1]["context"]["source"] == "reconfigure"
    assert call_args[1]["context"]["entry_id"] == mock_config_entry.entry_id
    
    # Verify flow completed
    assert result["type"] == "create_entry"
    assert result["data"] == {}

    # Verify issue was deleted
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None
