const AUTH_METHOD_BANKID_QR = "bankid_qr";
const AUTH_METHOD_BANKID_PERSONNO = "bankid_personno";
const AUTH_METHOD_USERPASS = "userpass";
const AUTH_METHOD_MANUAL_COOKIE = "manual_cookie";
const AUTH_STATUS_INPROGRESS = "inprogress";
const AUTH_STATUS_SUCCESS = "success";
const AUTH_STATUS_FAIL = "fail";
const PERSISTED_SECRET_SENTINEL = "__PERSISTED_SECRET__";
const CARD_TAG = "vklass-auth-card";
const EDITOR_TAG = "vklass-auth-card-editor";
const SUPPORTED_AUTH_METHODS = new Set([
  AUTH_METHOD_BANKID_QR,
  AUTH_METHOD_BANKID_PERSONNO,
  AUTH_METHOD_USERPASS,
  AUTH_METHOD_MANUAL_COOKIE,
]);
const TRANSLATIONS = {
  en: {
    logged_in: "Logged in to Vklass",
    scan_bankid: "Scan with the BankID app",
    waiting_for_qr: "Waiting for QR code...",
    starting_authentication: "Starting authentication...",
    login_to_vklass: "Log in to Vklass",
    username: "Username",
    password: "Password",
    personno: "Personal number",
    cookie: "se.vklass.authentication cookie:",
    save_credentials: "Save credentials",
    cookie_instructions:
      "Log in to Vklass with a browser and paste the value of the se.vklass.authentication cookie here",
    logout: "Log out",
    auth_sensor: "Auth sensor",
    select_auth_sensor: "Select a Vklass auth sensor",
    auth_sensor_hint: "Only entities matching sensor.vklass_*_auth are shown.",
  },
  sv: {
    logged_in: "Inloggad i Vklass",
    scan_bankid: "Scanna med BankID appen",
    waiting_for_qr: "Väntar på QR-kod...",
    starting_authentication: "Startar autentisering...",
    login_to_vklass: "Logga in i Vklass",
    username: "Användarnamn",
    password: "Lösenord",
    personno: "Personnummer",
    cookie: "se.vklass.authentication cookie:",
    save_credentials: "Spara inloggningsuppgifter",
    cookie_instructions:
      "Logga in i Vklass med en webbläsare och klistra in värdet för cookien se.vklass.authentication här",
    logout: "Logga ut",
    auth_sensor: "Autentiseringssensor",
    select_auth_sensor: "Välj en Vklass autentiseringssensor",
    auth_sensor_hint: "Endast entiteter som matchar sensor.vklass_*_auth visas.",
  },
};

function isVklassAuthEntity(entityId, stateObj) {
  return (
    typeof entityId === "string" &&
    entityId.startsWith("sensor.vklass_") &&
    entityId.endsWith("_auth") &&
    stateObj &&
    typeof stateObj.attributes?.auth_method === "string"
  );
}

function getVklassAuthEntities(hass) {
  return Object.entries(hass?.states ?? {})
    .filter(([entityId, stateObj]) => isVklassAuthEntity(entityId, stateObj))
    .map(([entityId, stateObj]) => ({
      entityId,
      name: stateObj.attributes.friendly_name || entityId,
    }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

function hasElement(tagName) {
  return Boolean(customElements.get(tagName));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getLanguage(hass) {
  return (hass?.selectedLanguage || hass?.language || "en").split("-")[0];
}

function localize(hass, key) {
  const language = getLanguage(hass);
  const table = TRANSLATIONS[language] || TRANSLATIONS.en;
  return table[key] || TRANSLATIONS.en[key] || key;
}

class VklassAuthCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig(hass) {
    const firstEntity = getVklassAuthEntities(hass)[0]?.entityId;
    return firstEntity ? { entity: firstEntity } : {};
  }

  setConfig(config) {
    if (!config?.entity) {
      throw new Error("Required configuration missing: entity");
    }

    this._config = config;
    this._pendingAction = null;
    this._lastState = null;
    this._qrCode = null;
    this._qrImageUrl = null;
    this._qrLoading = false;
    this._qrError = null;
    this._formValues = {
      username: "",
      password: "",
      personno: "",
      cookie: "",
      save_credentials: false,
    };
    this._dirtyFields = new Set();

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];
    const authMethod = stateObj?.attributes?.auth_method;
    const nextState = stateObj?.state ?? null;
    let forceSync = false;

    if (
      this._pendingAction === "authenticate" &&
      authMethod === AUTH_METHOD_BANKID_QR &&
      nextState === AUTH_STATUS_INPROGRESS
    ) {
      this._pendingAction = null;
    }

    if (this._pendingAction === "logout" && nextState !== AUTH_STATUS_SUCCESS) {
      this._pendingAction = null;
      this._dirtyFields.clear();
      forceSync = true;
    }

    if (this._lastState !== AUTH_STATUS_SUCCESS && nextState === AUTH_STATUS_SUCCESS) {
      this._dirtyFields.clear();
      forceSync = true;
    }

    if (!stateObj) {
      this._renderErrorCard(`Entity not found: ${this._config.entity}`);
      this._lastState = null;
      return;
    }

    if (!SUPPORTED_AUTH_METHODS.has(authMethod)) {
      this._renderErrorCard(`Unsupported auth method: ${authMethod ?? "unknown"}`);
      this._lastState = nextState;
      return;
    }

    this._syncFormFromState(stateObj, forceSync);

    const qrCode =
      nextState === AUTH_STATUS_INPROGRESS
        ? String(stateObj?.attributes?.qr_code ?? "").trim()
        : "";
    this._syncQrImage(qrCode);

    this._render(stateObj);
    this._lastState = nextState;
  }

  getCardSize() {
    return 5;
  }

  _syncFormFromState(stateObj, force = false) {
    if (!stateObj) {
      return;
    }

    const attrs = stateObj.attributes ?? {};
    const authMethod = attrs.auth_method;
    const nextValues = {
      username: String(attrs.username ?? ""),
      password: attrs.persisted_password ? PERSISTED_SECRET_SENTINEL : "",
      personno: String(attrs.personno ?? ""),
      cookie: "",
      save_credentials: this._supportsSaveCredentials(authMethod)
        ? Boolean(attrs.save_credentials)
        : false,
    };

    for (const [key, value] of Object.entries(nextValues)) {
      if (force || !this._dirtyFields.has(key)) {
        this._formValues[key] = value;
      }
    }
  }

  _render(stateObj) {
    if (!this.shadowRoot || !this._hass) {
      return;
    }

    const authMethod = stateObj.attributes.auth_method;
    const state = stateObj.state;
    const message = stateObj.attributes.message;

    this.shadowRoot.innerHTML = `
      ${this._style()}
      <ha-card>
        <div class="wrap">
          ${this._renderHeader(stateObj, authMethod, this._config.entity)}
          ${this._renderBody(stateObj, authMethod, state, message)}
        </div>
      </ha-card>
    `;

    this.shadowRoot
      .querySelector("[data-action='authenticate']")
      ?.addEventListener("click", () => this._handleAuthenticate());

    this.shadowRoot
      .querySelector("[data-action='logout']")
      ?.addEventListener("click", () => this._handleLogout());

    this.shadowRoot.querySelectorAll("[data-field]").forEach((input) => {
      input.addEventListener("input", (event) => {
        const { field } = event.target.dataset;
        this._formValues[field] = event.target.value;
        this._dirtyFields.add(field);
        this._render(this._hass.states[this._config.entity]);
      });
    });

    this.shadowRoot.querySelector("[data-field='save_credentials']")?.addEventListener("change", (event) => {
      this._formValues.save_credentials = event.target.checked;
      this._dirtyFields.add("save_credentials");
      this._render(this._hass.states[this._config.entity]);
    });
  }

  _style() {
    return `
      <style>
        :host {
          display: block;
        }
        .wrap {
          display: grid;
          gap: 16px;
          padding: 16px;
        }
        .header-block {
          display: grid;
          gap: 4px;
          justify-items: center;
          text-align: center;
        }
        .header-title {
          color: var(--primary-text-color);
          font-size: var(--ha-font-size-l);
          font-weight: var(--ha-font-weight-medium);
          line-height: 1.3;
          margin-bottom: 10px;
        }
        .header-subtitle {
          color: var(--secondary-text-color);
          font-family: var(--ha-font-family-body);
          font-size: var(--ha-font-size-m);
          font-weight: var(--ha-font-weight-medium);
          line-height: 1.4;
        }
        .status,
        .hint {
          color: var(--primary-text-color);
          line-height: 1.45;
          text-align: center;
        }
        .hint {
          color: var(--secondary-text-color);
          font-size: 0.95rem;
        }
        .error {
          color: var(--error-color);
          font-size: 0.95rem;
          line-height: 1.45;
          text-align: center;
        }
        .actions {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
          justify-content: center;
        }
        .form {
          display: grid;
          gap: 12px;
        }
        .field {
          display: grid;
          gap: 6px;
        }
        .field label,
        .checkbox {
          color: var(--primary-text-color);
          font-size: 0.95rem;
        }
        .checkbox {
          display: flex;
          gap: 10px;
          align-items: center;
          justify-content: center;
        }
        .field input {
          width: 100%;
          box-sizing: border-box;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }
        .action-button {
          appearance: none;
          border: 0;
          border-radius: 999px;
          padding: 12px 18px;
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
          font: inherit;
          font-weight: 600;
          line-height: 1;
          cursor: pointer;
          transition: transform 120ms ease, opacity 120ms ease, filter 120ms ease;
        }
        .action-button:hover {
          filter: brightness(1.05);
        }
        .action-button:active {
          transform: translateY(1px);
        }
        .action-button:disabled {
          opacity: 0.45;
          cursor: not-allowed;
          filter: none;
        }
        .spinner {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          border: 3px solid color-mix(in srgb, var(--primary-color) 20%, transparent);
          border-top-color: var(--primary-color);
          animation: spin 0.9s linear infinite;
        }
        .qr-shell {
          background: linear-gradient(180deg, #ffffff, #f6f6f6);
          border-radius: 18px;
          padding: 16px;
          display: grid;
          place-items: center;
        }
        .qr-shell img {
          display: block;
          width: min(100%, 320px);
          height: auto;
        }
        ha-alert {
          --alert-color: var(--error-color);
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      </style>
    `;
  }

  _renderErrorCard(error) {
    if (!this.shadowRoot) {
      return;
    }

    this.shadowRoot.innerHTML = "";
    const errorCard = document.createElement("hui-error-card");
    errorCard.setConfig({
      type: "error",
      error,
      origConfig: this._config,
    });
    errorCard.hass = this._hass;
    this.shadowRoot.appendChild(errorCard);
  }

  _renderHeader(stateObj, authMethod, fallbackTitle) {
    const title = this._getCardTitle(stateObj, fallbackTitle);
    const subtitles = this._getCardSubtitles(stateObj, authMethod);

    return `
      <div class="header-block">
        <div class="header-title">${escapeHtml(title)}</div>
        ${subtitles
          .map((subtitle) => `<div class="header-subtitle">${escapeHtml(subtitle)}</div>`)
          .join("")}
      </div>
    `;
  }

  _getCardTitle(stateObj, fallbackTitle) {
    return (
      stateObj?.attributes?.device_name ||
      stateObj?.attributes?.friendly_name ||
      fallbackTitle ||
      this._config.entity
    );
  }

  _getCardSubtitles(stateObj, authMethod) {
    if (
      authMethod !== AUTH_METHOD_BANKID_QR &&
      authMethod !== AUTH_METHOD_BANKID_PERSONNO &&
      authMethod !== AUTH_METHOD_USERPASS &&
      authMethod !== AUTH_METHOD_MANUAL_COOKIE
    ) {
      return [];
    }

    const subtitles = [];
    const adapterTitle = String(stateObj?.attributes?.auth_adapter_title || "").trim();
    const user = String(stateObj?.attributes?.user || "").trim();

    if (adapterTitle) {
      subtitles.push(adapterTitle);
    }

    if (stateObj?.state === AUTH_STATUS_SUCCESS && user) {
      subtitles.push(user);
    }

    return subtitles;
  }

  _renderBody(stateObj, authMethod, state, message) {
    if (authMethod === AUTH_METHOD_BANKID_QR) {
      return this._renderBankIdQr(state, message);
    }

    if (this._isCredentialMethod(authMethod)) {
      return this._renderCredentialMethod(authMethod, state, message);
    }

    throw new Error(`Unsupported auth method: ${authMethod ?? "unknown"}`);
  }

  _renderBankIdQr(state, message) {
    if (state === AUTH_STATUS_SUCCESS) {
      return `
        <div class="actions">${this._renderLogoutButton()}</div>
      `;
    }

    if (state === AUTH_STATUS_INPROGRESS) {
      return `
        <div class="status">${escapeHtml(localize(this._hass, "scan_bankid"))}</div>
        ${this._renderQrImage()}
        ${message ? `<div class="hint">${escapeHtml(message)}</div>` : ""}
      `;
    }

    if (this._pendingAction === "authenticate") {
      return `
        <div class="status">${escapeHtml(localize(this._hass, "starting_authentication"))}</div>
        <div class="actions">${this._renderSpinner()}</div>
      `;
    }

    return `
      <div class="actions">
        ${this._renderActionButton("authenticate", localize(this._hass, "login_to_vklass"))}
      </div>
      ${state === AUTH_STATUS_FAIL && message ? this._renderError(message) : ""}
    `;
  }

  _renderCredentialMethod(authMethod, state, message) {
    if (state === AUTH_STATUS_SUCCESS) {
      return `
        <div class="actions">${this._renderLogoutButton()}</div>
      `;
    }

    const buttonDisabled = this._isCredentialButtonDisabled(authMethod);
    const showSpinner = this._pendingAction === "authenticate";

    return `
      <div class="form">
        ${this._getCredentialFields(authMethod).join("")}
        ${this._supportsSaveCredentials(authMethod) ? `
        <label class="checkbox">
          <input type="checkbox" data-field="save_credentials" ${this._formValues.save_credentials ? "checked" : ""}>
          <span>${escapeHtml(localize(this._hass, "save_credentials"))}</span>
        </label>
        ` : ""}
        <div class="actions">
          ${showSpinner
            ? this._renderSpinner()
            : this._renderActionButton("authenticate", localize(this._hass, "login_to_vklass"), buttonDisabled)}
        </div>
        ${state === AUTH_STATUS_FAIL && message ? this._renderError(message) : ""}
      </div>
    `;
  }

  _renderInput(field, type) {
    return `
      <div class="field">
        <label for="${escapeHtml(field)}">${escapeHtml(localize(this._hass, field))}</label>
        <input
          id="${escapeHtml(field)}"
          type="${escapeHtml(type)}"
          data-field="${escapeHtml(field)}"
          value="${escapeHtml(this._formValues[field] ?? "")}"
          autocomplete="${escapeHtml(this._getAutocompleteValue(field, type))}"
          autocapitalize="off"
          autocorrect="off"
          spellcheck="false"
        >
      </div>
    `;
  }

  _getAutocompleteValue(field, type) {
    if (field === "cookie") {
      return "off";
    }

    if (field === "password") {
      return "current-password";
    }

    if (type === "password") {
      return "off";
    }

    return "off";
  }

  _isCredentialMethod(authMethod) {
    return (
      authMethod === AUTH_METHOD_BANKID_PERSONNO ||
      authMethod === AUTH_METHOD_USERPASS ||
      authMethod === AUTH_METHOD_MANUAL_COOKIE
    );
  }

  _supportsSaveCredentials(authMethod) {
    return authMethod === AUTH_METHOD_BANKID_PERSONNO || authMethod === AUTH_METHOD_USERPASS;
  }

  _getCredentialFields(authMethod) {
    if (authMethod === AUTH_METHOD_BANKID_PERSONNO) {
      return [this._renderInput("personno", "text")];
    }

    if (authMethod === AUTH_METHOD_USERPASS) {
      return [
        this._renderInput("username", "text"),
        this._renderInput("password", "password"),
      ];
    }

    if (authMethod === AUTH_METHOD_MANUAL_COOKIE) {
      return [
        `<div class="hint">${escapeHtml(localize(this._hass, "cookie_instructions"))}</div>`,
        this._renderInput("cookie", "text"),
      ];
    }

    return [];
  }

  _isCredentialButtonDisabled(authMethod) {
    if (authMethod === AUTH_METHOD_BANKID_PERSONNO) {
      return !String(this._formValues.personno || "").trim();
    }
    if (authMethod === AUTH_METHOD_USERPASS) {
      return !String(this._formValues.username || "").trim() || !String(this._formValues.password || "").trim();
    }
    if (authMethod === AUTH_METHOD_MANUAL_COOKIE) {
      return !String(this._formValues.cookie || "").trim();
    }
    return false;
  }

  _renderQrImage() {
    if (this._qrImageUrl) {
      return `<div class="qr-shell"><img src="${escapeHtml(this._qrImageUrl)}" alt="BankID QR code"></div>`;
    }

    if (this._qrError) {
      return this._renderError(this._qrError);
    }

    if (this._qrLoading || this._qrCode) {
      return `<div class="actions">${this._renderSpinner()}<div class="hint">${escapeHtml(localize(this._hass, "waiting_for_qr"))}</div></div>`;
    }

    return `<div class="hint">${escapeHtml(localize(this._hass, "waiting_for_qr"))}</div>`;
  }

  _clearQrImage() {
    if (this._qrImageUrl) {
      URL.revokeObjectURL(this._qrImageUrl);
    }
    this._qrCode = null;
    this._qrImageUrl = null;
    this._qrLoading = false;
    this._qrError = null;
  }

  _syncQrImage(qrCode) {
    if (!qrCode) {
      this._clearQrImage();
      return;
    }

    if (qrCode === this._qrCode && (this._qrLoading || this._qrImageUrl)) {
      return;
    }

    this._loadQrImage(qrCode);
  }

  async _loadQrImage(qrCode) {
    if (!this._hass?.auth?.data?.access_token) {
      this._qrError = "Home Assistant access token missing";
      this._qrLoading = false;
      this._render(this._hass.states[this._config.entity]);
      return;
    }

    this._qrCode = qrCode;
    this._qrLoading = true;
    this._qrError = null;

    try {
      const response = await fetch(`/api/vklass/qr?data=${encodeURIComponent(qrCode)}`, {
        headers: {
          Authorization: `Bearer ${this._hass.auth.data.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`QR request failed with status ${response.status}`);
      }

      const blob = await response.blob();
      const nextUrl = URL.createObjectURL(blob);

      if (this._qrImageUrl) {
        URL.revokeObjectURL(this._qrImageUrl);
      }

      if (qrCode !== this._qrCode) {
        URL.revokeObjectURL(nextUrl);
        return;
      }

      this._qrImageUrl = nextUrl;
      this._qrLoading = false;
      this._render(this._hass.states[this._config.entity]);
    } catch (err) {
      if (qrCode !== this._qrCode) {
        return;
      }

      this._qrImageUrl = null;
      this._qrLoading = false;
      this._qrError = err instanceof Error ? err.message : "Failed loading QR code";
      this._render(this._hass.states[this._config.entity]);
    }
  }

  _renderActionButton(action, label, disabled = false) {
    if (hasElement("ha-progress-button")) {
      return `<ha-progress-button data-action="${escapeHtml(action)}" ${disabled ? "disabled" : ""}>${escapeHtml(label)}</ha-progress-button>`;
    }

    return `<button class="action-button" type="button" data-action="${escapeHtml(action)}" ${disabled ? "disabled" : ""}>${escapeHtml(label)}</button>`;
  }

  _renderLogoutButton() {
    if (this._pendingAction === "logout") {
      return this._renderSpinner();
    }

    return this._renderActionButton("logout", localize(this._hass, "logout"));
  }

  _renderSpinner() {
    if (hasElement("ha-circular-progress")) {
      return `<ha-circular-progress size="small" indeterminate></ha-circular-progress>`;
    }

    return `<div class="spinner" aria-label="Loading"></div>`;
  }

  _renderError(message) {
    if (hasElement("ha-alert")) {
      return `<ha-alert alert-type="error">${escapeHtml(message)}</ha-alert>`;
    }

    return `<div class="error">${escapeHtml(message)}</div>`;
  }

  _buildAuthenticatePayload(authMethod) {
    const payload = {
      entity_id: this._config.entity,
    };

    if (authMethod === AUTH_METHOD_BANKID_PERSONNO) {
      payload.save_credentials = Boolean(this._formValues.save_credentials);
      payload.personno = this._formValues.personno ?? "";
      return payload;
    }

    if (authMethod === AUTH_METHOD_USERPASS) {
      payload.save_credentials = Boolean(this._formValues.save_credentials);
      payload.username = this._formValues.username ?? "";
      payload.password = this._formValues.password ?? "";
      return payload;
    }

    if (authMethod === AUTH_METHOD_MANUAL_COOKIE) {
      payload.cookie = this._formValues.cookie ?? "";
    }

    return payload;
  }

  async _handleAuthenticate() {
    const stateObj = this._hass.states[this._config.entity];
    const authMethod = stateObj?.attributes?.auth_method;
    const payload = this._buildAuthenticatePayload(authMethod);

    this._pendingAction = "authenticate";
    this._render(stateObj);

    try {
      await this._hass.callService("vklass", "login", payload);
    } catch (err) {
      this._pendingAction = null;
      this._render(this._hass.states[this._config.entity]);
      throw err;
    } finally {
      if (this._pendingAction === "authenticate" && authMethod !== AUTH_METHOD_BANKID_QR) {
        this._pendingAction = null;
        this._render(this._hass.states[this._config.entity]);
      }
    }
  }

  async _handleLogout() {
    this._pendingAction = "logout";
    this._render(this._hass.states[this._config.entity]);

    try {
      await this._hass.callService("vklass", "logout", {
        entity_id: this._config.entity,
      });
    } catch (err) {
      this._pendingAction = null;
      this._render(this._hass.states[this._config.entity]);
      throw err;
    }
  }
}

class VklassAuthCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) {
      return;
    }

    const entities = getVklassAuthEntities(this._hass);
    const currentValue = this._config?.entity || "";

    this.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .wrap {
          display: grid;
          gap: 8px;
          padding: 4px 0;
        }
        label {
          color: var(--primary-text-color);
          font-size: 0.95rem;
          font-weight: 500;
        }
        select {
          width: 100%;
          box-sizing: border-box;
          padding: 10px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }
        .hint {
          color: var(--secondary-text-color);
          font-size: 0.9rem;
          line-height: 1.4;
        }
      </style>
      <div class="wrap">
        <label for="entity">${escapeHtml(localize(this._hass, "auth_sensor"))}</label>
        <select id="entity">
          <option value="">${escapeHtml(localize(this._hass, "select_auth_sensor"))}</option>
          ${entities
            .map(
              ({ entityId, name }) =>
                `<option value="${escapeHtml(entityId)}" ${entityId === currentValue ? "selected" : ""}>${escapeHtml(name)} (${escapeHtml(entityId)})</option>`,
            )
            .join("")}
        </select>
        <div class="hint">${escapeHtml(localize(this._hass, "auth_sensor_hint"))}</div>
      </div>
    `;

    this.querySelector("#entity")?.addEventListener("change", (event) => {
      const entity = event.target.value;
      this._config = entity ? { ...this._config, entity } : {};
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        }),
      );
    });
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, VklassAuthCard);
}

if (!customElements.get(EDITOR_TAG)) {
  customElements.define(EDITOR_TAG, VklassAuthCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TAG,
  name: "Vklass Authentication",
  description: "Vklass authentication card for adapter-driven login flows",
});
