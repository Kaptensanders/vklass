# Vklass implementation roadmap for version 1.0

## Roadmap rules
* Work on current milestone, subtasks, until finished. Do not start next step until current is stable and prodution grade
* Completion of a milestone means it is production grade code
* Milestones must not be worked on unless it is marked Status: In progress

## Milestones:

### 1. Setup project structure
Status: **Finished**
* vklass repository
* devcontainer
* folder strucure and stub files

### 2. The VklassGateway Componant - fundamentals
Status: **In Progress**
    * basic logic and structure of the gateway componant in /custom_componants/vklass/vklassgateway.py
    * auth cookie renewal flow (in progress). AUTH_COOKIE_FROM_RESTAPI method only
        * auth cookie callback function
        * direct setCookies function
    * dynamic cookie updates from vklas responce
    * robust vklass content fetching (class VklassSession) with robust error and auth handling
    * basic but stable raw calendar retrieval

### 3. The VklassGateway Componant - completion and refinement
Status: **Pending**
* core functionality of the gateway componant in /custom_componants/vklass/vklassgateway.py
    * convert vklass calendar event entries into conventional calendar entry format
    * auth cookie renewal flow (in progress).
        * read cookie from browser cookie file
            * chromium
            * firefox
        * username / password

### 3. HA vklass integration
Status: **Pending**
* basic integration design
* config flow
* vklass device
* vklass authenticated binary_sensor (including UI card example for going to login page)
* vklass calendar entity, with calendar entities per student, and per eventtype separation of calendars
* input_text.vklass_<name>_cookie, for setting auth cookie manually (copy/paste). With UI card example
* Save auth cookies in HA storage, if exists on integration load, set with VklassGateway object SetCookie(), to persist HA restarts
