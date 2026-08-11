#!/usr/bin/env node

const fs = require("fs");

function usage() {
  console.error(
    "Usage: node ys6_ppsspp_memory_dump.js <port> <address> <size> <output>"
  );
  process.exit(2);
}

if (process.argv.length !== 6) usage();

const port = Number(process.argv[2]);
const address = Number(process.argv[3]);
const size = Number(process.argv[4]);
const output = process.argv[5];

if (!Number.isInteger(port) || port <= 0 || port > 65535) usage();
if (!Number.isInteger(address) || address < 0) usage();
if (!Number.isInteger(size) || size <= 0) usage();

const chunkSize = 0x10000;
const chunks = [];
let offset = 0;
let finished = false;

const socket = new WebSocket(
  `ws://127.0.0.1:${port}/debugger`,
  "debugger.ppsspp.org"
);

const timeout = setTimeout(() => fail("Timed out while reading PPSSPP memory"), 60000);

function fail(message) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  console.error(message);
  try { socket.close(); } catch (_) {}
  process.exitCode = 1;
}

function requestNext() {
  if (offset >= size) {
    finished = true;
    clearTimeout(timeout);
    const data = Buffer.concat(chunks, size);
    fs.writeFileSync(output, data);
    console.log(JSON.stringify({
      address: `0x${address.toString(16)}`,
      size: data.length,
      output,
    }));
    socket.close();
    return;
  }

  socket.send(JSON.stringify({
    event: "memory.read",
    address: address + offset,
    size: Math.min(chunkSize, size - offset),
  }));
}

socket.onopen = requestNext;
socket.onerror = () => fail("Unable to connect to the PPSSPP remote debugger");
socket.onmessage = (event) => {
  let response;
  try {
    response = JSON.parse(event.data);
  } catch (_) {
    return;
  }

  if (response.event !== "memory.read") return;
  if (typeof response.base64 !== "string") {
    fail(`PPSSPP memory.read failed: ${JSON.stringify(response)}`);
    return;
  }

  const chunk = Buffer.from(response.base64, "base64");
  if (chunk.length === 0) {
    fail("PPSSPP returned an empty memory chunk");
    return;
  }
  chunks.push(chunk);
  offset += chunk.length;
  requestNext();
};
