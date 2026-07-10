"use strict";
const fs = require("fs"),
  path = require("path");

function loadConfig() {
  try {
    return JSON.parse(
      fs.readFileSync(
        path.resolve(__dirname, "..", "solar.config.json"),
        "utf8",
      ),
    );
  } catch {
    return null;
  }
}

function readLedger() {
  try {
    return fs.readFileSync(
      path.resolve(__dirname, "..", ".ai_ledger.md"),
      "utf8",
    );
  } catch {
    return "";
  }
}

// Hooks are on when config.hooks is absent or true; off only when explicitly false.
function isSolarActive(config) {
  return config?.hooks !== false;
}

module.exports = {
  loadConfig,
  readLedger,
  isSolarActive,
};
