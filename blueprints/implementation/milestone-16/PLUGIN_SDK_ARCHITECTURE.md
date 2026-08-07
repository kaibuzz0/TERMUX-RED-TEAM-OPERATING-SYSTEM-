# Plugin SDK Architecture

The Plugin SDK is a narrow waist between plugins and Hive OS subsystems.

## Layers

1. **Manifest** — strict schema validation
2. **Identity** — plugin digest binding
3. **Capabilities** — grant contract
4. **Compatibility** — version negotiation
5. **Policy** — Policy Engine integration
6. **Broker Client** — bounded API
7. **Configuration** — Config Engine namespace
8. **Lifecycle** — state machine
9. **Registry** — staged plugin tracking
10. **Loader** — safe bundle extraction
11. **Signing** — metadata trust states
12. **Audit** — non-secret audit records
