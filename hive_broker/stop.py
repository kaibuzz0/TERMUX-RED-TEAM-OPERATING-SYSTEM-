"""Emergency stop support."""

from __future__ import annotations

from hive_broker.session import BrokerSession


def stop_session(session: BrokerSession, transaction_id: str | None = None) -> dict:
    if transaction_id:
        found = session.stop_transaction(transaction_id)
        return {"stopped": found, "transaction_id": transaction_id}
    session.stop()
    return {"stopped": True, "scope": "session"}
