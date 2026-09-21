"""
SIH26100 — Neo4j Knowledge Graph Synchronization Script
Seeds all 12 bidders, directors, addresses, bank accounts, and relationships into Neo4j.
"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mock_apis.synthetic_data import get_all_bidders
from db.neo4j_driver import neo4j_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("authbid.sync_neo4j")


def sync_knowledge_graph():
    if not neo4j_service.is_available:
        logger.warning("Neo4j database is currently unreachable. Sync will run when database is online.")
        return False

    bidders = get_all_bidders()
    logger.info(f"Synchronizing {len(bidders)} bidders to Neo4j Knowledge Graph...")

    # 1. Create Constraints & Indexes
    constraints = [
        "CREATE CONSTRAINT bidder_id_unique IF NOT EXISTS FOR (b:Bidder) REQUIRE b.bidder_id IS UNIQUE",
        "CREATE CONSTRAINT director_din_unique IF NOT EXISTS FOR (d:Director) REQUIRE d.din IS UNIQUE",
        "CREATE CONSTRAINT bank_ifsc_unique IF NOT EXISTS FOR (b:Bank) REQUIRE b.ifsc IS UNIQUE",
    ]
    for c in constraints:
        try:
            neo4j_service.execute_write(c)
        except Exception as e:
            logger.debug(f"Constraint notice: {e}")

    # 2. Sync Nodes and Edges
    for b in bidders:
        bidder_id = b["bidder_id"]
        # Bidder node
        neo4j_service.execute_write(
            """
            MERGE (b:Bidder {bidder_id: $bidder_id})
            SET b.entity_name = $entity_name,
                b.pan = $pan,
                b.gstin = $gstin,
                b.cin = $cin,
                b.bid_amount = $bid_amount,
                b.make_in_india_percent = $mii,
                b.oem_name = $oem_name
            """,
            {
                "bidder_id": bidder_id,
                "entity_name": b["entity_name"],
                "pan": b.get("pan", ""),
                "gstin": b.get("gstin", ""),
                "cin": b.get("cin", ""),
                "bid_amount": b.get("bid_amount", 0),
                "mii": b.get("make_in_india_percent", 50),
                "oem_name": b.get("oem_name", ""),
            },
        )

        # Directors
        for d in b.get("directors", []):
            din = d.get("din") or d.get("pan") or d.get("name")
            neo4j_service.execute_write(
                """
                MATCH (b:Bidder {bidder_id: $bidder_id})
                MERGE (d:Director {din: $din})
                SET d.name = $name, d.pan = $pan, d.phone = $phone, d.email = $email
                MERGE (b)-[:HAS_DIRECTOR]->(d)
                """,
                {
                    "bidder_id": bidder_id,
                    "din": din,
                    "name": d.get("name", ""),
                    "pan": d.get("pan", ""),
                    "phone": d.get("phone", ""),
                    "email": d.get("email", ""),
                },
            )

        # Address
        addr = b.get("registered_address", {})
        if addr:
            addr_id = f"{addr.get('pincode', '')}-{addr.get('line1', '')[:15]}"
            neo4j_service.execute_write(
                """
                MATCH (b:Bidder {bidder_id: $bidder_id})
                MERGE (a:Address {address_id: $addr_id})
                SET a.line1 = $line1, a.city = $city, a.state = $state, a.pincode = $pincode
                MERGE (b)-[:REGISTERED_AT]->(a)
                """,
                {
                    "bidder_id": bidder_id,
                    "addr_id": addr_id,
                    "line1": addr.get("line1", ""),
                    "city": addr.get("city", ""),
                    "state": addr.get("state", ""),
                    "pincode": addr.get("pincode", ""),
                },
            )

        # Bank Account
        bank = b.get("bank_account", {})
        if bank.get("ifsc"):
            neo4j_service.execute_write(
                """
                MATCH (b:Bidder {bidder_id: $bidder_id})
                MERGE (bk:Bank {ifsc: $ifsc})
                SET bk.bank_name = $bank_name, bk.branch = $branch
                MERGE (b)-[:BANKS_WITH]->(bk)
                """,
                {
                    "bidder_id": bidder_id,
                    "ifsc": bank.get("ifsc"),
                    "bank_name": bank.get("bank_name", ""),
                    "branch": bank.get("branch", ""),
                },
            )

    logger.info("Successfully synced all bidders to Neo4j Knowledge Graph.")
    return True


if __name__ == "__main__":
    sync_knowledge_graph()
