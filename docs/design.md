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
* The gateway may still observe and propagate updated auth cookies received from Vklass responses, but cookie import is not a supported primary auth method
* The session keepalive is part of the login/session lifecycle, not something entities manage individually
* Entities consume gateway data only and should not know how login works

`binary_sensor.vklass_<name>_loggedin` represents session state. Login state and keepalive are handled independently of calendar entities. Vklass should be touched regularly to keep the session alive, while other entities should stay focused on their own data refresh responsibilities.

## Authentication design
Login is handled through real Vklass-supported authentication methods owned by the gateway.

### Username and password
* Config flow option: `Username/Password`
* The user provides credentials in the config flow
* Authentication is handled fully inside the gateway

### BankID
Most districts primarily use BankID for guardians. The design target is to execute the real BankID flow inside the integration and session instead of asking the user to retrieve browser cookies externally.

#### BankID QR flow
* Config flow option: `BankID QR`
* The user provides the district-specific auth start URL, for example an organisation login entry under `auth.vklass.se`
* The gateway loads the login page, follows the BankID path, parses the SAML handoff, extracts the BankID `aid`, fetches QR payloads, and polls status until success or failure
* QR content is surfaced to Home Assistant through an async callback so the UI can show the currently valid QR code
* When BankID completes successfully, the auth handshake continues in the same `aiohttp` session until the required Vklass cookies are established

#### BankID personal number flow
* Config flow option: `BankID Personal Number`
* The user provides the district-specific auth URL and personal number
* The gateway performs the same core auth sequence but uses the personal-number variant where supported

### Unsupported approach for version 1.0
The following is no longer part of the active design:
* Reading browser cookie files
* Manual cookie paste helpers
* External REST APIs that return cookies
* Home Assistant API endpoints for pushing plaintext cookies into the gateway

If Vklass or district-specific behavior later forces a fallback strategy, it should be treated as a new design decision rather than assumed as part of the main architecture.

## Home Assistant integration
* Full Home Assistant integration with entities tied to a device
* Config flow
* Vklass device
* Vklass authenticated binary sensor
* Vklass calendar entities, split by student and later by event type as designed
* UI support for BankID login interaction, primarily QR presentation and login-state feedback

## Vklass calendar raw example
After successful login, the full calendar can be retrieved via:

`https://custodian.vklass.se/Events/FullCalendar`

The request is authenticated by the session established through the gateway login flow. The calendar payload contains mixed event types and student contexts that later gateway layers can normalize into Home Assistant-friendly structures.
