# This is the design document for vklass custom componant for Home Assistant. 

## Design and development rules
* Comply always to Home Assistant best practice and design patterns
* Avoid overengineering
* Assume a fail fast approact. Do not safeguard things that will have an obvious immmidiate effect. Eg shown in logs or otherwise crashing visibly.
* Do not overengineer


## Project Description
Vklass is the planning and parental communication tool for many swedish schools. It contains among other things calendars for homework and other plannings. We are creating a Home Assistant custom componant that reads the calander in vklass and populates thoas events in Home Assistant.
The component can be extended later to allow also retrival of other things, but version 1.0 is for calendar only.


## Hight level architecture

- Full blown HA integration, with config flows and entities mapped to a device.
- All entities follow the <type>.vklass_<device name>_<property> pattern
- Translations for Swedish and English 
- The VklassGateway componant is the central vklass communication gateway. It must be kept completly HomeAssistant independant
- We design this with a standalone core componant that can be run outside Home Assistant. class . 


# Main project structure & design
- `custom_components/vklass/`: Contains the Home Assistant integration implementation, as well as the HA independant python module vklassgateway.py.
- consumers such as calendar entity implementation, never handles the vklass interface directly. It uses only the VklassGateway as interface.





## vklassgateway module (custom_components/vklass/vklassgateway.py)
- the vklassgateway shall be a standalone python module, and must not depend in any way on HomeAssistant
- exports VklassGateway class
- VklassGateway is API and contains only methods for fetching and managing content
- VklassGateway derives from VklassSession, that handles all generic session and vklass communication.
- VklassGateway should not do calls directly to vklass site, it should use base class functionality
- gateway.py should be considered standalone python, and must not depend in any way on HomeAssistant





* vklass calendar entity, with calendar entities per student, and per eventtype separation of calendars

´binary_sensor.vklass_<name>_loggedin´ holds the logged in state. Login entity state should be an entity independant process, that also serves as the keep-alive functionality for the session. vklass should be queried at least every 20 mins. Other entities, like calendar, should not 


* VklassSession maintains the connection to vklass, handles login, handles session keepalive, and exposes api_call() for consumer entities.


### vklass authentication/login design
Login is handled via BankId or Username/Password. Most districts only allows BankID. 

#### *Username/Password*
*   Config flow option: `Username/Password` - Input fields for Username/Passwork. Auth is handled within the custom component

#### *BankID*
* Login as "vårndnadshavare" is done via (ex) "Göteborgs Stad UBF", eg https://auth.vklass.se/organisation/189
* After browser login, the cookies "se.vklass.authentication" and "vhvklass.ASPXAUTH" can be used to request data from vklass.
* We accept that user needs to sometimes re-login, and that this requires manual interraction. Manual interraction should be simplified as much as possible.


#### Supported methods to get browser cookies after BankID login

*   Config flow option: `Direct access to the browser cookies` - Eg we read the browser coockie file directly. Filepath specified in text field, browser type as dropdown selection field. 
    Set by calling VklassGateway::SetCookies()
*   Config flow option: `Manual Cookie Paste` - The integrations helper entity `input_text.vklass_<name>_cookie` contains cookies (plain text), probably pasted from browser devtools etc
*   Config Option: `Rest API` - user provide some `https://getmyvklasscookie` api that can be queried for the plaintext cookies
*   Config flow option: `HA API` - Users pushes plaintext cookies via 
    ```
    -POST /api/vklass/set_cookie"
    {vklass_name:"<vklass device name>", cookies="<plaintext>"}
    ```
    Set from ha api by calling VklassGateway::SetCookies()


### 3. HA vklass integration
- Full HA integration with entities tied to a device
- config flow
- vklass device
- vklass authenticated binary_sensor (including UI card example for going to login page)
- vklass calendar
    * calendars split per student -> eventtype
- input_text.vklass_<name>_cookie, for setting auth cookie manually (copy/paste).



## Vklas calendar - raw example

After login, the full calendar can be retrieved via
`https://custodian.vklass.se/Events/FullCalendar`

**Request headers**:
```
:authority:             custodian.vklass.se
:method:                POST
:path:                  /Events/FullCalendar
:scheme:                https
accept:                 */*
accept-encoding:        gzip, deflate, br, zstd
accept-language:        sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6
content-length:         103
content-type:           application/x-www-form-urlencoded
cookie:    
se.vklass.authentication=CfDJ8AF1v64zmWNJt9xTu8U9aMqsWQjekSg6WEBEjG8iZBKGZW4fut521u8VCunV-TilotM3kFLyakz7KlmEN9mGLT8dAbAGBI0U3KiSjLMTILoMCXkyPeEflgYax1rEdkXHeb7jJGtT9jowSm7Ez9I9LooVFUQhEsXHNEwilAo3izK0baDNsT2cxpSHPpjpghXJdcXMbkU_q3xFSRqFUEYSgR8nV0KC7n1aG76rlLAuwt2-CJcXV_NB_Kpqwlhfhi-nPlKpiAC5vVoutnU5fV6G1PKimb-DcXc7nNEZHT9fUBs88mlW2aJBADjjO9M2oxHsmHAEaaJ2FuAbLz_skwCXBjeWr_wrfFBaaTwd6rvsVCdVJzP34_4LWqmdak874S3xFEJBDLZDvaGpjZEud02nioy4wK7u73evCstGh8bud_GLoBBgBFWNJ6prVy5Qpa1a83X8frNFRRWowNZ_qfB6HX81XLKS9JB2A3Me5uE4uR3alRfI3nmeCWbyjpu3NxP6wuNMLZwxM2JviX_44skConjAqhNYnm9wqdjQuR5DDXEnqESZYh0iuWLxF1rNkrQtP19V6XRqvDf5prHBJHkyTZKQXVbLn2vBt54QcrA19JxQJ9FpXlX-FCIS5CIDgKyYF3N53OHA11bwCLUQT1_0hJQkLGHgawh4wES3dX0ohFLQNfST09Wyg7I6v_L_cmnJJ2elib8esvedaQnSjtqVGsmRBcGcRnnf5QOA6wV-UA2ZBMAhmhDXW8iGCq0SG3gbGu6jNYpPl29frxKdvymDb3o61rf92TfQhmPvP7JID-Q-1j_2wmWGyeSVlNRdAFD6WcyfPvarfyha7b5Fkl8h2y2vvJSwXjUCVQdeb2Y1grWUKzbvs7n4OCFW2J3k3WYq53T98XhAqF5wBTLdLXzCxOJkl7-GytRhOYbUTFyj6s8NsgjcTIWsaLSfmNlA9ce30QSIajkbHvKV9jpmu6k9up-JVCSBAfwdfQaIimgv8H_rBIUKZ3DL3jZ6oworf__lYDPApOWVw1KKG-34ADBabXXwdHyoesfmvvxQAeLxFXN5J5rt1v2KkSmSEFuDgY7tVCEboaRm0CBrv20SU-Ttez03V-iTQPVmZmgwkuYGD8UR7dbRN5alMbYrVfT5dUAA6QqMD3VfshfpOEelABW5_8_uKwutUcyqkHsvSwpsYHcjWAQP-5eCWIs4xEC3Adfp55pLnXUEmU8AIvV2xOt_oMndTWq_MALyrH_l1yCKdMSbzm85nn28YWw9QcGZcxc9mujTtANm14iNcjgGwIXQLWjbI8fqkW4JP2z8IcjSuH1fAirG8dou3FpUoEM_oofAfWbeVX64SjnYKCAaZCi84qs0_dHvN6aOYRDyUgtnK05Bq05rjF_rtk3PbVorEg_xDraRoej5aNL37tuxAlUB9mt1gYWmHctLGfF-2B64jUqoIvoRIchkRHKP1bIcvilUof1PvBXB5TgJcIpHXJQbVf3WpmmTRsWwmxGQMkbYwDaBqA5WAbWKXqcxGsCyss9RbzyaeHaYuvdOS04FmP4W-qq2YXnSzQELNzNCeRF88hmva8oyf5zi_c9mETnFW-j1tfPSjFgHKqdvmjv7DseSmow; LogoutRedirectURL=%2Fsaml%2Fsignout; vhvklass.ASPXAUTH=8675068F73873988A02C7BAE113BFC76F21B953BF07A6AAFC1A94C036A57D38DC73D808DDCB24B85B7735D806A1F102605096BC107B887CBBB6B4629868572B8EAEA02F406486F0261AD2BE7CA5F8CAB78CFAD5DA72627D8A672D03199A131701B2D8E04EA636081229BE1D7BE1953BABF89ACBA830B311CE92C25304C9F6AFB4F0FAAD3; vk.vh.localization=c%3Dsv-SE%7Cuic%3Dsv-SE; vk-pointer=mouse
dnt:                    1
origin:                 https://custodian.vklass.se
priority:               u=1, i
referer:                https://custodian.vklass.se/
sec-ch-ua:              "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"
sec-ch-ua-mobile:       ?0
sec-ch-ua-platform:     "Windows"
sec-fetch-dest:         empty
sec-fetch-mode:         cors
sec-fetch-site:         same-origin
user-agent:             Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36
```

**Responce (snippets)**:
```
[
    {
        "id": null,
        "sortIndex": 0,
        "title": "Svenska (1B/SV)",
        "start": "2026-03-23 08:00",
        "end": "2026-03-23 09:20",
        "allDay": false,
        "context": "Matilda",
        "location": "",
        "text": "SV",
        "detailUrl": "/Calendar/Lecture/197099154",
        "eventType": 1,
        "subtype": 0,
        "showEventAsSubtype": false,
        "className": "vk-cl-event-lecture",
        "cancelled": false,
        "cancellingEnabled": true,
        "adminAccess": false,
        "attendanceRegistrationEnabled": false,
        "alertText": null,
        "alertUrl": null,
        "lectureId": null,
        "isSubstitute": false,
        "courseId": null
    },
    ...
    {
        "id": null,
        "sortIndex": 34,
        "title": "Läxa i matematik",
        "start": "2026-03-26 09:40",
        "end": null,
        "allDay": true,
        "context": "Knut",
        "location": "",
        "text": "<div style=\"font-size: 14px;\"><span style=\"color: rgb(74, 74, 74); font-family: Roboto, sans-serif; font-size: 14px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: 0.14px; orphans: 2; text-align: start; text-indent: 0px; text-transform: none; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; white-space: pre-line; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;\" id=\"isPasted\">9:ans multiplikationstabell. Efter genomförd läxa behöver eleverna träna på de tal som de tycker är svåra.</span></div>",
        "detailUrl": "/Calendar/Assignment/4681263",
        "eventType": 2,
        "subtype": 0,
        "showEventAsSubtype": false,
        "className": "vk-cl-event-assignment",
        "cancelled": false,
        "cancellingEnabled": true,
        "adminAccess": false,
        "attendanceRegistrationEnabled": false,
        "alertText": null,
        "alertUrl": null,
        "lectureId": null,
        "isSubstitute": false,
        "courseId": null
    },
    ...   
    {
        "id": null,
        "sortIndex": 35,
        "title": "1B/BIFYKE",
        "start": "2026-03-26 09:50",
        "end": "2026-03-26 10:35",
        "allDay": false,
        "context": "Matilda",
        "location": "",
        "text": "NO",
        "detailUrl": "/Calendar/Lecture/197376632",
        "eventType": 1,
        "subtype": 0,
        "showEventAsSubtype": false,
        "className": "vk-cl-event-lecture",
        "cancelled": false,
        "cancellingEnabled": true,
        "adminAccess": false,
        "attendanceRegistrationEnabled": false,
        "alertText": null,
        "alertUrl": null,
        "lectureId": null,
        "isSubstitute": false,
        "courseId": null
    },
    ...
