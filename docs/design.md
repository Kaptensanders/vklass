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
* Authentication happens inside the integration and inside that gateway-owned session
* Successful authentication must leave the required Vklass cookies in the `aiohttp` cookie jar used by later data requests
* Authentication support is adapter-driven. The integration selects one auth adapter from the adapters exposed by `custom_components/vklass/auth_adapters/`
* The selected adapter is stable configuration. Adapter-specific credentials are runtime auth input
* Manual cookie authentication remains supported, but as a normal auth adapter rather than a special backend API
* The session keepalive is part of the login/session lifecycle, not something entities manage individually
* Entities consume gateway data only and should not know how login works
* The gateway session may use auth-specific transport settings when district login stacks require browser-sensitive behavior

## Authentication design
Login is handled through real Vklass-supported authentication methods owned by the gateway.

### Public and internal gateway API
* `VklassGateway.login(credentials=None, reuse_credentials=False)` is the public authentication API used by consumers
* `credentials` is optional and adapter-specific runtime auth input
* `reuse_credentials=True` means the supplied credentials may remain seeded in gateway memory for bounded automatic re-authentication
* `VklassSession._authenticate(...)` is internal gateway logic and not part of the consumer API
* Successful login must be validated by a real authenticated Vklass request, not only by checking whether an auth cookie exists

### Supported authentication methods
Supported methods are adapter-driven. The selected adapter declares which auth method it implements.

Current design examples:
* BankID QR through a district-specific adapter, for example the Göteborg-specific guardian flow
* Username/password through an adapter that supports it
* BankID personal number through an adapter that supports it
* Manual cookie through an adapter that accepts the Vklass auth cookie as runtime input

### BankID QR flow
Most districts primarily use BankID for guardians. Where a compatible adapter exists, the design target is to execute the real BankID flow inside the integration and the gateway-owned session.

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
* Required user inputs are runtime credentials supplied by the consumer
* Compatibility is determined by the selected adapter
* Success means the shared `aiohttp` session ends up with the required Vklass auth cookies

### Re-authentication model
* `VklassGateway` owns authentication mechanics, session lifecycle, keepalive, auth-cookie/session state, and bounded re-authentication attempts
* The gateway may only perform automatic re-authentication when reusable credentials have already been seeded in memory by a consumer through `login(..., reuse_credentials=True)`
* The gateway does not persist credentials, cookies, or auth data
* Consumers such as Home Assistant own persistence, restore-on-startup, reseeding, and UI behavior
* If no reusable in-memory credentials exist, or if re-authentication with seeded credentials fails, the gateway raises an authentication failure and the consumer decides how to recover
* Explicit logout is treated as a clear user intent to fully sign out. Home Assistant must clear persisted credentials and persisted auth cookie for that entry when logout is requested
* After explicit logout, no automatic session resume or automatic login may happen until the user explicitly logs in again

### Runtime credential shapes
The public `login()` API accepts adapter-specific runtime credentials.

Current design shapes:
* `AUTH_METHOD_BANKID_QR`: `credentials=None`
* `AUTH_METHOD_BANKID_PERSONNO`: `{"personno": "<personal number>"}`
* `AUTH_METHOD_USERPASS`: `{"username": "<username>", "password": "<password>"}`
* `AUTH_METHOD_MANUAL_COOKIE`: `{"cookie": "<cookie value>"}`

### Unsupported approach for version 1.0
The following is no longer part of the active design:
* Auth URL based adapter lookup
* `set_auth_cookie` as a separate gateway or Home Assistant API
* Reading browser cookie files
* External REST APIs that return cookies
* Declaring auth support independently of the selected auth adapter

If Vklass or district-specific behavior later forces a fallback strategy, it should be treated as a new design decision rather than assumed as part of the main architecture.


## Home Assistant integration BASE
* Full Home Assistant integration with entities tied to a device
* Config flow supporting config.py implied settings/keys
* Vklass device
* Config flow selects the auth adapter and other stable settings only. It must not ask for credentials
* Integration may persist reusable credentials and cookies in Home Assistant storage and restore them on startup by calling `VklassGateway.login(..., reuse_credentials=True)`
* expose `vklass.authenticate` as service, implemented as a call to `VklassGateway.login(...)`
* expose `vklass.logout` as service, implemented as a call to `VklassGateway.logout()`
* `vklass.logout` must also clear persisted credentials, persisted auth cookie, and persistence preference for that entry in Home Assistant storage
* Home Assistant runtime auth state is the authoritative integration state for gating entity updates and auth-related recovery decisions
* create a sensor.vklass_<name>_auth sensor, reflecting the current auth state.
  * Sensor state in inprogress|success|fail (const.AUTH_STATUS_XX)
  * Sensor should hold the QR code callback function used in auth adapters. Function shall update qr_code attribute
  * Sensor shall hold the auth_status callback function used by `VklassGateway.login()` to communicate state and message
  * The auth sensor reflects runtime auth state for UI and debugging only. Other entities must not depend on the auth sensor entity state as their coordination mechanism
  * Attributes:
    * auth_adapter - selected adapter key
    * auth_method - auth method of selected adapter
    * qr_code - exist only after callback function set's it
    * message - latest auth status message
    * last_success - last successful authentication
    * username - persisted username if present
    * personno - persisted personal number if present
    * persisted_password - boolean
    * persisted_cookie - boolean
    * save_credentials - current persistence preference

## Home Assistant integration EXTENDED
* Vklass calendar entities, split by student and later by event type as designed
* Entities must remain focused on their own domain behavior and must not contain auth-method-specific logic
* Before a gateway read, entities should ask a Home Assistant owned runtime policy helper whether update/fetch is currently allowed
* That policy helper may consult Home Assistant runtime auth state together with narrow gateway capability methods, but must not require entities to reason about auth methods or interactive flows
* Background entity updates must never trigger interactive authentication
* Expected unauthenticated states should be handled quietly by skipping update/fetch without noisy error logging. When an exception is logged, it should represent a real unexpected failure worth investigation

## Lovelave companion card for vklass authentication
* card in custom_components/vklass/frontend/vklass-auth-card.js
* auto registered and injected as a frontend resource at integration init
* card is configured with an auth sensor entity. The entity's `auth_method` attribute decides the behaviour of the card. The entity's `auth_adapter` attribute is available for debugging and future adapter-specific UI use
* raw `qr_code` sensor data is passed unchanged from the gateway. The integration/card layer is responsible for rendering that raw payload as a visible QR image
* when auth fields are shown, the card should always show the `save credentials` checkbox
* real persisted secrets must never be exposed to the card through sensor attributes
* for persisted password or cookie fields, the card uses the sentinel value `__PERSISTED_SECRET__`
* if the submitted password or cookie field still equals `__PERSISTED_SECRET__`, the backend must replace it with the persisted secret before calling `VklassGateway.login(...)`
  
  * auth_method=AUTH_METHOD_BANKID_QR and state=
    * fail - display button with "Logga in i Vklass"
    * success - display text "Vklass logged in", and show a logout button that calls the vklass logout service
    * inprogress - 
      * display text: "Scanna med BankID appen"
      * render qr code from auth sensor, update image when code renews
    * When "Logga in i Vklass" button is pressed the card should render a spinner instead of the button util the state changes to inprogress

  * auth_method=AUTH_METHOD_BANKID_PERSONNO and state=fail
    * display personal number input
    * if a personal number is already persisted, prefill that field
    * display `save credentials` checkbox
    * display login button - calls `vklass.authenticate`

  * auth_method=AUTH_METHOD_USERPASS and state=fail
    * display username and password fields
    * if a username is already persisted, prefill that field
    * if a password is already persisted, prefill the password field with `__PERSISTED_SECRET__`
    * display `save credentials` checkbox
    * display login button - calls `vklass.authenticate`

  * auth_method=AUTH_METHOD_MANUAL_COOKIE and state=fail
    * display text: "Login to Vklass with browser and paste value of se.vklass.authentication cookie here"
    * display cookie input field
    * if a cookie is already persisted, prefill the field with `__PERSISTED_SECRET__`
    * display `save credentials` checkbox
    * display login button - calls `vklass.authenticate`

  * auth_method in (`AUTH_METHOD_BANKID_PERSONNO`, `AUTH_METHOD_USERPASS`, `AUTH_METHOD_MANUAL_COOKIE`) and state=success
    * display text "Vklass logged in"

  * auth_method in (`AUTH_METHOD_BANKID_PERSONNO`, `AUTH_METHOD_USERPASS`, `AUTH_METHOD_MANUAL_COOKIE`) and state=fail after explicit logout or failed auth
    * render the fields again so the user can re-authenticate
    * if persisted values exist, the user should be able to press the login button directly without retyping unchanged secrets

* if auth entity state is "success", display logout button (calling vklass logout service)
