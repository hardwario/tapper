"""Config loading and Network Manager handling."""

import ipaddress
import json
import uuid
from enum import verify

import click
import dbus
import yaml
from loguru import logger


@logger.catch(reraise=True)
def load(path: str) -> tuple[str, int, str | None, str | None, str | None, bool]:
    """Load the config and configure the Wi-Fi network.

    Args:
        path (): path to the configuration file

    Returns:
        A tuple containing all the settings from the config file.

        (mqtt_host, mqtt_port, tls_ca, tls_cert, tls_key)
    """
    with open(path, "r") as file:
        config: dict = yaml.safe_load(file)

    mqtt_host: str = config["mqtt"]["host"]
    mqtt_port: int = int(config["mqtt"]["port"])

    if "tls" in config["mqtt"]:
        tls_ca: str = config["mqtt"]["tls"].get("cafile")
        tls_cert: str = config["mqtt"]["tls"].get("certfile")
        tls_key: str = config["mqtt"]["tls"].get("keyfile")

    legacy: bool = config.get("legacy")

    logger.debug("Config loaded: " + f"'{json.dumps(config)}'")

    if "wifi" in config:
        logger.debug("Setting up WiFi")
        options: dict = config["wifi"]
        _setup_network(options)

    return (
        mqtt_host,
        mqtt_port,
        tls_ca if "tls_ca" in locals() else None,
        tls_cert if "tls_cert" in locals() else None,
        tls_key if "tls_key" in locals() else None,
        legacy,
    )


def _setup_network(options: dict[str, str | list]):
    network: str = options.get("network")
    passphrase: str = options.get("passphrase")
    dns: list | None = (
        [ipaddress.ip_address(server).packed for server in options.get("nameservers")]
        if options.get("dns") is not None
        else None
    )
    gateway: str | None = options.get("gateway")
    address: str | None = options.get("address")
    mode: str = options.get("mode")

    method: str

    settings_connection: dbus.Dictionary = dbus.Dictionary(
        {"type": "802-11-wireless", "uuid": str(uuid.uuid4()), "id": "tapper"}
    )

    settings_wifi: dbus.Dictionary = dbus.Dictionary(
        {"ssid": dbus.ByteArray(network.encode("utf-8")), "mode": "infrastructure"}
    )

    settings_wifi_security: dbus.Dictionary = dbus.Dictionary(
        {"key-mgmt": "wpa-psk", "auth-alg": "open", "psk": passphrase}
    )

    connection: dbus.Dictionary = dbus.Dictionary(
        {
            "connection": settings_connection,
            "802-11-wireless": settings_wifi,
            "802-11-wireless-security": settings_wifi_security,
        }
    )

    match mode:
        case "dynamic":
            settings_ip: dbus.Dictionary = dbus.Dictionary({"method": "auto"})

            connection["ipv4"] = settings_ip
            connection["ipv6"] = settings_ip

        case "static":
            ip_interface = ipaddress.ip_interface(f"{address}")

            settings_address: dbus.Dictionary = dbus.Dictionary(
                {
                    "address": dbus.String(str(ip_interface.ip), variant_level=1),
                    "prefix": dbus.UInt32(
                        ip_interface.network.prefixlen, variant_level=1
                    ),
                }
            )

            if gateway is not None:
                settings_address["gateway"] = dbus.String(gateway)

            if dns is not None:
                settings_address["dns"] = dbus.Array(
                    [dbus.Array(dbus.UInt32(server)) for server in dns]
                )

            settings_ip: dbus.Dictionary = dbus.Dictionary(
                {
                    "method": "manual",
                    "address-data": dbus.Array([settings_address]),
                }
            )

            connection[f"ipv{int(ip_interface.ip.version)}"] = settings_ip

        case _:
            raise click.UsageError(
                f"Invalid mode for connection specified! Should be static or dynamic. Mode: {mode}"
            )

    logger.debug(
        "Creating connection: "
        + settings_connection["id"]
        + " - "
        + settings_connection["uuid"]
    )
    logger.debug(f"SSID: {settings_wifi['ssid']}")

    bus = dbus.SystemBus()
    proxy = bus.get_object(
        "org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings"
    )
    nm_settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")

    logger.debug("DBus NetworkManager settings interface opened")

    nm_settings.AddConnection(connection)
    logger.debug("Connection added")

    connections: list = nm_settings.ListConnections()
    logger.debug(f"Connections: {connections}")

    connection_0_proxy = bus.get_object(
        "org.freedesktop.NetworkManager", connections[0]
    )

    connection_0 = dbus.Interface(
        connection_0_proxy, "org.freedesktop.NetworkManager.Settings.Connection"
    )

    logger.debug(f"{connection_0.GetSettings()}")
