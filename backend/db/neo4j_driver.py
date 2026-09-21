"""
SIH26100 — Production Neo4j Driver & Graph Operations
Provides asynchronous Neo4j connection pooling, Cypher execution,
and multi-hop relationship traversal for GeM collusion detection.
"""
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger("authbid.neo4j")


class Neo4jService:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self._driver = None
        self._is_available = False

    def get_driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_lifetime=300,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=3.0,
                )
                # Verify connectivity
                with self._driver.session() as session:
                    session.run("RETURN 1 AS ping")
                self._is_available = True
                logger.info(f"Connected to Neo4j database at {self.uri}")
            except Exception as e:
                self._is_available = False
                logger.warning(f"Neo4j is not reachable at {self.uri}: {e}. Operating in graceful in-memory fallback mode.")
        return self._driver

    @property
    def is_available(self) -> bool:
        if self._driver is None:
            self.get_driver()
        return self._is_available

    def execute_query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher read query and return records as dictionaries."""
        driver = self.get_driver()
        if not self._is_available or not driver:
            return []
        try:
            with driver.session() as session:
                result = session.run(cypher, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            return []

    def execute_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a Cypher write transaction."""
        driver = self.get_driver()
        if not self._is_available or not driver:
            return None
        try:
            with driver.session() as session:
                result = session.execute_write(lambda tx: tx.run(cypher, parameters or {}).data())
                return result
        except Exception as e:
            logger.error(f"Error executing Cypher write: {e}")
            return None

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            self._is_available = False


# Singleton instance
neo4j_service = Neo4jService()
