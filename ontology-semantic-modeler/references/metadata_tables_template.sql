-- ============================================================================
-- Template: Ontology Metadata Tables
-- ============================================================================
-- Replace {{DATABASE}}, {{SCHEMA}}, {{ONTOLOGY_NAME}} with actual values.
-- Replace {{CLASS_ROWS}}, {{RELATION_ROWS}}, etc. with generated data.
--
-- This template shows the 4-table pattern for mapping OWL concepts to Snowflake:
--   ONT_CLASS           -> OWL classes (hierarchy)
--   ONT_RELATION_DEF    -> OWL object properties (relationships)
--   ONT_CLASS_MAPPING   -> Class -> physical table mapping
--   ONT_RELATION_MAPPING -> Relationship -> physical edge source mapping
-- ============================================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ONT_CLASS: Stores the class hierarchy extracted from OWL
-- One row per OWL class. PARENT_CLASS_NAME creates the hierarchy tree.
-- IS_ABSTRACT=TRUE means no physical table (used for grouping only).
CREATE TABLE IF NOT EXISTS ONT_CLASS (
    CLASS_NAME          STRING NOT NULL PRIMARY KEY,
    PARENT_CLASS_NAME   STRING,
    IS_ABSTRACT         BOOLEAN DEFAULT FALSE,
    DESCRIPTION         STRING,
    ONTOLOGY_NAME       STRING DEFAULT '{{ONTOLOGY_NAME}}',
    TYPE_CLASS          STRING DEFAULT 'ANALYTICAL',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ONT_RELATION_DEF: Stores relationship definitions from OWL object properties
-- DOMAIN_CLASS/RANGE_CLASS constrain which classes can participate.
-- IS_HIERARCHICAL=TRUE enables hierarchy view generation.
-- IS_TRANSITIVE=TRUE enables recursive CTE patterns.
CREATE TABLE IF NOT EXISTS ONT_RELATION_DEF (
    REL_NAME            STRING NOT NULL PRIMARY KEY,
    DOMAIN_CLASS        STRING NOT NULL,
    RANGE_CLASS         STRING NOT NULL,
    CARDINALITY         STRING DEFAULT 'N:N',
    IS_HIERARCHICAL     BOOLEAN DEFAULT FALSE,
    IS_TRANSITIVE       BOOLEAN DEFAULT FALSE,
    INVERSE_REL_NAME    STRING,
    DESCRIPTION         STRING,
    ONTOLOGY_NAME       STRING DEFAULT '{{ONTOLOGY_NAME}}',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ONT_CLASS_MAPPING: Maps each OWL class to a physical Snowflake table
-- SOURCE_TABLE is the fully-qualified table name.
-- FILTER_CONDITION is an optional WHERE clause (e.g., NODE_TYPE = 'CellType').
-- ID_COLUMN, NAME_COLUMN, DESCRIPTION_COLUMN identify the key columns.
CREATE TABLE IF NOT EXISTS ONT_CLASS_MAPPING (
    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,
    CLASS_NAME          STRING NOT NULL,
    SOURCE_TABLE        STRING NOT NULL,
    FILTER_CONDITION    STRING,
    ID_COLUMN           STRING NOT NULL,
    NAME_COLUMN         STRING,
    DESCRIPTION_COLUMN  STRING,
    PROPS_COLUMN        STRING,
    ONTOLOGY_NAME       STRING DEFAULT '{{ONTOLOGY_NAME}}',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (CLASS_NAME) REFERENCES ONT_CLASS(CLASS_NAME)
);

-- ONT_RELATION_MAPPING: Maps each OWL relationship to a physical edge source
-- SOURCE_TABLE + SRC_COLUMN + DST_COLUMN define the edge.
-- FILTER_CONDITION narrows to specific edge types if the table stores multiple.
CREATE TABLE IF NOT EXISTS ONT_RELATION_MAPPING (
    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,
    REL_NAME            STRING NOT NULL,
    SOURCE_TABLE        STRING NOT NULL,
    FILTER_CONDITION    STRING,
    SRC_COLUMN          STRING NOT NULL,
    DST_COLUMN          STRING NOT NULL,
    PROPS_COLUMN        STRING,
    ONTOLOGY_NAME       STRING DEFAULT '{{ONTOLOGY_NAME}}',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (REL_NAME) REFERENCES ONT_RELATION_DEF(REL_NAME)
);
