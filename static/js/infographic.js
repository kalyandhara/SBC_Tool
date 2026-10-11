// Infographic buttons: each [data-infographic] button downloads a PNG card for its tab.
// data-params maps the tab's own inputs to query args, as "input-id:arg,input-id:arg".
// An arg named "month" takes the first seven characters of the input (YYYY-MM).
(function () {
  const notify = (msg) => (typeof showToast === "function" ? showToast(msg) : alert(msg));

  function queryFor(btn) {
    const q = new URLSearchParams();
    (btn.dataset.params || "").split(",").filter(Boolean).forEach((pair) => {
      const [id, arg] = pair.split(":");
      const input = document.getElementById(id);
      const value = input ? String(input.value || "").trim() : "";
      if (!value) return;
      q.set(arg, arg === "month" ? value.slice(0, 7) : value);
    });
    return q;
  }

  async function download(btn) {
    const page = btn.dataset.infographic;
    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Drawing…";
    try {
      const qs = queryFor(btn).toString();
      const response = await fetch(`/api/infographic/${encodeURIComponent(page)}${qs ? "?" + qs : ""}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || `Infographic failed (${response.status})`);
      }
      const blob = await response.blob();
      const name = (response.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name ? name[1] : `sbc-${page}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      notify(e.message || "Infographic failed");
    } finally {
      btn.disabled = false;
      btn.textContent = label;
    }
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-infographic]");
    if (btn) download(btn);
  });
})();
