APEX GUI — Major Fix Release

🔥 Highlights

This release focuses on critical bug fixes, workflow robustness, and major usability improvements.
The system transitions toward a more recoverable and observable workflow execution model.

⸻

🔧 Critical Bug Fixes

* Fixed parameter override during submit
    * Previously, user-defined parameters were unintentionally overridden by templates.
    * New behavior: user input always takes precedence; templates act as defaults only.
* Fixed parameter override during properties selection
    * Selecting properties no longer resets or overwrites existing user configurations.
    * Ensures parameter consistency across workflow stages.

⸻

🚀 New Features

Workflow & Data Management

* Workdir support
    * Define and manage working directories explicitly.
    * Added support for:
        * File uploads
        * Structure uploads (direct ingestion into workflow)
* Decoupled Retrieve + Report system
    * Removed blocking report behavior.
    * Reports now launch via a separate port, preventing UI freeze during workflow execution.
* Network-resilient Retrieve
    * Retry retrieve downloads only for transient network failures.
    * Permanent storage errors, such as missing artifacts, fail fast without retry.
    * Prevents workflow interruption due to unstable network conditions while avoiding long waits on unrecoverable artifact errors.

⸻

Monitoring & Progress Tracking

* Configuration statistics
    * Track number of:
        * Completed configurations
        * Failed configurations
* Workflow activity timestamp
    * Displays Last updated: <timestamp>
    * Helps detect stalled or inactive workflows
* Retrieve progress bar
    * Real-time progress visualization
    * Automatically skips already retrieved configurations (idempotent behavior)
    * Automatically detects `apex-retrieve.log` in the selected Workdir and updates retrieve progress when retrieve is already running.
    * Failed-artifact downloads skip existing `.failed-artifacts` target folders when files are already present.
* Auto workflow status query
    * Entering a Workflow ID now triggers automatic status retrieval
* Fast workflow progress query
    * Workflow progress now first queries lightweight `Phase` and Argo `Progress` fields.
    * Displays status such as `Phase: Running | Progress: 850/1942` without waiting for full step details.
* Background workflow detail cache
    * Detailed `Steps` and `Confs` statistics are queried in a background process.
    * Detail refresh is throttled to 30 seconds and cached after completion.
    * Slow full-step queries no longer block the GUI progress callback.

⸻

Control & Parameter Alignment

* Enhanced Reset functionality
    * Fully resets:
        * Logs
        * Intermediate states
        * Cached data
* Parameter naming alignment
    * maximal → maxeval
    * Consistent with LAMMPS parameter conventions
* Removed Apply button
    * Redundant with Submit
    * Simplifies user interaction flow

⸻

🧭 UI / UX Improvements

* Refined interface text
    * Removed prompt-like or ambiguous wording
    * Improved clarity and usability

⸻

⚠️ Known Issues

* Workflow data propagation issue (apex submit -s)
    * Files generated during the relaxation stage are not correctly passed to the properties calculation stage
    * Likely related to artifact handling or step isolation in workflow execution
* Insufficient error reporting
    * Failure reasons are not properly exposed
    * Limited debugging visibility for failed computations
