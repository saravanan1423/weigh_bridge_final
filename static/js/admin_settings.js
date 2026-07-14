const adminSettingsApiUrl = "/settings/api/admin";
const adminSettingsForm = document.querySelector("#adminSettingsForm");
const resetSerialDailyInput = document.querySelector("#resetSerialDaily");
const resendButtonEnabledInput = document.querySelector("#resendButtonEnabled");
const liveWeightEnabledInput = document.querySelector("#liveWeightEnabled");
const updateManifestUrlInput = document.querySelector("#updateManifestUrl");
const appVersionLabel = document.querySelector("#appVersion");
const checkUpdateButton = document.querySelector("#checkUpdateButton");
const applyUpdateButton = document.querySelector("#applyUpdateButton");
const updateStatus = document.querySelector("#updateStatus");
const adminSectionButtons = Array.from(document.querySelectorAll("[data-admin-section]"));
const adminPanels = Array.from(document.querySelectorAll("[data-admin-panel]"));
const adminLinkButtons = Array.from(document.querySelectorAll("[data-admin-link]"));

adminSectionButtons.forEach(button => {
  button.addEventListener("click", () => {
    const section = button.dataset.adminSection;
    adminSectionButtons.forEach(item => item.classList.toggle("active", item === button));
    adminPanels.forEach(panel => {
      panel.hidden = panel.dataset.adminPanel !== section;
    });
  });
});

adminLinkButtons.forEach(button => {
  button.addEventListener("click", () => {
    const targetUrl = button.dataset.adminLink;
    if (targetUrl) {
      window.location.href = targetUrl;
    }
  });
});


function applyAdminSettings(settings = {}) {
  resetSerialDailyInput.checked = Boolean(settings.resetSerialDaily);
  resendButtonEnabledInput.checked = settings.resendButtonEnabled !== false;
  liveWeightEnabledInput.checked = settings.liveWeightEnabled !== false;
  updateManifestUrlInput.value = settings.updateManifestUrl || "";
  appVersionLabel.textContent = settings.appVersion || "--";
}


function setUpdateStatus(message, isError = false) {
  updateStatus.textContent = message || "";
  updateStatus.classList.toggle("error", Boolean(isError));
}


async function loadAdminSettings() {
  const response = await fetch(adminSettingsApiUrl);
  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(result.message || "Failed to load admin settings");
  }

  applyAdminSettings(result.settings || {});
}


adminSettingsForm.addEventListener("submit", async event => {
  event.preventDefault();

  try {
    const response = await fetch(adminSettingsApiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        resetSerialDaily: resetSerialDailyInput.checked,
        resendButtonEnabled: resendButtonEnabledInput.checked,
        liveWeightEnabled: liveWeightEnabledInput.checked,
        updateManifestUrl: updateManifestUrlInput.value.trim()
      })
    });
    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(result.message || "Failed to save admin settings");
    }

    applyAdminSettings(result.settings || {});
    showToast(result.message || "Admin settings saved");
  } catch (error) {
    showToast(error.message || "Failed to save admin settings");
  }
});

checkUpdateButton.addEventListener("click", async () => {
  applyUpdateButton.disabled = true;
  setUpdateStatus("Checking for update...");

  try {
    const response = await fetch("/settings/api/admin/update/check", { cache: "no-store" });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.message || "Failed to check update");
    }
    const latest = result.latestVersion || result.currentVersion || "--";
    setUpdateStatus(result.updateAvailable
      ? `Update available: ${result.currentVersion} -> ${latest}`
      : (result.message || "Already up to date."));
    applyUpdateButton.disabled = !result.updateAvailable;
  } catch (error) {
    setUpdateStatus(error.message || "Failed to check update", true);
  }
});


applyUpdateButton.addEventListener("click", async () => {
  applyUpdateButton.disabled = true;
  setUpdateStatus("Downloading update...");

  try {
    const response = await fetch("/settings/api/admin/update/apply", { method: "POST" });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.message || "Failed to apply update");
    }
    setUpdateStatus(result.message || "Update downloaded. Restarting...");
  } catch (error) {
    setUpdateStatus(error.message || "Failed to apply update", true);
    applyUpdateButton.disabled = false;
  }
});


loadAdminSettings().catch(error => {
  showToast(error.message || "Failed to load admin settings");
});
