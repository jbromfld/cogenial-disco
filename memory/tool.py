import psycopg2
from psycopg2.extras import Json

from config import settings


def upsert_agent_memory(
    db_connection,
    primary_abstraction: str,
    primary_embedding: list[float],
    new_memory_value: dict,
    new_cue_anchors: list[str],
) -> dict:
    """
    MCP Tool: Processes a new memory by checking for semantic similarity against
    existing memory structures. Updates if a match is found; inserts otherwise.

    Args:
        db_connection: Active psycopg2 database connection.
        primary_abstraction (str): The summary concept (e.g., "Project Timeline").
        primary_embedding (list[float]): Vector of the abstraction (dim set by EMBEDDING_DIM).
        new_memory_value (dict): The raw, detailed memory to store.
        new_cue_anchors (list[str]): Semantic hooks (e.g., ["Jane", "hiking"]).

    Returns:
        dict: A status payload indicating if a record was updated or inserted.
    """

    # Cosine distance = 1 - cosine_similarity. Threshold driven by MEMORY_SIMILARITY_THRESHOLD.
    SIMILARITY_DISTANCE_THRESHOLD = 1.0 - settings.MEMORY_SIMILARITY_THRESHOLD
    
    try:
        with db_connection.cursor() as cursor:
            # Step 1: Search for the closest matching Primary Abstraction
            # We cast the Python list to a vector type in Postgres natively
            search_query = """
                SELECT id, memory_value, cue_anchors, 
                       (primary_embedding <=> %s::vector) AS distance 
                FROM agent_memory 
                ORDER BY distance ASC 
                LIMIT 1;
            """
            cursor.execute(search_query, (primary_embedding,))
            result = cursor.fetchone()

            # Step 2 & 3: Evaluate and Merge/Insert
            if result and result[3] < SIMILARITY_DISTANCE_THRESHOLD:
                # MATCH FOUND: Retrieve existing data
                match_id = result[0]
                existing_memory_value = result[1]
                existing_cue_anchors = result[2] or []

                # --- LLM MERGE LOGIC GOES HERE ---
                # In a full MEMORA implementation, you would pass 'existing_memory_value' 
                # and 'new_memory_value' to an LLM here to intelligently merge them.
                # For this tool, we will combine the JSON dictionaries.
                merged_memory_value = {**existing_memory_value, **new_memory_value}
                
                # Combine and deduplicate cue anchors
                merged_cues = list(set(existing_cue_anchors + new_cue_anchors))

                # Update the existing record
                update_query = """
                    UPDATE agent_memory 
                    SET memory_value = %s, 
                        cue_anchors = %s 
                    WHERE id = %s;
                """
                cursor.execute(update_query, (Json(merged_memory_value), merged_cues, match_id))
                db_connection.commit()
                
                return {
                    "status": "success",
                    "action": "updated",
                    "id": match_id,
                    "distance": result[3]
                }

            else:
                # NO MATCH (or database is empty): Insert a new record
                insert_query = """
                    INSERT INTO agent_memory 
                    (primary_abstraction, primary_embedding, memory_value, cue_anchors) 
                    VALUES (%s, %s::vector, %s, %s)
                    RETURNING id;
                """
                cursor.execute(insert_query, (
                    primary_abstraction, 
                    primary_embedding, 
                    Json(new_memory_value), 
                    new_cue_anchors
                ))
                new_id = cursor.fetchone()[0]
                db_connection.commit()
                
                return {
                    "status": "success",
                    "action": "inserted",
                    "id": new_id,
                    "distance": result[3] if result else None
                }

    except Exception as e:
        db_connection.rollback()
        return {
            "status": "error",
            "message": str(e)
        }