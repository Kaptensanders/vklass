DOMAIN = "vklass"

VKLASS_AUTH_USERNAME_PASSWORD   = "username_password"   # auth.vklass.se/credentials
VKLASS_AUTH_BANKID_QR           = "bankid_qr"           # bankid using QR code (mobile BankId app)
VKLASS_AUTH_BANKID_PERSONALNO   = "bankid_personalno"   # bankid using personal number

VKLASS_CONFKEY_AUTH_METHOD                  = "auth_method"     # VKLASS_CONFKEY_AUTH_METHOD: AUTH_COOKIE_FROM_RESTAPI | AUTH_COOKIE_FROM_LOGIN | AUTH_COOKIE_FROM_FILE | AUTH_COOKIE_FROM_HAAPI
VKLASS_CONFKEY_AUTH_URL                     = "auth_url"        # Auth starting point url 
VKLASS_CONFKEY_USERNAME                     = "username"
VKLASS_CONFKEY_PASSWORD                     = "password"
VKLASS_CONFKEY_PERSONNO                     = "personno"
VKLASS_CONFKEY_KEEPALIVE_MIN                = "keepalive_minutes"
VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE           = "async_on_qr_update_cb" # async callback function to notify when a new QR code is available, plaintext QR string as input parameter
VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB        = "async_on_auth_fail_cb"
VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE  = "async_on_auth_cookie_update_cb"

AUTH_ADAPTERS = {
    "auth.vklass.se/bankid":        "vklass_bankid.py",
    "auth.vklass.se/credentials":   "vklass_credentials.py",
    "authpub.goteborg.se":          "bankid_goteborg.py",
}
