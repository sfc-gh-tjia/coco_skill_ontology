-- ============================================================================
-- Template: Abstract Ontology Views
-- ============================================================================
-- Replace {{DATABASE}}, {{SCHEMA}} with actual values.
-- These views enable Cortex Analyst to query ontology concepts.
--
-- Pattern 1: Hierarchy Relationship View
--   Resolves edge table IDs to human-readable names via node table JOINs.
--   Used by recursive CTEs for descendant/ancestor traversal.
--
-- Pattern 2: Entity Type View
--   One per concrete OWL class. Standardizes columns to (ID, ENTITY_TYPE, LABEL, DESCRIPTION).
--
-- Pattern 3: Unified Entity View
--   UNION ALL of all entity type views for polymorphic queries.
--
-- Pattern 4: Helper Views
--   Descendants, ancestors, hierarchy stats for common query patterns.
-- ============================================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Pattern 1: Hierarchy relationship view with resolved names
-- Requires: edge table (src_id, dst_id) + node table (node_id, name)
CREATE OR REPLACE VIEW VW_ONT_SUBCLASS_OF AS
SELECT
    e.SRC_ID AS CHILD_ID,
    e.DST_ID AS PARENT_ID,
    'subClassOf' AS REL_TYPE,
    child.NAME AS CHILD_NAME,
    parent.NAME AS PARENT_NAME,
    child.NODE_TYPE AS CHILD_TYPE,
    parent.NODE_TYPE AS PARENT_TYPE
FROM {{EDGE_TABLE}} e
LEFT JOIN {{NODE_TABLE}} child ON e.SRC_ID = child.{{NODE_ID_COL}}
LEFT JOIN {{NODE_TABLE}} parent ON e.DST_ID = parent.{{NODE_ID_COL}}
WHERE e.EDGE_TYPE = 'subClassOf';  -- adjust filter per ontology

-- Pattern 2: Entity type view (one per mapped class)
CREATE OR REPLACE VIEW VW_ONT_{{CLASS_NAME}} AS
SELECT
    {{ID_COL}} AS ID,
    '{{CLASS_NAME}}' AS ENTITY_TYPE,
    {{NAME_COL}} AS LABEL,
    {{DESC_COL}} AS DESCRIPTION
FROM {{SOURCE_TABLE}}
WHERE {{FILTER_CONDITION}};  -- omit WHERE if no filter needed

-- Pattern 3: Unified entity view
CREATE OR REPLACE VIEW VW_ONT_ALL_ENTITIES AS
SELECT ID, ENTITY_TYPE, LABEL, DESCRIPTION, '{{TABLE_1}}' AS SOURCE_TABLE
FROM VW_ONT_{{CLASS_1}}
UNION ALL
SELECT ID, ENTITY_TYPE, LABEL, DESCRIPTION, '{{TABLE_2}}' AS SOURCE_TABLE
FROM VW_ONT_{{CLASS_2}};
-- ... add more UNION ALL for each entity type

-- Pattern 4a: Descendant helper (used with recursive CTEs)
CREATE OR REPLACE VIEW VW_DESCENDANTS AS
SELECT CHILD_ID, PARENT_ID, CHILD_NAME, PARENT_NAME, CHILD_TYPE, PARENT_TYPE
FROM VW_ONT_SUBCLASS_OF;

-- Pattern 4b: Ancestor helper (inverse direction)
CREATE OR REPLACE VIEW VW_ANCESTORS AS
SELECT
    PARENT_ID AS ANCESTOR_ID,
    CHILD_ID AS DESCENDANT_ID,
    PARENT_NAME AS ANCESTOR_NAME,
    CHILD_NAME AS DESCENDANT_NAME
FROM VW_ONT_SUBCLASS_OF;

-- Pattern 4c: Hierarchy stats
CREATE OR REPLACE VIEW VW_ONT_HIERARCHY_STATS AS
SELECT
    n.{{NODE_ID_COL}} AS NODE_ID,
    n.{{NAME_COL}} AS NODE_NAME,
    COUNT(DISTINCT child.CHILD_ID) AS DIRECT_CHILDREN_COUNT,
    COUNT(DISTINCT parent.PARENT_ID) AS DIRECT_PARENTS_COUNT
FROM {{NODE_TABLE}} n
LEFT JOIN VW_ONT_SUBCLASS_OF child ON n.{{NODE_ID_COL}} = child.PARENT_ID
LEFT JOIN VW_ONT_SUBCLASS_OF parent ON n.{{NODE_ID_COL}} = parent.CHILD_ID
GROUP BY n.{{NODE_ID_COL}}, n.{{NAME_COL}};
