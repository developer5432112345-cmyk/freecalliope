const statusEl = document.querySelector("#status");
const logEl = document.querySelector("#log");
const form = document.querySelector("#create-form");
const button = document.querySelector("#create-button");

function log(value) {
  if (typeof value === "string") {
    logEl.textContent = value;
  } else {
    logEl.textContent = JSON.stringify(value, null, 2);
  }
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    statusEl.textContent = `FastSD: ${data.fastsd_api ? "online" : "offline"} | Piper: ${data.piper ? "ready" : "missing"} | Edge: ${data.edge_tts ? "ready" : "missing"} | Gemini: ${data.gemini ? "key found" : "no key"}`;
  } catch (err) {
    statusEl.textContent = "Status unavailable";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  payload.minutes = Number(payload.minutes);
  payload.scene_count = Number(payload.scene_count);
  payload.width = Number(payload.width);
  payload.height = Number(payload.height);
  payload.generate_backgrounds = data.has("generate_backgrounds");
  payload.generate_narration = data.has("generate_narration");
  payload.openvino = data.has("openvino");

  button.disabled = true;
  log("Creating project pack. This may take a while if backgrounds are enabled...");
  try {
    const res = await fetch("/api/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (!res.ok || body.error) {
      throw new Error(body.error || `Request failed: ${res.status}`);
    }
    log(body);
  } catch (err) {
    log(`Error: ${err.message}`);
  } finally {
    button.disabled = false;
  }
});

refreshStatus();
setInterval(refreshStatus, 10000);
