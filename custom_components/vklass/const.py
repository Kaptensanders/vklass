DOMAIN = "vklass"
VERSION = "0.25"

HA_ENTITYNAME_AUTH = "Vklass Authentication"

# config flow settings
VKLASS_CONFKEY_NAME             = "name"
VKLASS_CONFKEY_KEEPALIVE_MIN    = "keepalive_minutes"
VKLASS_CONFKEY_AUTHADAPTER      = "authadapter"

VKLASS_CREDKEY_USERNAME         = "username"
VKLASS_CREDKEY_PASSWORD         = "password"
VKLASS_CREDKEY_PERSONNO         = "personno"
VKLASS_CREDKEY_COOKIE           = "cookie"

# async notification handler function keys
VKLASS_HANDLER_ON_AUTH_EVENT                = "on_auth_event"           # async def mycallback(state:str, message:str) 
VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE         = "on_authcookie_update"    # async def mycallback(cookie_value:str)
VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE        = "on_qrcode_update"        # async def mycallback(qr_code:str)

# config entry / runtime keys
CONF_SAVE_CREDENTIALS                       = "save_credentials"         # True/False if method requires personel number, or username/password, but user may not want HA to save it. Manual input in the card instead for each auth, if False
DEFAULT_KEEPALIVE_MINUTES                   = 10
DATA_GATEWAY                                = "gateway"
DATA_AUTH_STATE                             = "auth_state"
DATA_AUTH_STATUS                            = "auth_status"
DATA_CALLBACKS                              = "callbacks"
DATA_SERVICES_REGISTERED                    = "services_registered"
DATA_CONFIG_STORE                           = "config_store"
STORAGE_KEY                                 = "vklass"
STORAGE_VERSION                             = 1

# service keys
SERVICE_LOGIN                               = "login"
SERVICE_LOGOUT                              = "logout"

AUTH_STATUS_INPROGRESS = "inprogress"
AUTH_STATUS_SUCCESS = "success"
AUTH_STATUS_FAIL = "fail"

AUTH_METHOD_BANKID_QR = "bankid_qr"
AUTH_METHOD_BANKID_PERSONNO = "bankid_personno"
AUTH_METHOD_USERPASS = "userpass"
AUTH_METHOD_MANUAL_COOKIE = "manual_cookie"

AUTH_ADAPTER_ATTR_NAME              = "name"
AUTH_ADAPTER_ATTR_TITLE             = "title"
AUTH_ADAPTER_ATTR_METHOD            = "method"
AUTH_ADAPTER_ATTR_MODULENAME        = "module"
AUTH_ADAPTER_ATTR_AUTH_FUNCTION     = "authFn"

VKLASS_URL_BASE     = "https://custodian.vklass.se"
AUTH_COOKIE_NAME    = "se.vklass.authentication"
AUTH_COOKIE_DOMAIN  = ".vklass.se"

PERSISTED_SECRET_SENTINEL = "__PERSISTED_SECRET__"

VKLASS_CONTEXT_USER = "user"
VKLASS_CONTEXT_SCHOOL = "school"
VKLASS_CONTEXT_STUDENTS = "students"
