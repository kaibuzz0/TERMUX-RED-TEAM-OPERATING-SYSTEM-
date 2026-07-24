# Hive Ops Tools

## Overview

The `tools/` directory contains 27 specialized security, analysis, and automation tools for the Hive Ops DevAI system.

## Tool Categories

### Blockchain & Crypto (5 tools)
| Tool | Purpose | Size |
|------|---------|------|
| `wallet_crypto_simulator.py` | Simulate crypto wallet operations | 7.4 KB |
| `blockchain_batch_checker.py` | Batch verification of blockchain data | 6.6 KB |
| `blockchain_monitor.py` | Real-time blockchain monitoring | 3.5 KB |
| `multi_address_generator.py` | Generate multiple crypto addresses | 6.4 KB |

### Analysis & Disassembly (4 tools)
| Tool | Purpose | Size |
|------|---------|------|
| `deep_disassembler_sqvi.py` | Advanced binary disassembler | 14.6 KB |
| `sci_deep_disassembler.py` | Scientific disassembly engine | 10.8 KB |
| `sq_investigation_suite.py` | Investigation toolkit | 9.0 KB |
| `resonance_scanner.py` | Pattern detection scanner | 5.1 KB |

### Obfuscation & Security (3 tools)
| Tool | Purpose | Size |
|------|---------|------|
| `obfuscation_layer.py` | Code obfuscation utilities | 7.6 KB |
| `condition_simulator.py` | Simulate various conditions | 7.2 KB |
| `sq_series_scanner.py` | Series pattern scanner | 7.4 KB |

### Batch Processing (3 tools)
| Tool | Purpose | Size |
|------|---------|------|
| `batch_job_runner.py` | Execute batch operations | 7.0 KB |
| `sci_emulator.py` | Scientific emulator | 3.0 KB |
| `hive_tool_builder.py` | Build custom Hive tools | 3.6 KB |

### Monitoring & Health (2 tools)
| Tool | Purpose | Size |
|------|---------|------|
| `hive_health_monitor.py` | System health monitoring | 5.3 KB |

## Usage

```bash
# Run a tool
cd Hive Ops Final/tools
python3 wallet_crypto_simulator.py

# Or from anywhere (if in PATH)
hive-tool wallet_crypto_simulator
```

## Dependencies

Most tools require:
- Python 3.8+
- See `../requirements.txt` for full dependencies

## Safety Notice

These tools are for authorized security testing and educational purposes only. See main project LEGAL_NOTICE.
