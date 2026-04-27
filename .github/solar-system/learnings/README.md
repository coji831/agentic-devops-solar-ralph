# SOLAR Learning System

<!-- Activated when `"learning": true` in `.github/solar.config.json`. Empty by default. -->

Learning files are generated at runtime when `"learning": true` is set in `solar.config.json`. This folder is empty by default.

To enable the learning system, set `"learning": true` in `.github/solar.config.json`. The agent will scaffold `PATTERNS.md`, `ERRORS.md`, `FEATURE_REQUESTS.md`, and `LOG-SOURCES.md` in this folder, and will inject a condensed learning summary into each session's context.
