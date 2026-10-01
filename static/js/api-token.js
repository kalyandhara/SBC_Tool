// Writes (POST/PUT/DELETE) need X-API-Token once the server has SBC_API_TOKEN set.
// Store yours once:  localStorage.setItem('sbcApiToken', '<token>')
(function () {
  var orig = window.fetch;
  window.fetch = function (input, init) {
    init = init || {};
    var method = (init.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
      var token = null;
      try { token = localStorage.getItem('sbcApiToken'); } catch (e) {}
      if (token) {
        var headers = new Headers(init.headers || {});
        headers.set('X-API-Token', token);
        init = Object.assign({}, init, { headers: headers });
      }
    }
    return orig.call(this, input, init);
  };
})();
