DOMAIN = "vklass"
AUTH_COOKIE_FROM_RESTAPI = "restAPI" # requires user to setup a restapi entity that can be queried for an auth cookie, vklass integration calls VklassGateway::SetCookie() with the rest call result
AUTH_COOKIE_FROM_LOGIN = "login"
AUTH_COOKIE_FROM_FILE = "file"
AUTH_COOKIE_FROM_HAAPI = "ha_api"
COOKIE_FILE_TYPE_CHROMIUM = "chromium"
COOKIE_FILE_TYPE_FIREFOX = "firefox"


VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD     = "cookie_retrival_method"
VKLASS_CONFKEY_ASYNC_COOKIE_CB            = "async_cookie_cb"
VKLASS_CONFKEY_USERNAME                   = "username"
VKLASS_CONFKEY_PASSWORD                   = "password"
VKLASS_CONFKEY_COOKIEFILE                 = "cookie_file"
VKLASS_CONFKEY_COOKIEFILE_TYPE            = "cookie_file_type"
VKLASS_CONFKEY_KEEPALIVE_MIN              = "keepalive_minutes"
VKLASS_ASYNC_ON_AUTH_FAIL_CB              = "async_on_auth_fail_cb"
VKLASS_ASYNC_ON_AUTH_COOKIE_UPDATE        = "async_on_auth_cookie_update_cb"


VKLASS_COOKIE_RETRIVAL_METHOD_MANUAL   = "manual"
VKLASS_COOKIE_RETRIVAL_METHOD_FUNCTION = "callback"
VKLASS_COOKIE_RETRIVAL_METHOD_FILE     = "file"
VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN    = "login"

VKLASS_CONFKEY_COOKIEFILE_TYPE_CHROMIUM = "chromium"
VKLASS_CONFKEY_COOKIEFILE_TYPE_FIREFOX  = "firefox"
