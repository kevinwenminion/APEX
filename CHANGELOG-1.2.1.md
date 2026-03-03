# APEX 1.2.1 Changelog

Release date: 2026-03-03

## New Features

- Added the `apex account` command to manage Bohrium account settings in one place (default path: `~/.apex/account.json`).
- Added both interactive and non-interactive account setup options:
  - `--email`
  - `--password`
  - `--program-id`
- Added account management utilities:
  - `apex account --show`
  - `apex account --reset`

## Configuration Improvements

- For Bohrium workflows, the following shared settings are auto-injected when they are missing in `-c` JSON:
  - `dflow_host = https://workflows.deepmodeling.com`
  - `k8s_api_server = https://workflows.deepmodeling.com`
  - `batch_type = Bohrium`
  - `context_type = Bohrium`
  - `apex_image_name = registry.dp.tech/dptech/prod-11045/apex-dependency:1.2.0`
- Configuration priority is now:
  1. Values in the `-c` JSON file
  2. Values in `~/.apex/account.json`
  3. Built-in Bohrium defaults

## Examples and Documentation

- Simplified Bohrium `global_bohrium.json` examples to avoid storing credentials in project directories.
- Updated README with `apex account` usage and default-injection behavior.
- Updated all property examples to use `req_calc` instead of `skip` for property on/off control.
- Documented property selection defaults:
  - Property block absent from `properties`: not calculated.
  - Property block present without `req_calc`: calculated by default.
  - Property block with `req_calc: false`: not calculated.

## Compatibility

- Backward compatible: if account or shared Bohrium fields are explicitly set in `global_bohrium.json`, those values are still used.
- Backward compatible for property controls: legacy `skip` is still accepted when `req_calc` is not provided.
