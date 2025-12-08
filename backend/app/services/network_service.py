from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import Party, Relationship
from typing import List, Dict, Any

def get_downstream_network(db: Session, party_id: int, max_depth: int = 10) -> Dict[str, Any]:
    """
    Get all parties downstream from the given party using recursive CTE.
    
    Downstream = parties that this party supplies to, manufactures for, etc.
    Example: If A → B → C, then B and C are downstream from A
    
    Args:
        db: Database session
        party_id: ID of the root party
        max_depth: Maximum depth to traverse (prevents infinite loops)
    
    Returns:
        Dictionary with 'nodes' (list of parties) and 'edges' (relationships)
    """
    # Recursive CTE (Common Table Expression) query
    # This is like a temporary table that references itself
    query = text("""
        WITH RECURSIVE network_tree AS (
            -- BASE CASE: Start with the root party (depth 0)
            SELECT 
                p.id,
                p.name,
                p.party_type,
                0 as depth,
                ARRAY[p.id] as path  -- Track path to prevent cycles
            FROM parties p
            WHERE p.id = :party_id
            
            UNION ALL
            
            -- RECURSIVE CASE: Find parties connected from previous level
            SELECT 
                p.id,
                p.name,
                p.party_type,
                nt.depth + 1 as depth,  -- Increment depth
                nt.path || p.id         -- Add current party to path
            FROM parties p
            -- Join through relationships table
            JOIN relationships r ON r.to_party_id = p.id
            -- Join with previous iteration results
            JOIN network_tree nt ON nt.id = r.from_party_id
            WHERE nt.depth < :max_depth           -- Stop at max depth
              AND NOT p.id = ANY(nt.path)         -- Prevent cycles (don't revisit same party)
        )
        SELECT DISTINCT id, name, party_type, depth
        FROM network_tree
        ORDER BY depth, name
    """)
    
    # Execute query with parameters
    result = db.execute(query, {"party_id": party_id, "max_depth": max_depth})
    
    # Convert result rows to list of dictionaries
    nodes = [dict(row._mapping) for row in result]
    
    # Get the relationships (edges) between these nodes
    if nodes:
        node_ids = [node['id'] for node in nodes]
        edges = db.query(Relationship).filter(
            Relationship.from_party_id.in_(node_ids),
            Relationship.to_party_id.in_(node_ids)
        ).all()
    else:
        edges = []
    
    return {
        "nodes": nodes,
        "edges": edges
    }


def get_upstream_network(db: Session, party_id: int, max_depth: int = 10) -> Dict[str, Any]:
    """
    Get all parties upstream from the given party.
    
    Upstream = parties that supply to this party
    Example: If A → B → C, then A and B are upstream from C
    
    Args:
        db: Database session
        party_id: ID of the root party
        max_depth: Maximum depth to traverse
    
    Returns:
        Dictionary with 'nodes' (list of parties) and 'edges' (relationships)
    """
    query = text("""
        WITH RECURSIVE network_tree AS (
            -- BASE CASE: Start with the root party
            SELECT 
                p.id,
                p.name,
                p.party_type,
                0 as depth,
                ARRAY[p.id] as path
            FROM parties p
            WHERE p.id = :party_id
            
            UNION ALL
            
            -- RECURSIVE CASE: Find parties that supply to current level
            -- Notice: Join is reversed compared to downstream
            SELECT 
                p.id,
                p.name,
                p.party_type,
                nt.depth + 1 as depth,
                nt.path || p.id
            FROM parties p
            JOIN relationships r ON r.from_party_id = p.id  -- Reversed join
            JOIN network_tree nt ON nt.id = r.to_party_id   -- Reversed join
            WHERE nt.depth < :max_depth
              AND NOT p.id = ANY(nt.path)  -- Prevent cycles
        )
        SELECT DISTINCT id, name, party_type, depth
        FROM network_tree
        ORDER BY depth, name
    """)
    
    result = db.execute(query, {"party_id": party_id, "max_depth": max_depth})
    nodes = [dict(row._mapping) for row in result]
    
    # Get relationships between these nodes
    if nodes:
        node_ids = [node['id'] for node in nodes]
        edges = db.query(Relationship).filter(
            Relationship.from_party_id.in_(node_ids),
            Relationship.to_party_id.in_(node_ids)
        ).all()
    else:
        edges = []
    
    return {
        "nodes": nodes,
        "edges": edges
    }


def get_direct_counterparties(db: Session, party_id: int) -> List[Party]:
    """
    Get parties directly connected to this party (depth = 1 only).
    
    Useful for showing immediate business partners.
    
    Args:
        db: Database session
        party_id: ID of the party
    
    Returns:
        List of Party objects
    """
    # Get parties this party connects TO (downstream)
    downstream_ids = db.query(Relationship.to_party_id).filter(
        Relationship.from_party_id == party_id
    ).all()
    
    # Get parties that connect TO this party (upstream)
    upstream_ids = db.query(Relationship.from_party_id).filter(
        Relationship.to_party_id == party_id
    ).all()
    
    # Combine and get unique party IDs
    all_ids = set([id[0] for id in downstream_ids + upstream_ids])
    
    # Fetch the actual Party objects
    if all_ids:
        return db.query(Party).filter(Party.id.in_(all_ids)).all()
    return []