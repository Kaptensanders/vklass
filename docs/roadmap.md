# Vklass implementation roadmap for version 1.0

## Roadmap rules
* A milestone marked `Status: Current` is the active implementation focus
* A milestone marked `Status: In Progress` has been started and may continue to receive limited follow-up work while another milestone is `Current`
* Completion of a milestone means production-grade code
* A later milestone may be marked `Current` before an earlier milestone is completed when continued implementation is needed to understand, validate, or finish the earlier milestone
* At most one milestone should be marked `Status: Current` at a time
* Milestones must not be worked on unless marked `Status: Current` or `Status: In Progress`

## Milestones

### 1. Setup project structure
Status: **Finished**
* Vklass repository
* Devcontainer
* Folder structure and stub files

### 2. The VklassGateway component - fundamentals
Status: **Complete**
* Basic logic and structure of the gateway component in `custom_components/vklass/vklassgateway.py`
* Real authentication entry point in `VklassSession`
* Basic, but good foundation for auth adapter handling
* BankID QR flow foundation in `custom_components/vklass/login.py`
* BankID QR auth implementation for gothenburg in `custom_components/vklass/auth_adapters/goteborg_bankid.py`, working but not production grade for now
* Basic bankid qr code propagation through callback function
* Shared authenticated `aiohttp` session handling
* Dynamic auth-cookie updates from Vklass responses
* Robust Vklass content fetching in `VklassSession` with fail-fast auth and error handling
* Basic but stable raw calendar retrieval
* Student discovery and keepalive loop

### 3. Home Assistant Vklass integration, phase 1
Status: **Complete**
* **Home Assistant integration BASE** design implementation only
* Some stub code exist as example, design pattern guidance, replace with real implementation 
* (DONE) Basic robust integration design, shared vklassgateway and the Vklass device
* (DONE) Config flow for supporting auth methods (implied in const.py)
* The Vklass sensor for authentication
* Home Assistant presentation of BankID QR updates during login

### 4. Lovelace companion card for QR auth
Status: **Complete**
* according do design spec


### 5. Home Assistant Vklass integration, phase 2
Status: **Current**
* Vklass calendar entity, with calendar entities per student and later event-type separation


### 6. The VklassGateway component - completion and refinement
Status: **Pending**  
* better _step3_poll_qr status handling in goteborg_bankid.py when we can try better with the HA integration
* consistant and production grade handling of auth adapters. Documented and well designed. 
* Implement vklass BankID personal-number authentication (vklass_bankid.py)
* Implement vklass username/password authentication (vklass_userpass.py)
* Complete auth result propagation through callbacks for QR update and auth-failed state
* Convert raw Vklass calendar entries into conventional calendar entry format
* Validate district-specific auth URL handling and redirect behavior
