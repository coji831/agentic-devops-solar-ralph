/**
 * common.cjs
 * Shared utilities for SOLAR-Ralph hook system
 * v4.1 - Extracted common patterns across all 8 hooks
 */

"use strict";

const fs = require("fs");
const path = require("path");

function getHookLogRetentionDays(config) {
  const days = Number(config?.logging?.hookLog?.daysToKeep);
  return Number.isFinite(days) && days > 0 ? days : 7;
}

function rotateHookLogsDaily(logDir, retentionDays) {
  try {
    const rotationStampPath = path.join(logDir, ".hook-log-rotation.last");
    const today = new Date().toISOString().slice(0, 10);

    if (fs.existsSync(rotationStampPath)) {
      const lastRotationDay = fs.readFileSync(rotationStampPath, "utf8").trim();
      if (lastRotationDay === today) {
        return;
      }
    }

    const threshold = Date.now() - retentionDays * 24 * 60 * 60 * 1000;
    const logFiles = fs
      .readdirSync(logDir)
      .filter((name) => name.endsWith(".log"))
      .map((name) => path.join(logDir, name));

    logFiles.forEach((logFilePath) => {
      try {
        const stat = fs.statSync(logFilePath);
        if (stat.mtimeMs < threshold) {
          fs.unlinkSync(logFilePath);
        }
      } catch (e) {
        // Best-effort per file; never fail hook flow
      }
    });

    fs.writeFileSync(rotationStampPath, today, "utf8");
  } catch (e) {
    // Rotation is best-effort, never block hook execution
  }
}

/**
 * Log hook execution event to dedicated log file
 * v4.1 Task 1.5: Hook execution logging
 * @param {string} eventName - Hook event name (e.g., "SessionStart", "PreToolUse")
 * @param {string} message - Log message
 */
function logHookExecution(eventName, message) {
  try {
    const logDir = path.resolve(__dirname, "../solar-system/logs");
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }

    const config = loadConfig();
    const retentionDays = getHookLogRetentionDays(config);
    rotateHookLogsDaily(logDir, retentionDays);

    const logFile = path.join(logDir, eventName.toLowerCase() + ".log");
    const timestamp = new Date().toISOString();
    const logLine = `[${timestamp}] [${eventName}] ${message}\n`;
    fs.appendFileSync(logFile, logLine, "utf8");
  } catch (e) {
    // Logging is best-effort, never block hook execution
  }
}

/**
 * Load SOLAR configuration from solar.config.json
 * @returns {object|null} Parsed config or null if missing/invalid
 */
function loadConfig() {
  try {
    const configPath = path.resolve(__dirname, "../solar.config.json");
    return JSON.parse(fs.readFileSync(configPath, "utf8"));
  } catch (e) {
    return null;
  }
}

/**
 * Read AI ledger file content
 * @returns {string} Ledger content or empty string if missing
 */
function readLedger() {
  try {
    const ledgerPath = path.resolve(__dirname, "../.ai_ledger.md");
    return fs.existsSync(ledgerPath) ? fs.readFileSync(ledgerPath, "utf8") : "";
  } catch (e) {
    return "";
  }
}

/**
 * Extract session type from ledger
 * @param {string} ledger - Ledger content
 * @returns {string} Session type (lowercase) or "chat" as default
 */
function getSessionType(ledger) {
  const match = ledger.match(/Session-Type:\s*(\w[\w-]*)/i);
  return match ? match[1].toLowerCase() : "chat";
}

/**
 * Check global SOLAR gate (master switch)
 * v4.1: Merged hooks.enabled into solar.active (Option A)
 * @param {object} config - SOLAR config object
 * @returns {boolean} True if SOLAR is active
 */
function isSolarActive(config) {
  return config && config.solar?.active === true;
}

/**
 * Check if current session is bootstrap mode (bypass all governance)
 * @param {object} config - SOLAR config object
 * @param {string} sessionType - Current session type
 * @returns {boolean} True if bootstrap mode active
 */
function isBootstrapMode(config, sessionType) {
  return (
    config &&
    config.sessionTypes &&
    config.sessionTypes[sessionType] === "bootstrap"
  );
}

/**
 * Resolve session log directory path from config
 * @param {object} config - SOLAR config object
 * @returns {string} Absolute path to session log directory
 */
function resolveSessionLogDir(config) {
  return config.logging?.sessionLog?.path
    ? path.resolve(__dirname, "../../", config.logging.sessionLog.path)
    : path.resolve(__dirname, "../solar-system/logs/");
}

/**
 * Resolve learnings directory path from config
 * @param {object} config - SOLAR config object
 * @returns {string} Absolute path to learnings directory
 */
function resolveLearningsDir(config) {
  return config.selfImprovement?.learningsPath
    ? path.resolve(__dirname, "../../", config.selfImprovement.learningsPath)
    : path.resolve(__dirname, "../solar-system/learnings/");
}

/**
 * Resolve LEARNINGS.md file path
 * @param {object} config - SOLAR config object
 * @returns {string} Absolute path to LEARNINGS.md
 */
function resolveLearningsPath(config) {
  return path.join(resolveLearningsDir(config), "PATTERNS.md");
}

/**
 * Resolve ERRORS.md file path
 * @param {object} config - SOLAR config object
 * @returns {string} Absolute path to ERRORS.md
 */
function resolveErrorsPath(config) {
  return path.join(resolveLearningsDir(config), "ERRORS.md");
}

/**
 * Resolve ledger file path
 * @returns {string} Absolute path to .ai_ledger.md
 */
function resolveLedgerPath() {
  return path.resolve(__dirname, "../.ai_ledger.md");
}

/**
 * Resolve hook debug log path
 * @returns {string} Absolute path to hook-debug.log
 */
function resolveDebugLogPath() {
  return path.resolve(__dirname, "../solar-system/logs/hook-debug.log");
}

module.exports = {
  logHookExecution,
  loadConfig,
  readLedger,
  getSessionType,
  isSolarActive,
  isBootstrapMode,
  resolveSessionLogDir,
  resolveLearningsDir,
  resolveLearningsPath,
  resolveErrorsPath,
  resolveLedgerPath,
  resolveDebugLogPath,
};
