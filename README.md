![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=)
![Version](https://img.shields.io/github/v/release/Kaptensanders/vklass)
# VKLASS integration for HomeAssistant

This integration imports your Vklass calendar events into Home Assistant

## Authenticating VKLASS

VKlass has two auth modes:

### Username and password
If this is the way you login, then you are in luck, just provide it when in the config flow.
You can reconfigure later yf you change password

### BankID
This is the tricky part. BankId login cannot be automated, so you need to login manually. The integration will keep the vklass session alive for you, so hopefully you dont need to login that often.
An enity - `binary_sensor.vklass_<name>_loggedin` - will let you know when you need to login again.<br>
#### Anyway, this needs to happen:
* You login using bankid -> end up in vklass
* The login cookie/auth information needs to be accessible in HomeAssistant

#### And this can happen in the following ways:
*   ***Direct access to the browser cookies***
    <br>Eg, HA is running on the host where you logged in with the browser.
    <br>In config flow select, "Host cookie access", and provice the path to the cookies file.
    ```
    /home/olle/.config/chromium/Default/Cookies
    /home/olle/.config/google-chrome/Default/Cookies
    /home/olle/.config/microsoft-edge/Default/Cookies
    ```
    Or whatever. And make sure the file is accessible to the user running Home Assistant.
    <br>
    ....or
    <br>

    If you are running **HA as container**, just mount the cookie file like <br>
    ```
        volumes:
        - /home/olle/.config/chromium/Default/Cookies:/config/vklasscookie/Cookies:ro
    ```
    and provide `/config/vklasscookie/Cookies`<br>
    <br>

*   ***The HA host is running headless***
    <br>Here you have the following conflig flow options:
    * *Manual Cookie Paste* - keep pasting the cookie content from browser (dev tools / cookie extention, etc) into `input_text.vklass_<name>_cookie` helper entity.
    * *Rest API* - provide some `https://getmyvklasscookie` that can be queried for the cookie.
    * *POST /api/vklass/set_cookie" - Push the cookie via HA API

<br>
Although there is some pain involved, this should allow you a way forward whatever infrastructure you have.
