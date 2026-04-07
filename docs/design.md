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
* The gateway uses its own `aiohttp.ClientSession` instead of Home Assistant's shared session
* Authentication happens inside the integration and inside that gateway-owned session, not by importing cookies from an external source
* Successful authentication must leave the required Vklass cookies in the `aiohttp` cookie jar used by later data requests
* Authentication support is adapter-driven. The gateway selects an auth adapter by matching the configured auth URL against available modules in `custom_components/vklass/auth_adapters/`
* An authentication method is considered supported only when a compatible auth adapter exists and can handle the configured auth URL
* The gateway may still observe and propagate updated auth cookies received from Vklass responses, but cookie import is not a supported primary auth method
* The session keepalive is part of the login/session lifecycle, not something entities manage individually
* Entities consume gateway data only and should not know how login works
* The gateway session may use auth-specific transport settings when district login stacks require browser-sensitive behavior

## Authentication design
Login is handled through real Vklass-supported authentication methods owned by the gateway.

### Adapter-based auth detection
* The primary auth input is a district-specific auth URL
* `login.py` discovers available auth adapters from `custom_components/vklass/auth_adapters/`
* At runtime, the gateway selects the first adapter whose `can_handle(url)` matches the configured auth URL
* The auth URL therefore determines both the login flow and which input fields are relevant for that flow
* If no adapter matches the URL, gateway-driven authentication fails immediately and the integration falls back to the manual-cookie path

### Supported authentication methods
Supported methods are not defined by a fixed global list. They are defined by the set of compatible auth adapters present in the codebase.

Current design examples:
* BankID QR is supported when a matching adapter exists for the configured auth URL, for example the Göteborg-specific BankID QR flow
* Username/password is supported only for auth URLs handled by a compatible username/password adapter
* BankID personal number is supported only for auth URLs handled by a compatible personal-number adapter

### BankID QR flow
Most districts primarily use BankID for guardians. Where a compatible adapter exists, the design target is to execute the real BankID flow inside the integration and the gateway-owned session instead of asking the user to retrieve browser cookies externally.

The gateway adapter may:
* Load the district login page
* Follow the BankID path and any district-specific SAML or redirect handoff
* Extract the BankID session identifiers needed for QR/status polling
* Surface QR content through an async callback so the UI can show the currently valid QR code
* Continue the handshake in the same `aiohttp` session until the required Vklass cookies are established

### Aiohttp transport requirements
Some district auth stacks are incompatible with `aiohttp`'s default cookie quoting. The Göteborg BankID flow is a confirmed example.

Proof:
* The same live `wssoi` session values succeed when replayed with browser or curl cookie formatting
* The same live values fail when replayed with `aiohttp`'s default quoted cookie formatting
* A raw one-off `wssoi` request with unquoted browser-shaped cookies succeeds and reaches the expected Göteborg IdP redirect

Required solution:
* The gateway-owned `aiohttp` session must use `CookieJar(quote_cookie=False)`
* Signed redirect flows must preserve raw redirect URLs, so the gateway session must keep `requote_redirect_url=False`
* These transport settings belong to the gateway-owned session and must not depend on mutating Home Assistant's shared session

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


## Home Assistant integration BASE
* Full Home Assistant integration with entities tied to a device
* Config flow supporting config.py implied settings/keys
* Vklass device
* Integration should supply a function for the VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE config entry, that serializes updated auth cookies to HA's storage
* Integration shall restore latest saved auth cookie from HA storage on HA restart/load using VklassGateWay.setAuthCookie  
* expose vklass.set_auth_cookie as service (calling VklassGateway.setAuthCook())
* expose vklass.authenticate as service (calling VklassGateway.authenticate())
* create a sensor.vklass_<name>_auth sensor, reflecting the current auth state.
  * Sensor state in inprogress|success|fail (const.AUTH_STATUS_XX)
  * Sensor should hold the QR code callback function used in auth adapters. Function shall update qr_code attribute
  * Sensor shall hold the auth_status callback function used by VklassGateway.authenticate to communicate state and message.
  * Attributes:
    * auth url (as set in config flow)
    * auth_method - from VklassGateway.getAuthMethod()
    * auth_interactive - from VklassGateway.getAuthMethod(), informational metadata for current and future UI use
    * qr_code - exist only after callback function set's it
    * message - auth error if
    * last_success - last successful authentication

## Home Assistant integration EXTENDED
* Vklass calendar entities, split by student and later by event type as designed

## Lovelave companion card for vklass authentication
* card in custom_components/vklass/frontend/vklass-auth-card.js
* auto registered and injected as a frontend resource at integration init
* card is configured with an auth sensor entity. The entity's `auth_method` attribute decides the behaviour of the card. The entity also exposes `auth_interactive` as informational metadata for current and future UI use. (see const.py `AUTH_METHOD_<...>` for possible values)
* raw `qr_code` sensor data is passed unchanged from the gateway. The integration/card layer is responsible for rendering that raw payload as a visible QR image
  
  * auth_method=AUTH_METHOD_BANKID_QR and state=
    * fail - display button with "Logga in i Vklass"
    * success - display text "Vklass logged in", and show a logout button that calls the vklass logout service
    * inprogress - 
      * display text: "Scanna med BankID appen"
      * render qr code from auth sensor, update image when code renews
    * When "Logga in i Vklass" button is pressed the card should render a spinner instead of the button util the state changes to inprogress. 

  * auth_method=AUTH_METHOD_MANUAL_COOKIE and state=
    * fail - 
      * display text: "Login to Vklass with browser and paste value of se.vklass.authentication cookie here"
      * display text input field for cookie pasting.
      * display login button - calls vklass.set_auth_cookie service
    * success - display text "Vklass logged in"

* if auth entity state is "success", display logout button (calling vklass logout service)
