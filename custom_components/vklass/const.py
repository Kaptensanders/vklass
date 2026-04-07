DOMAIN = "vklass"
VERSION = "0.123"

HA_ENTITYNAME_AUTH = "Vklass Authentication"

# config flow settings
VKLASS_CONFKEY_NAME                         = "name"
VKLASS_CONFKEY_AUTH_URL                     = "auth_url"        # Auth starting point url
VKLASS_CONFKEY_USERNAME                     = "username"
VKLASS_CONFKEY_PASSWORD                     = "password"
VKLASS_CONFKEY_PERSONNO                     = "personno"
VKLASS_CONFKEY_KEEPALIVE_MIN                = "keepalive_minutes"

# async notification handler function keys
VKLASS_HANDLER_ON_AUTH_EVENT                = "on_auth_event"           # async def mycallback(state:str, message:str) 
VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE         = "on_authcookie_update"    # async def mycallback(cookie_value:str)
VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE        = "on_qrcode_update"        # async def mycallback(qr_code:str)

# config entry / runtime keys
CONF_UNSUPPORTED_AUTH_URL_ACTION            = "unsupported_auth_url_action"
CONF_ACTION_CONTINUE_MANUAL_COOKIE          = "continue_manual_cookie"
CONF_ACTION_EDIT_AUTH_URL                   = "edit_auth_url"
DEFAULT_KEEPALIVE_MINUTES                   = 10
DATA_GATEWAY                                = "gateway"
DATA_AUTH_STATE                             = "auth_state"
DATA_CALLBACKS                              = "callbacks"
DATA_SERVICES_REGISTERED                    = "services_registered"
DATA_CONFIG_STORE                           = "config_store"
STORAGE_KEY                                 = "vklass"
STORAGE_VERSION                             = 1

# service keys
SERVICE_AUTHENTICATE                        = "authenticate"
SERVICE_LOGOUT                              = "logout"
SERVICE_SET_AUTH_COOKIE                     = "set_auth_cookie"
SERVICE_ATTR_AUTH_COOKIE                    = "auth_cookie"

AUTH_STATUS_INPROGRESS = "inprogress"
AUTH_STATUS_SUCCESS = "success"
AUTH_STATUS_FAIL = "fail"

AUTH_METHOD_BANKID_QR = "bankid_qr"
AUTH_METHOD_BANKID_PERSONNO = "bankid_personno"
AUTH_METHOD_USERPASS = "userpass"
AUTH_METHOD_MANUAL_COOKIE = "manual_cookie"
