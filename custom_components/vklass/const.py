DOMAIN = "vklass"

# config flow settings 
VKLASS_CONFKEY_AUTH_URL                     = "auth_url"        # Auth starting point url 
VKLASS_CONFKEY_USERNAME                     = "username"
VKLASS_CONFKEY_PASSWORD                     = "password"
VKLASS_CONFKEY_PERSONNO                     = "personno"
VKLASS_CONFKEY_KEEPALIVE_MIN                = "keepalive_minutes"

# async callback config keys
VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE           = "async_on_qr_update_cb" # async callback function to notify when a new QR code is available, plaintext QR string as input parameter
VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB        = "async_on_auth_fail_cb"
VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE  = "async_on_auth_cookie_update_cb"
