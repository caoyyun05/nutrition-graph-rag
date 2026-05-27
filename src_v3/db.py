"""Neo4j database wrapper for v2."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from .config import Neo4jConfig


class Neo4jClient:
    def __init__(self, config: Neo4jConfig):
        self.config = config
        self.driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def execute(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

