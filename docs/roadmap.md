# Vklass implementation roadmap for version 1.0

## Roadmap rules
* Work on the current milestone until it is finished. Do not start the next milestone until the current one is stable and production grade
* Completion of a milestone means production-grade code
* Milestones must not be worked on unless marked `Status: In progress`

## Milestones

### 1. Setup project structure
Status: **Finished**
* Vklass repository
* Devcontainer
* Folder structure and stub files

### 2. The VklassGateway component - fundamentals
Status: **In Progress**
* Basic logic and structure of the gateway component in `custom_components/vklass/vklassgateway.py`
* Real authentication entry point in `VklassSession`
* BankID QR flow foundation in `custom_components/vklass/login.py`
* Shared authenticated `aiohttp` session handling
* Dynamic auth-cookie updates from Vklass responses
* Robust Vklass content fetching in `VklassSession` with fail-fast auth and error handling
* Basic but stable raw calendar retrieval
* Student discovery and keepalive loop

### 3. The VklassGateway component - completion and refinement
Status: **Pending**
* Complete the real BankID QR implementation
* Implement BankID personal-number authentication
* Implement username/password authentication
* Complete auth result propagation through callbacks for QR update and auth-failed state
* Convert raw Vklass calendar entries into conventional calendar entry format
* Validate district-specific auth URL handling and redirect behavior

### 4. Home Assistant Vklass integration
Status: **Pending**
* Basic integration design
* Config flow for selecting auth method and required input values
* Vklass device
* Vklass authenticated binary sensor with UI support for login status
* Home Assistant presentation of BankID QR updates during login
* Vklass calendar entity, with calendar entities per student and later event-type separation
