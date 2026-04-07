const AUTH_METHOD_BANKID_QR = "bankid_qr";
const AUTH_METHOD_MANUAL_COOKIE = "manual_cookie";
const AUTH_STATUS_INPROGRESS = "inprogress";
const AUTH_STATUS_SUCCESS = "success";
const AUTH_STATUS_FAIL = "fail";
const CARD_TAG = "vklass-auth-card";
const EDITOR_TAG = "vklass-auth-card-editor";
const TRANSLATIONS = {
  en: {
    entity_not_found: "Entity not found",
    unsupported_auth_method: "Unsupported auth method",
    logged_in: "Logged in to Vklass",
    logged_out: "Not logged in to Vklass",
    scan_bankid: "Scan with the BankID app",
    waiting_for_qr: "Waiting for QR code...",
    starting_authentication: "Starting authentication...",
    login_to_vklass: "Log in to Vklass",
    cookie_instructions:
      "Login to Vklass with a browser and paste the value of the se.vklass.authentication cookie here",
    login_with_cookie: "Login with cookie",
    logout: "Log out",
    auth_sensor: "Auth sensor",
    select_auth_sensor: "Select a Vklass auth sensor",
    auth_sensor_hint: "Only entities matching sensor.vklass_*_auth are shown.",
  },
  sv: {
    entity_not_found: "Entiteten hittades inte",
    unsupported_auth_method: "Autentiseringsmetoden stöds inte",
    logged_in: "Inloggad i Vklass",
    logged_out: "Inte inloggad i Vklass",
    scan_bankid: "Scanna med BankID appen",
    waiting_for_qr: "Väntar på QR-kod...",
    starting_authentication: "Startar autentisering...",
    login_to_vklass: "Logga in i Vklass",
    cookie_instructions:
      "Logga in i Vklass med en webbläsare och klistra in värdet för cookien se.vklass.authentication här",
    login_with_cookie: "Logga in med cookie",
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
    this._cookieValue = "";
    this._qrCode = null;
    this._qrImageUrl = null;
    this._qrLoading = false;
    this._qrError = null;

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];

    if (this._pendingAction === "authenticate" && stateObj?.state === AUTH_STATUS_INPROGRESS) {
      this._pendingAction = null;
    }
    if (this._pendingAction === "set_cookie" && stateObj?.state === AUTH_STATUS_SUCCESS) {
      this._pendingAction = null;
      this._cookieValue = "";
    }
    if (this._pendingAction === "logout" && stateObj?.state !== AUTH_STATUS_SUCCESS) {
      this._pendingAction = null;
    }

    const qrCode =
      stateObj?.state === AUTH_STATUS_INPROGRESS
        ? String(stateObj.attributes.qr_code ?? "").trim()
        : "";
    this._syncQrImage(qrCode);

    this._render(stateObj);
  }

  getCardSize() {
    return 4;
  }

  _render(stateObj) {
    if (!this.shadowRoot || !this._hass) {
      return;
    }

    if (!stateObj) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="wrap missing">${escapeHtml(localize(this._hass, "entity_not_found"))}: ${escapeHtml(this._config.entity)}</div>
        </ha-card>
        ${this._style()}
      `;
      return;
    }

    const authMethod = stateObj.attributes.auth_method;
    const state = stateObj.state;
    const message = stateObj.attributes.message;

    this.shadowRoot.innerHTML = `
      ${this._style()}
      <ha-card>
        <div class="wrap">
          ${this._renderBody(stateObj, authMethod, state, message)}
        </div>
      </ha-card>
    `;

    this.shadowRoot
      .querySelector("[data-action='authenticate']")
      ?.addEventListener("click", () => this._handleAuthenticate());

    this.shadowRoot
      .querySelector("[data-action='set-cookie']")
      ?.addEventListener("click", () => this._handleSetCookie());

    this.shadowRoot
      .querySelector("[data-action='logout']")
      ?.addEventListener("click", () => this._handleLogout());

    this.shadowRoot.querySelector(".cookie-input")?.addEventListener("input", (event) => {
      this._cookieValue = event.target.value;
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
          justify-items: center;
        }
        .missing,
        .status {
          color: var(--primary-text-color);
          font-size: 1rem;
          line-height: 1.45;
          text-align: center;
        }
        .hint {
          color: var(--secondary-text-color);
          font-size: 0.95rem;
          line-height: 1.5;
          text-align: center;
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
        ha-progress-button {
          --mdc-theme-primary: var(--primary-color);
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
        ha-circular-progress {
          color: var(--primary-color);
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
        .cookie-input {
          width: 100%;
          max-width: 32rem;
          min-height: 104px;
          box-sizing: border-box;
          resize: vertical;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
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

  _renderBody(stateObj, authMethod, state, message) {
    if (authMethod === AUTH_METHOD_BANKID_QR) {
      return this._renderBankIdQr(stateObj, state, message);
    }

    if (authMethod === AUTH_METHOD_MANUAL_COOKIE) {
      return this._renderManualCookie(state, message);
    }

    return `
      <div class="status">${escapeHtml(localize(this._hass, "unsupported_auth_method"))}</div>
      <div class="hint">${escapeHtml(authMethod ?? "unknown")}</div>
    `;
  }

  _renderBankIdQr(stateObj, state, message) {
    if (state === AUTH_STATUS_SUCCESS) {
      return `
        <div class="status">${escapeHtml(localize(this._hass, "logged_in"))}</div>
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
      <div class="status">${escapeHtml(localize(this._hass, "logged_out"))}</div>
      <div class="actions">
        ${this._renderActionButton("authenticate", localize(this._hass, "login_to_vklass"))}
      </div>
      ${state === AUTH_STATUS_FAIL && message ? this._renderError(message) : ""}
    `;
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

  _renderManualCookie(state, message) {
    if (state === AUTH_STATUS_SUCCESS) {
      return `
        <div class="status">${escapeHtml(localize(this._hass, "logged_in"))}</div>
        <div class="actions">${this._renderLogoutButton()}</div>
      `;
    }

    const buttonDisabled = this._pendingAction === "set_cookie" || !this._cookieValue.trim();

    return `
      <div class="status">${escapeHtml(localize(this._hass, "cookie_instructions"))}</div>
      <textarea class="cookie-input" placeholder="se.vklass.authentication">${escapeHtml(this._cookieValue)}</textarea>
      <div class="actions">
        ${this._pendingAction === "set_cookie"
          ? this._renderSpinner()
          : this._renderActionButton("set-cookie", localize(this._hass, "login_with_cookie"), buttonDisabled)}
      </div>
      ${state === AUTH_STATUS_FAIL && message ? this._renderError(message) : ""}
    `;
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

  async _handleAuthenticate() {
    this._pendingAction = "authenticate";
    this._render(this._hass.states[this._config.entity]);

    try {
      await this._hass.callService("vklass", "authenticate", {
        entity_id: this._config.entity,
      });
    } catch (err) {
      this._pendingAction = null;
      this._render(this._hass.states[this._config.entity]);
      throw err;
    }
  }

  async _handleSetCookie() {
    const authCookie = this._cookieValue.trim();
    if (!authCookie) {
      return;
    }

    this._pendingAction = "set_cookie";
    this._render(this._hass.states[this._config.entity]);

    try {
      await this._hass.callService("vklass", "set_auth_cookie", {
        entity_id: this._config.entity,
        auth_cookie: authCookie,
      });
    } catch (err) {
      this._pendingAction = null;
      this._render(this._hass.states[this._config.entity]);
      throw err;
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
  description: "Vklass authentication card for BankID QR and manual cookie login",
});
