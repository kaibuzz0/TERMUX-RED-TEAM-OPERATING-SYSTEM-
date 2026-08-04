# Termux:API Profile

## Identity

Optional profile that adds explicitly permissioned Android API integrations.

## Requirements

- Termux:API app installed.
- Android permissions granted individually by the user.

## Capabilities (optional and individually gated)

- Clipboard access (with timeout and clear policy).
- Battery/thermal status.
- Notification integration.
- Camera/microphone (only when explicitly enabled).
- Storage access (via `termux-setup-storage`).
- Fingerprint / biometric (if device supports and user opts in).

## Security note

Termux:API does not provide additional isolation. It is a convenience layer with explicit permissions.
