/**
 * Dev server launcher for Windows.
 * Bypasses npm spawnWithShell issues on some Windows/npm setups.
 */
const { spawn } = require("child_process");
const path = require("path");

const projectRoot = path.join(__dirname, "..");
const viteBin = path.join(
  projectRoot,
  "node_modules",
  "vite",
  "bin",
  "vite.js"
);

const args = [
  viteBin,
  "--host",
  "127.0.0.1",
  "--port",
  "5173",
];

const child = spawn(process.execPath, args, {
  cwd: projectRoot,
  stdio: "inherit",
  env: process.env,
  windowsHide: false,
});

child.on("error", (error) => {
  console.error("Failed to start Vite:", error.message);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
