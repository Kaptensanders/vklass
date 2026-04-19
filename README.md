![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=)
![Version](https://img.shields.io/github/v/release/Kaptensanders/vklass)
# VKLASS integration for Home Assistant

This integration imports Vklass calendar events into Home Assistant.



## Authentication
Vklass commonly uses one of these authentication modes:

### Username and password
If your district still allows username and password, you provide those credentials in the config flow and the integration handles the login flow internally.

### BankID
BankID is the primary target for this integration.

The intended design is that Home Assistant performs the real BankID-backed Vklass login flow itself. That means the integration should guide the login process and keep the authenticated Vklass session alive, instead of requiring you to fetch browser cookies manually.

For BankID, the integration is being designed around:
* A district-specific Vklass auth URL configured in the integration
* A QR-based login flow for mobile BankID
* A personal-number variant where supported
* A logged-in status entity such as `binary_sensor.vklass_<name>_loggedin`

## Current project direction

The project is intentionally moving away from the older cookie-import approach.

The following should be treated as abandoned design ideas, not the target user experience:
* Reading browser cookie files
* Pasting cookies into Home Assistant
* Querying an external API that returns cookies
* Pushing plaintext cookies into Home Assistant through a custom API

## Scope for version 1.0

Version 1.0 is focused on calendar import. The gateway and login flow are being built first so that later Home Assistant entities can depend on a real authenticated Vklass session rather than external cookie workarounds.

## Lovelace auth card resource loading

The integration includes the `vklass-auth-card` Lovelace card.

If your Home Assistant Lovelace resources are managed in storage mode, the card resource can be registered automatically by the integration.

If your Lovelace resources are managed in YAML mode, you must add the card resource explicitly in your Lovelace YAML configuration, just like other custom Lovelace resources such as `layout-card.js`.

Example:

```yaml
resources:
  - url: /vklass/vklass-auth-card.js?v=0.25
    type: module
```
