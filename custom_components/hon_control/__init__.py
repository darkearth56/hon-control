"""hOn control: stop, pause and resume services for washers on the gvigroux/hon integration.

Kept separate from gvigroux/hon so its updates don't overwrite these services. It reuses the
hon integration's own connection and the appliance command list it already loaded from the hOn cloud.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import (
    COMMAND_PAUSE,
    COMMAND_RESUME,
    COMMAND_STOP,
    DOMAIN,
    HON_DOMAIN,
    SERVICE_LIST_COMMANDS,
    SERVICE_PAUSE,
    SERVICE_RESUME,
    SERVICE_STOP,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_COMMANDS = {
    SERVICE_STOP: COMMAND_STOP,
    SERVICE_PAUSE: COMMAND_PAUSE,
    SERVICE_RESUME: COMMAND_RESUME,
}


def _device_ids(call: ServiceCall) -> list[str]:
    ids = call.data.get("device_id", [])
    if isinstance(ids, str):
        ids = [ids]
    if not ids:
        raise HomeAssistantError("Choose an hOn device as the target")
    return list(dict.fromkeys(ids))


def _find_hon_device(hass: HomeAssistant, device_id: str) -> Any:
    """Return gvigroux's HonDevice object for a Home Assistant device id."""
    registry = dr.async_get(hass)
    entry = registry.async_get(device_id)
    if entry is None:
        raise HomeAssistantError(f"Device {device_id} not found")
    hon_ids = [ident for ident in entry.identifiers if ident[0] == HON_DOMAIN]
    if not hon_ids:
        raise HomeAssistantError(f"Device {entry.name_by_user or entry.name} is not an hOn device")

    connections = hass.data.get(HON_DOMAIN, {})
    for connection in connections.values():
        get_device = getattr(connection, "get_device", None)
        if get_device is None:
            continue
        device = get_device(hass, device_id)
        if device is not None:
            return device
    raise HomeAssistantError("The hOn integration isn't loaded or doesn't know this device yet")


def _prepare(device: Any, command_name: str) -> Any:
    commands = getattr(device, "commands", None) or {}
    command = commands.get(command_name)
    if command is None:
        available = ", ".join(sorted(commands)) or "none"
        raise HomeAssistantError(f"This appliance has no {command_name} command. Available: {available}")
    # Sent with the values the hOn cloud defines for this command; copying the machine's current
    # parameters in would overwrite them (e.g. onOffStatus on a stop).
    return command


def _describe(command: Any) -> dict[str, Any]:
    result = {}
    for name, parameter in (getattr(command, "parameters", {}) or {}).items():
        info: dict[str, Any] = {"value": getattr(parameter, "value", None), "type": type(parameter).__name__}
        values = getattr(parameter, "values", None)
        if values is not None and name != "program":
            info["allowed"] = list(values)
        result[name] = info
    return result


async def _send(hass: HomeAssistant, device_id: str, command_name: str) -> None:
    device = _find_hon_device(hass, device_id)
    command = _prepare(device, command_name)
    _LOGGER.debug("Sending %s to %s", command_name, device_id)
    try:
        ok = await command.send()
    except Exception as err:  # gvigroux raises assorted internal errors
        raise HomeAssistantError(f"{command_name} failed: {err}") from err
    if not ok:
        raise HomeAssistantError(f"The hOn cloud rejected {command_name}. Check the Home Assistant log for its reply")
    coordinator = getattr(device, "coordinator", None)
    if coordinator is not None:
        await coordinator.async_request_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def handle_command(call: ServiceCall) -> None:
        command_name = SERVICE_COMMANDS[call.service]
        for device_id in _device_ids(call):
            await _send(hass, device_id, command_name)

    async def handle_list_commands(call: ServiceCall) -> ServiceResponse:
        result: dict[str, Any] = {}
        for device_id in _device_ids(call):
            device = _find_hon_device(hass, device_id)
            commands = getattr(device, "commands", None) or {}
            result[device_id] = {
                name: (_describe(cmd) if name != "startProgram" else sorted(getattr(cmd, "parameters", {}) or {}))
                for name, cmd in sorted(commands.items())
            }
        return {"devices": result}

    for service in SERVICE_COMMANDS:
        hass.services.async_register(DOMAIN, service, handle_command)
    hass.services.async_register(
        DOMAIN, SERVICE_LIST_COMMANDS, handle_list_commands, supports_response=SupportsResponse.ONLY
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    for service in [*SERVICE_COMMANDS, SERVICE_LIST_COMMANDS]:
        hass.services.async_remove(DOMAIN, service)
    return True
