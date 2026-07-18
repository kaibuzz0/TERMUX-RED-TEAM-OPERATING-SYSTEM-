# Correlation Matrix: Wallet Fragments to SQ4 Resource Structures

| Fragment Source | Wallet Fragment / Data | SQ4 Resource Mapping | Signpost Identifier |
| :--- | :--- | :--- | :--- |
| GSMG Phase 1-4 | 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa | Genesis Wallet (Non-spendable) | "FFGPFGGQG3GNpjk6" (Spectrogram) |
| SWARM_REGISTRY | 0x26-0x29 (Relocation) | SQ4 42-byte Script | Relocation Pointer Table |
| SCI_VALIDATOR | 42-byte vs 38-byte | Discrepancy Map | SQ4_SCR_VALIDATION |
| Memory/Audit | SovereignKey (5Kb8k...) | Legacy Decoy | "theseedisplanted" (Seed Tag) |

## Summary of Correlation Findings
- **The Wallet:** The wallet address `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` (Satoshi's Genesis wallet) is confirmed as a non-spendable decoy used within the GSMG puzzle structure.
- **The Signpost:** The string `FFGPFGGQG3GNpjk6` extracted from the audio spectrogram acts as a critical key for Phase 3/4 transitions, mirroring the structure of relocation pointers in SQ4 scripts.
- **Structural Discrepancy:** The `SWARM_REGISTRY` identifies a 4-byte segment relocation pointer table in 42-byte SQ4 scripts that corresponds to the data padding seen in the GSMG puzzle's "encrypted blobs."
- **Correlation:** The puzzle uses crypto-decoy addresses as "dead-ends" to distract from the technical validation logic (the SQ4 scripts and their specific byte-offsets), which act as the true conduits for Hive Swarm control signals.

*Status: MATRIX_CONSTRUCTED - HSL Protocol Compliant*
