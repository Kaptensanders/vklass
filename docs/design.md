# This is the design document for vklass custom component for Home Assistant.

## Design and development rules
* Comply always to Home Assistant best practice and design patterns
* Avoid overengineering
* Assume a fail fast approach. Do not safeguard things that will have an obvious immediate effect, for example visible log errors or a crashing flow
* Prefer small, reviewable changes

## Project description
Vklass is the planning and parental communication tool used by many Swedish schools. This project is a Home Assistant custom component that reads calendar data from Vklass and exposes it in Home Assistant.

Version 1.0 is calendar-focused. The component may later be extended with more Vklass data, but calendar import is the only scope for the current design.

## High level architecture
* Full Home Assistant integration, with config flows and entities mapped to a device
* All entities follow the `<type>.vklass_<device name>_<property>` pattern
* Translations for Swedish and English
* `VklassGateway` is the central Vklass communication gateway and must remain completely Home Assistant independent
* The gateway is designed as a standalone Python component that can run outside Home Assistant

## Main project structure and design
* `custom_components/vklass/` contains the Home Assistant integration implementation and the Home Assistant independent gateway module
* Consumers such as calendar entities never handle the Vklass web interface directly. They use only `VklassGateway`

## vklassgateway module (`custom_components/vklass/vklassgateway.py`)
* The gateway module shall be standalone Python and must not depend in any way on Home Assistant
* It exports `VklassGateway`
* `VklassGateway` is the API surface and contains only methods for fetching and managing Vklass content
* `VklassGateway` derives from `VklassSession`, which handles generic session lifecycle, authentication, keepalive, and HTTP communication
* `VklassGateway` should not perform raw web-flow logic directly when the base session class can own it

## Session and authentication model
* `VklassSession` owns the authenticated `aiohttp` session
* Authentication happens inside the integration and inside the shared session, not by importing cookies from an external source
* Successful authentication must leave the required Vklass cookies in the `aiohttp` cookie jar used by later data requests
* Authentication support is adapter-driven. The gateway selects an auth adapter by matching the configured auth URL against available modules in `custom_components/vklass/auth_adapters/`
* An authentication method is considered supported only when a compatible auth adapter exists and can handle the configured auth URL
* The gateway may still observe and propagate updated auth cookies received from Vklass responses, but cookie import is not a supported primary auth method
* The session keepalive is part of the login/session lifecycle, not something entities manage individually
* Entities consume gateway data only and should not know how login works

`binary_sensor.vklass_<name>_loggedin` represents session state. Login state and keepalive are handled independently of calendar entities. Vklass should be touched regularly to keep the session alive, while other entities should stay focused on their own data refresh responsibilities.

## Authentication design
Login is handled through real Vklass-supported authentication methods owned by the gateway.

### Adapter-based auth detection
* The primary auth input is a district-specific auth URL
* `login.py` discovers available auth adapters from `custom_components/vklass/auth_adapters/`
* At runtime, the gateway selects the first adapter whose `can_handle(url)` matches the configured auth URL
* The auth URL therefore determines both the login flow and which input fields are relevant for that flow
* If no adapter matches the URL, authentication fails immediately

### Supported authentication methods
Supported methods are not defined by a fixed global list. They are defined by the set of compatible auth adapters present in the codebase.

Current design examples:
* BankID QR is supported when a matching adapter exists for the configured auth URL, for example the Göteborg-specific BankID QR flow
* Username/password is supported only for auth URLs handled by a compatible username/password adapter
* BankID personal number is supported only for auth URLs handled by a compatible personal-number adapter

### BankID QR flow
Most districts primarily use BankID for guardians. Where a compatible adapter exists, the design target is to execute the real BankID flow inside the integration and shared session instead of asking the user to retrieve browser cookies externally.

The gateway adapter may:
* Load the district login page
* Follow the BankID path and any district-specific SAML or redirect handoff
* Extract the BankID session identifiers needed for QR/status polling
* Surface QR content through an async callback so the UI can show the currently valid QR code
* Continue the handshake in the same `aiohttp` session until the required Vklass cookies are established

### Other authentication flows
Other flows such as username/password or BankID personal number follow the same design principle:
* The flow is owned by the gateway
* Required user inputs come from integration configuration
* Compatibility is determined by whether an auth adapter exists for the supplied URL
* Success means the shared `aiohttp` session ends up with the required Vklass auth cookies

### Unsupported approach for version 1.0
The following is no longer part of the active design:
* Reading browser cookie files
* Manual cookie paste helpers
* External REST APIs that return cookies
* Home Assistant API endpoints for pushing plaintext cookies into the gateway
* Declaring auth support independently of the configured auth URL and installed auth adapters

If Vklass or district-specific behavior later forces a fallback strategy, it should be treated as a new design decision rather than assumed as part of the main architecture.


## Home Assistant integration
* Full Home Assistant integration with entities tied to a device
* Config flow supporting config.py implied settings/keys
* Vklass device
* Vklass authenticated binary sensor, reflecting the current auth state. The binary_sensor implementation should also hold the qr_update_cb function, and the function should update the "qr_code" attribute then qr_update_cb function is called.
* Vklass calendar entities, split by student and later by event type as designed
* UI support for BankID login interaction, primarily QR presentation and login-state feedback


