#!/usr/bin/env node

if (process.argv.length !== 5) {
  console.error("Usage: node ys6_ppsspp_request.js <port> <request-json-file> <output-json>");
  process.exit(2);
}

const fs = require("fs");
const port = Number(process.argv[2]);
const requestText = fs.readFileSync(process.argv[3], "utf8").replace(/^\uFEFF/, "");
const request = JSON.parse(requestText);
const output = process.argv[4];
const socket = new WebSocket(`ws://127.0.0.1:${port}/debugger`, "debugger.ppsspp.org");
const timeout = setTimeout(() => fail("Timed out"), 30000);
let done = false;

function fail(message) {
  if (done) return;
  done = true;
  clearTimeout(timeout);
  console.error(message);
  try { socket.close(); } catch (_) {}
  process.exitCode = 1;
}

socket.onopen = () => socket.send(JSON.stringify(request));
socket.onerror = () => fail("Unable to connect");
socket.onmessage = (message) => {
  let response;
  try { response = JSON.parse(message.data); } catch (_) { return; }
  if (response.event !== request.event && response.event !== "error") return;
  done = true;
  clearTimeout(timeout);
  fs.writeFileSync(output, JSON.stringify(response, null, 2) + "\n");
  console.log(JSON.stringify(response));
  socket.close();
};
