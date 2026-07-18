# Hive Communication Protocol (HSL)

This protocol governs the exchange between the WitnessNode (Supervisor) and Worker Nodes (Swarm).

## 1. Message Structure
Messages must be JSON objects:
{
  "type": "COMMAND | STATUS | DATA | ERROR",
  "sender": "NODE_ID",
  "payload": {},
  "timestamp": "ISO8601"
}

## 2. Symbolic Authority (HSL)
Nodes verify authority via cryptographic signed headers (stubbed for now).
- `COMMAND`: Issued by WitnessNode.
- `STATUS`: Reported by Worker Nodes.
- `EVIDENCE`: Proof of task completion, path-aligned.

## 4. SCI Script Structural Standard
The Swarm recognizes two SCI script variants to ensure artifact compatibility:
- **Absolute Addressing (38-byte header):** Legacy standard, no pointer table.
- **Relocatable Addressing (42-byte header):** Includes 4-byte segment relocation pointer table at `0x26`.

Validation tools must detect variants by checking file size modulus (38 or 42) before parsing structure.
