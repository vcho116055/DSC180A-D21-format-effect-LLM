# Initial transport failure and explicit restart

The first direct `python -m` launch attempted four calibration requests before the runner's error stop took effect. All returned APIConnectionError without a response ID or HTTP status. They are retained here as operational failures and not scored as completed model observations. No main requests were sent.

A read-only model-access check succeeded through urllib, and a separate SDK model lookup succeeded through a PowerShell Python-stdin launch. Before examining any model answers, the same frozen 32 calibration cases were explicitly restarted through that working invocation. This was a documented transport restart, not a silent per-request retry or replacement of incorrect model answers. The original gate and every stimulus were unchanged. The completed calibration, if successful, is recorded at the parent directory; this attempt remains available in addition to it.

The original protocol did not predefine a transport restart. This is an operational deviation introduced before any model output was available. Counts of completed experimental requests must be distinguished from these four additional failed dispatches. The original source/protocol snapshots and plan hashes are preserved.
