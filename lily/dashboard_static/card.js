// Live updates over a websocket (E22). Upgrades the polling in app.js: on any bus
// event Lily emits, refresh the cards immediately. Falls back to polling if the
// socket drops. Relies on renderAll(), poll() and setConn() defined in app.js.
"use strict";

(function () {
  let ws = null;

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => setConn("live ◆", "live");

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.event === "snapshot" && msg.cards) {
        renderAll(msg.cards);
      } else {
        // A bus event fired — pull fresh card data.
        poll();
      }
    };

    ws.onclose = () => {
      setConn("reconnecting…", "dead");
      setTimeout(connect, 3000);
    };

    ws.onerror = () => { try { ws.close(); } catch (e) { /* ignore */ } };
  }

  connect();
})();
