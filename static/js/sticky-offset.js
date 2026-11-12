// The workspace tab bar sticks just below the sticky topbar. The topbar wraps to two or
// three rows on narrow windows (or wider fonts), so its height is measured, not assumed:
// a fixed offset let the topbar cover the tabs and swallow their clicks.
(function () {
  const topbar = document.querySelector(".topbar");
  if (!topbar) return;
  const apply = () =>
    document.documentElement.style.setProperty("--topbar-h", `${topbar.offsetHeight}px`);
  apply();
  if ("ResizeObserver" in window) new ResizeObserver(apply).observe(topbar);
  else window.addEventListener("resize", apply);
})();
