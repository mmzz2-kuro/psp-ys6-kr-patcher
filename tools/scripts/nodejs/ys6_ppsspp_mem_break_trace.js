#!/usr/bin/env node

const fs = require("fs");

if (process.argv.length !== 7) {
  console.error("Usage: node ys6_ppsspp_mem_break_trace.js <port> <address> <size> <output-jsonl>");
  process.exit(2);
}

const port = Number(process.argv[2]);
const address = Number(process.argv[3]);
const size = Number(process.argv[4]);
const output = process.argv[5];
const timeoutSeconds = Number(process.argv[6]);
if (!Number.isInteger(port) || !Number.isInteger(address) || !Number.isInteger(size) ||
    !Number.isFinite(timeoutSeconds) || size <= 0 || timeoutSeconds <= 0) {
  throw new Error("Invalid numeric argument");
}

const socket = new WebSocket(`ws://127.0.0.1:${port}/debugger`, "debugger.ppsspp.org");
let finished = false;
let breakpointReady = false;
let requestedRegisters = false;

function record(value) {
  fs.appendFileSync(output, JSON.stringify({ time: new Date().toISOString(), ...value }) + "\n");
}

function send(event, values = {}) {
  socket.send(JSON.stringify({ event, ...values }));
}

function finish(code, message) {
  if (finished) return;
  finished = true;
  clearTimeout(timer);
  if (message) console.log(message);
  try { socket.close(); } catch (_) {}
  process.exitCode = code;
}

const timer = setTimeout(() => finish(3, "TRACE_TIMEOUT"), timeoutSeconds * 1000);

socket.onopen = () => {
  fs.writeFileSync(output, "");
  send("memory.breakpoint.add", {
    address,
    size,
    enabled: true,
    log: true,
    read: false,
    write: true,
    change: true,
    logFormat: "YS6 system glyph buffer write pc={pc}",
  });
};

socket.onerror = () => finish(1, "TRACE_CONNECTION_ERROR");
socket.onclose = () => {
  if (!finished) finish(1, "TRACE_CONNECTION_CLOSED");
};

socket.onmessage = (message) => {
  let data;
  try { data = JSON.parse(message.data); } catch (_) { return; }
  record({ response: data });

  if (data.event === "error") {
    finish(1, `TRACE_ERROR ${data.message || "unknown"}`);
    return;
  }
  if (data.event === "memory.breakpoint.add" && !breakpointReady) {
    breakpointReady = true;
    console.log(`TRACE_READY address=0x${address.toString(16)} size=${size}`);
    return;
  }
  if (data.event === "cpu.stepping" && breakpointReady && !requestedRegisters) {
    requestedRegisters = true;
    send("cpu.getAllRegs");
    send("cpu.status");
    send("memory.read", { address: address - 0x20, size: size + 0x80 });
    return;
  }
  if (data.event === "cpu.getAllRegs" && requestedRegisters) {
    const gpr = Array.isArray(data.categories)
      ? data.categories.find((category) => category.name === "GPR")
      : null;
    if (gpr) {
      const regs = Object.fromEntries(gpr.registerNames.map((name, index) => [name, gpr.uintValues[index]]));
      console.log(`TRACE_HIT pc=0x${Number(regs.pc).toString(16)}`);
      record({ registers: regs });
    } else {
      console.log("TRACE_HIT");
    }
    finish(0, `TRACE_SAVED ${output}`);
  }
};
