# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Generate SQL and Semantic Model YAML from parsed OWL ontology + table mappings.

Takes the JSON output from parse_owl.py plus a mappings configuration file,
and produces:
  1. Metadata tables SQL (ONT_CLASS, ONT_RELATION_DEF, ONT_CLASS_MAPPING, ONT_RELATION_MAPPING)
  2. Abstract views SQL (hierarchy views, entity union views, stats views)
  3. Cortex Analyst semantic model YAML

Usage:
    uv run --script generate_artifacts.py -- \
      --classes-json /tmp/parsed/classes.json \
      --relations-json /tmp/parsed/relations.json \
      --mappings-json /tmp/mappings.json \
      --database MYDB \
      --schema MYSCHEMA \
      --ontology-name DOMAIN \
      --output-dir /tmp/generated
"""

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import yaml


def sql_escape(val: str | None) -> str:
    """Escape a string for SQL single-quoted literal."""
    if val is None:
        return "NULL"
    return "'" + str(val).replace("'", "''") + "'"


def generate_metadata_sql(
    classes: list[dict],
    relations: list[dict],
    mappings: list[dict],
    rel_mappings: list[dict],
    database: str,
    schema: str,
    ontology_name: str,
) -> str:
    """Generate SQL for ontology metadata tables."""
    fqn = f"{database}.{schema}"
    lines = []
    lines.append(f"-- {'='*76}")
    lines.append(f"-- Ontology Metadata Tables for {ontology_name}")
    lines.append(f"-- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"-- {'='*76}")
    lines.append(f"")
    lines.append(f"USE SCHEMA {fqn};")
    lines.append(f"")

    # ONT_CLASS
    lines.append(f"-- ONT_CLASS: Class hierarchy from OWL")
    lines.append(f"CREATE TABLE IF NOT EXISTS ONT_CLASS (")
    lines.append(f"    CLASS_NAME          STRING NOT NULL PRIMARY KEY,")
    lines.append(f"    PARENT_CLASS_NAME   STRING,")
    lines.append(f"    IS_ABSTRACT         BOOLEAN DEFAULT FALSE,")
    lines.append(f"    DESCRIPTION         STRING,")
    lines.append(f"    ONTOLOGY_NAME       STRING DEFAULT {sql_escape(ontology_name)},")
    lines.append(f"    TYPE_CLASS          STRING DEFAULT 'ANALYTICAL',")
    lines.append(f"    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),")
    lines.append(f"    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()")
    lines.append(f");")
    lines.append(f"")

    if classes:
        lines.append(f"INSERT INTO ONT_CLASS (CLASS_NAME, PARENT_CLASS_NAME, IS_ABSTRACT, DESCRIPTION, ONTOLOGY_NAME, TYPE_CLASS)")
        lines.append(f"SELECT * FROM VALUES")
        class_rows = []
        for cls in classes:
            if cls.get("is_deprecated"):
                continue
            name = cls["name"]
            parent = cls.get("parent_name")
            is_abs = cls.get("is_abstract", False)
            desc = (cls.get("description") or cls.get("label") or "")[:500]
            type_class = "ANALYTICAL" if is_abs else "OPERATIONAL"
            class_rows.append(
                f"    ({sql_escape(name)}, {sql_escape(parent)}, {str(is_abs).upper()}, "
                f"{sql_escape(desc)}, {sql_escape(ontology_name)}, {sql_escape(type_class)})"
            )
        lines.append(",\n".join(class_rows))
        lines.append(f"AS t(CLASS_NAME, PARENT_CLASS_NAME, IS_ABSTRACT, DESCRIPTION, ONTOLOGY_NAME, TYPE_CLASS)")
        lines.append(f"WHERE NOT EXISTS (SELECT 1 FROM ONT_CLASS WHERE CLASS_NAME = t.CLASS_NAME);")
    lines.append(f"")

    # ONT_RELATION_DEF
    lines.append(f"-- ONT_RELATION_DEF: Relationship definitions from OWL properties")
    lines.append(f"CREATE TABLE IF NOT EXISTS ONT_RELATION_DEF (")
    lines.append(f"    REL_NAME            STRING NOT NULL PRIMARY KEY,")
    lines.append(f"    DOMAIN_CLASS        STRING NOT NULL,")
    lines.append(f"    RANGE_CLASS         STRING NOT NULL,")
    lines.append(f"    CARDINALITY         STRING DEFAULT 'N:N',")
    lines.append(f"    IS_HIERARCHICAL     BOOLEAN DEFAULT FALSE,")
    lines.append(f"    IS_TRANSITIVE       BOOLEAN DEFAULT FALSE,")
    lines.append(f"    INVERSE_REL_NAME    STRING,")
    lines.append(f"    DESCRIPTION         STRING,")
    lines.append(f"    ONTOLOGY_NAME       STRING DEFAULT {sql_escape(ontology_name)},")
    lines.append(f"    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()")
    lines.append(f");")
    lines.append(f"")

    if relations:
        lines.append(f"INSERT INTO ONT_RELATION_DEF (REL_NAME, DOMAIN_CLASS, RANGE_CLASS, CARDINALITY, IS_HIERARCHICAL, IS_TRANSITIVE, INVERSE_REL_NAME, DESCRIPTION)")
        lines.append(f"SELECT * FROM VALUES")
        rel_rows = []
        for rel in relations:
            rel_rows.append(
                f"    ({sql_escape(rel['name'])}, {sql_escape(rel['domain_class'])}, {sql_escape(rel['range_class'])}, "
                f"{sql_escape(rel['cardinality'])}, {str(rel['is_hierarchical']).upper()}, {str(rel['is_transitive']).upper()}, "
                f"{sql_escape(rel.get('inverse_name'))}, {sql_escape(rel.get('description', '')[:500])})"
            )
        lines.append(",\n".join(rel_rows))
        lines.append(f"AS t(REL_NAME, DOMAIN_CLASS, RANGE_CLASS, CARDINALITY, IS_HIERARCHICAL, IS_TRANSITIVE, INVERSE_REL_NAME, DESCRIPTION)")
        lines.append(f"WHERE NOT EXISTS (SELECT 1 FROM ONT_RELATION_DEF WHERE REL_NAME = t.REL_NAME);")
    lines.append(f"")

    # ONT_CLASS_MAPPING
    lines.append(f"-- ONT_CLASS_MAPPING: Map OWL classes to physical Snowflake tables")
    lines.append(f"CREATE TABLE IF NOT EXISTS ONT_CLASS_MAPPING (")
    lines.append(f"    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,")
    lines.append(f"    CLASS_NAME          STRING NOT NULL,")
    lines.append(f"    SOURCE_TABLE        STRING NOT NULL,")
    lines.append(f"    FILTER_CONDITION    STRING,")
    lines.append(f"    ID_COLUMN           STRING NOT NULL,")
    lines.append(f"    NAME_COLUMN         STRING,")
    lines.append(f"    DESCRIPTION_COLUMN  STRING,")
    lines.append(f"    PROPS_COLUMN        STRING,")
    lines.append(f"    ONTOLOGY_NAME       STRING DEFAULT {sql_escape(ontology_name)},")
    lines.append(f"    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),")
    lines.append(f"    FOREIGN KEY (CLASS_NAME) REFERENCES ONT_CLASS(CLASS_NAME)")
    lines.append(f");")
    lines.append(f"")

    if mappings:
        lines.append(f"INSERT INTO ONT_CLASS_MAPPING (CLASS_NAME, SOURCE_TABLE, FILTER_CONDITION, ID_COLUMN, NAME_COLUMN, DESCRIPTION_COLUMN, PROPS_COLUMN)")
        lines.append(f"SELECT * FROM VALUES")
        map_rows = []
        for m in mappings:
            map_rows.append(
                f"    ({sql_escape(m['class_name'])}, {sql_escape(m['source_table'])}, "
                f"{sql_escape(m.get('filter_condition'))}, {sql_escape(m['id_column'])}, "
                f"{sql_escape(m.get('name_column'))}, {sql_escape(m.get('description_column'))}, "
                f"{sql_escape(m.get('props_column'))})"
            )
        lines.append(",\n".join(map_rows))
        lines.append(f"AS t(CLASS_NAME, SOURCE_TABLE, FILTER_CONDITION, ID_COLUMN, NAME_COLUMN, DESCRIPTION_COLUMN, PROPS_COLUMN)")
        lines.append(f"WHERE NOT EXISTS (SELECT 1 FROM ONT_CLASS_MAPPING WHERE CLASS_NAME = t.CLASS_NAME AND SOURCE_TABLE = t.SOURCE_TABLE);")
    lines.append(f"")

    # ONT_RELATION_MAPPING
    lines.append(f"-- ONT_RELATION_MAPPING: Map relationships to physical edge sources")
    lines.append(f"CREATE TABLE IF NOT EXISTS ONT_RELATION_MAPPING (")
    lines.append(f"    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,")
    lines.append(f"    REL_NAME            STRING NOT NULL,")
    lines.append(f"    SOURCE_TABLE        STRING NOT NULL,")
    lines.append(f"    FILTER_CONDITION    STRING,")
    lines.append(f"    SRC_COLUMN          STRING NOT NULL,")
    lines.append(f"    DST_COLUMN          STRING NOT NULL,")
    lines.append(f"    PROPS_COLUMN        STRING,")
    lines.append(f"    ONTOLOGY_NAME       STRING DEFAULT {sql_escape(ontology_name)},")
    lines.append(f"    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),")
    lines.append(f"    FOREIGN KEY (REL_NAME) REFERENCES ONT_RELATION_DEF(REL_NAME)")
    lines.append(f");")
    lines.append(f"")

    if rel_mappings:
        lines.append(f"INSERT INTO ONT_RELATION_MAPPING (REL_NAME, SOURCE_TABLE, FILTER_CONDITION, SRC_COLUMN, DST_COLUMN, PROPS_COLUMN)")
        lines.append(f"SELECT * FROM VALUES")
        rmap_rows = []
        for rm in rel_mappings:
            rmap_rows.append(
                f"    ({sql_escape(rm['rel_name'])}, {sql_escape(rm['source_table'])}, "
                f"{sql_escape(rm.get('filter_condition'))}, {sql_escape(rm['src_column'])}, "
                f"{sql_escape(rm['dst_column'])}, {sql_escape(rm.get('props_column'))})"
            )
        lines.append(",\n".join(rmap_rows))
        lines.append(f"AS t(REL_NAME, SOURCE_TABLE, FILTER_CONDITION, SRC_COLUMN, DST_COLUMN, PROPS_COLUMN)")
        lines.append(f"WHERE NOT EXISTS (SELECT 1 FROM ONT_RELATION_MAPPING WHERE REL_NAME = t.REL_NAME AND SOURCE_TABLE = t.SOURCE_TABLE);")
    lines.append(f"")

    return "\n".join(lines)


def generate_views_sql(
    classes: list[dict],
    relations: list[dict],
    mappings: list[dict],
    rel_mappings: list[dict],
    database: str,
    schema: str,
    ontology_name: str,
    node_table: str | None = None,
    edge_table: str | None = None,
) -> str:
    """Generate SQL for abstract ontology views."""
    fqn = f"{database}.{schema}"
    lines = []
    lines.append(f"-- {'='*76}")
    lines.append(f"-- Abstract Ontology Views for {ontology_name}")
    lines.append(f"-- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"-- {'='*76}")
    lines.append(f"")
    lines.append(f"USE SCHEMA {fqn};")
    lines.append(f"")

    # Find the subClassOf relation mapping for hierarchy views
    subclass_mapping = None
    for rm in rel_mappings:
        if rm["rel_name"].lower() == "subclassof":
            subclass_mapping = rm
            break

    # 1. Hierarchy relationship view
    if subclass_mapping:
        src_tbl = subclass_mapping["source_table"]
        src_col = subclass_mapping["src_column"]
        dst_col = subclass_mapping["dst_column"]
        filt = subclass_mapping.get("filter_condition", "")

        # Determine node table for name resolution
        nt = node_table
        if not nt:
            # Try to find from class mappings
            for m in mappings:
                if m.get("source_table") and "node" in m["source_table"].lower():
                    nt = m["source_table"]
                    break

        if nt:
            # Find ID and name columns from the node table mapping
            id_col = "NODE_ID"
            name_col = "NAME"
            for m in mappings:
                if m.get("source_table") == nt:
                    id_col = m.get("id_column", "NODE_ID")
                    name_col = m.get("name_column", "NAME")
                    break

            lines.append(f"-- VW_ONT_SUBCLASS_OF: Resolved subClassOf relationships")
            lines.append(f"CREATE OR REPLACE VIEW VW_ONT_SUBCLASS_OF AS")
            lines.append(f"SELECT")
            lines.append(f"    e.{src_col} AS CHILD_ID,")
            lines.append(f"    e.{dst_col} AS PARENT_ID,")
            lines.append(f"    'subClassOf' AS REL_TYPE,")
            lines.append(f"    child.{name_col} AS CHILD_NAME,")
            lines.append(f"    parent.{name_col} AS PARENT_NAME,")
            if any(m.get("filter_condition") for m in mappings):
                lines.append(f"    child.NODE_TYPE AS CHILD_TYPE,")
                lines.append(f"    parent.NODE_TYPE AS PARENT_TYPE")
            else:
                lines.append(f"    'entity' AS CHILD_TYPE,")
                lines.append(f"    'entity' AS PARENT_TYPE")
            lines.append(f"FROM {src_tbl} e")
            lines.append(f"LEFT JOIN {nt} child ON e.{src_col} = child.{id_col}")
            lines.append(f"LEFT JOIN {nt} parent ON e.{dst_col} = parent.{id_col}")
            if filt:
                lines.append(f"WHERE e.{filt}")
            lines.append(f";")
            lines.append(f"")
        else:
            # Simple edge-only view
            lines.append(f"-- VW_ONT_SUBCLASS_OF: SubClassOf edges")
            lines.append(f"CREATE OR REPLACE VIEW VW_ONT_SUBCLASS_OF AS")
            lines.append(f"SELECT")
            lines.append(f"    {src_col} AS CHILD_ID,")
            lines.append(f"    {dst_col} AS PARENT_ID,")
            lines.append(f"    'subClassOf' AS REL_TYPE")
            lines.append(f"FROM {src_tbl}")
            if filt:
                lines.append(f"WHERE {filt}")
            lines.append(f";")
            lines.append(f"")

    # 2. Descendants helper view
    if subclass_mapping:
        lines.append(f"-- VW_DESCENDANTS: Helper for descendant traversal (use with recursive CTE)")
        lines.append(f"CREATE OR REPLACE VIEW VW_DESCENDANTS AS")
        lines.append(f"SELECT CHILD_ID, PARENT_ID, CHILD_NAME, PARENT_NAME")
        if nt:
            lines.append(f"    , CHILD_TYPE, PARENT_TYPE")
        lines.append(f"FROM VW_ONT_SUBCLASS_OF;")
        lines.append(f"")

        lines.append(f"-- VW_ANCESTORS: Helper for ancestor traversal")
        lines.append(f"CREATE OR REPLACE VIEW VW_ANCESTORS AS")
        lines.append(f"SELECT")
        lines.append(f"    PARENT_ID AS ANCESTOR_ID,")
        lines.append(f"    CHILD_ID AS DESCENDANT_ID,")
        lines.append(f"    PARENT_NAME AS ANCESTOR_NAME,")
        lines.append(f"    CHILD_NAME AS DESCENDANT_NAME")
        lines.append(f"FROM VW_ONT_SUBCLASS_OF;")
        lines.append(f"")

    # 3. Entity type views for mapped classes
    concrete_mappings = [m for m in mappings if m.get("source_table")]
    for m in concrete_mappings:
        cls_name = m["class_name"]
        view_name = f"VW_ONT_{cls_name.upper()}"
        src_table = m["source_table"]
        id_col = m["id_column"]
        name_col = m.get("name_column")
        desc_col = m.get("description_column")
        filt = m.get("filter_condition")

        lines.append(f"-- {view_name}: Abstract view for {cls_name}")
        lines.append(f"CREATE OR REPLACE VIEW {view_name} AS")
        lines.append(f"SELECT")
        lines.append(f"    {id_col} AS ID,")
        lines.append(f"    '{cls_name}' AS ENTITY_TYPE,")
        if name_col:
            lines.append(f"    {name_col} AS LABEL,")
        else:
            lines.append(f"    {id_col} AS LABEL,")
        if desc_col:
            lines.append(f"    {desc_col} AS DESCRIPTION")
        else:
            lines.append(f"    NULL AS DESCRIPTION")
        lines.append(f"FROM {src_table}")
        if filt:
            lines.append(f"WHERE {filt}")
        lines.append(f";")
        lines.append(f"")

    # 4. Unified entity view (UNION ALL of all concrete types)
    if len(concrete_mappings) > 1:
        lines.append(f"-- VW_ONT_ALL_ENTITIES: Unified view of all entity types")
        lines.append(f"CREATE OR REPLACE VIEW VW_ONT_ALL_ENTITIES AS")
        for i, m in enumerate(concrete_mappings):
            cls_name = m["class_name"]
            src_table = m["source_table"]
            id_col = m["id_column"]
            name_col = m.get("name_column") or id_col
            desc_col = m.get("description_column")
            filt = m.get("filter_condition")

            if i > 0:
                lines.append(f"UNION ALL")
            lines.append(f"SELECT")
            lines.append(f"    {id_col} AS ID,")
            lines.append(f"    '{cls_name}' AS ENTITY_TYPE,")
            lines.append(f"    {name_col} AS LABEL,")
            if desc_col:
                lines.append(f"    {desc_col} AS DESCRIPTION,")
            else:
                lines.append(f"    NULL AS DESCRIPTION,")
            lines.append(f"    '{src_table}' AS SOURCE_TABLE")
            lines.append(f"FROM {src_table}")
            if filt:
                lines.append(f"WHERE {filt}")
        lines.append(f";")
        lines.append(f"")

    # 5. Hierarchy stats view
    if subclass_mapping and nt:
        # Find the primary entity mapping to use for the base
        primary_mapping = concrete_mappings[0] if concrete_mappings else None
        if primary_mapping:
            pm_table = primary_mapping["source_table"]
            pm_id = primary_mapping["id_column"]
            pm_name = primary_mapping.get("name_column") or pm_id
            pm_filt = primary_mapping.get("filter_condition")

            lines.append(f"-- VW_ONT_HIERARCHY_STATS: Hierarchy statistics")
            lines.append(f"CREATE OR REPLACE VIEW VW_ONT_HIERARCHY_STATS AS")
            lines.append(f"SELECT")
            lines.append(f"    e.{pm_id} AS NODE_ID,")
            lines.append(f"    e.{pm_name} AS NODE_NAME,")
            lines.append(f"    COUNT(DISTINCT child.CHILD_ID) AS DIRECT_CHILDREN_COUNT,")
            lines.append(f"    COUNT(DISTINCT parent.PARENT_ID) AS DIRECT_PARENTS_COUNT")
            lines.append(f"FROM {pm_table} e")
            lines.append(f"LEFT JOIN VW_ONT_SUBCLASS_OF child ON e.{pm_id} = child.PARENT_ID")
            lines.append(f"LEFT JOIN VW_ONT_SUBCLASS_OF parent ON e.{pm_id} = parent.CHILD_ID")
            if pm_filt:
                lines.append(f"WHERE {pm_filt}")
            lines.append(f"GROUP BY e.{pm_id}, e.{pm_name};")
            lines.append(f"")

    return "\n".join(lines)


def generate_semantic_model_yaml(
    classes: list[dict],
    relations: list[dict],
    mappings: list[dict],
    database: str,
    schema: str,
    ontology_name: str,
    has_subclass_view: bool = True,
    has_unified_view: bool = True,
    has_stats_view: bool = True,
) -> str:
    """Generate Cortex Analyst semantic model YAML."""
    now_ts = int(datetime.now(timezone.utc).timestamp())

    model = {
        "name": f"{ontology_name}_ONTOLOGY_SEMANTIC_VIEW",
        "description": (
            f"{ontology_name} ontology hierarchy for dynamic traversal. "
            f"Contains entity types and their subClassOf relationships. "
            f"Use for finding descendants, hierarchy paths, and entity lookups. "
            f"For cohort expansion queries, use recursive CTEs on the SUBCLASS_RELATIONS table."
        ),
        "tables": [],
        "verified_queries": [],
    }

    # Add entity views as tables
    concrete_mappings = [m for m in mappings if m.get("source_table")]
    for m in concrete_mappings:
        cls_name = m["class_name"]
        view_name = f"VW_ONT_{cls_name.upper()}"
        name_col = m.get("name_column")

        table_def = {
            "name": view_name,
            "base_table": {
                "database": database,
                "schema": schema,
                "table": view_name,
            },
            "primary_key": {"columns": ["ID"]},
            "dimensions": [
                {"name": "ID", "expr": "ID", "data_type": "VARCHAR",
                 "description": f"Unique identifier for {cls_name}"},
                {"name": "ENTITY_TYPE", "expr": "ENTITY_TYPE", "data_type": "VARCHAR"},
                {"name": "LABEL", "expr": "LABEL", "data_type": "VARCHAR",
                 "description": f"Display name for {cls_name}"},
                {"name": "DESCRIPTION", "expr": "DESCRIPTION", "data_type": "VARCHAR"},
            ],
        }
        model["tables"].append(table_def)

    # Add subclass relationship table
    if has_subclass_view:
        subclass_table = {
            "name": "VW_ONT_SUBCLASS_OF",
            "base_table": {
                "database": database,
                "schema": schema,
                "table": "VW_ONT_SUBCLASS_OF",
            },
            "dimensions": [
                {"name": "CHILD_ID", "expr": "CHILD_ID", "data_type": "VARCHAR"},
                {"name": "PARENT_ID", "expr": "PARENT_ID", "data_type": "VARCHAR"},
                {"name": "REL_TYPE", "expr": "REL_TYPE", "data_type": "VARCHAR"},
                {"name": "CHILD_NAME", "expr": "CHILD_NAME", "data_type": "VARCHAR"},
                {"name": "PARENT_NAME", "expr": "PARENT_NAME", "data_type": "VARCHAR"},
                {"name": "CHILD_TYPE", "expr": "CHILD_TYPE", "data_type": "VARCHAR"},
                {"name": "PARENT_TYPE", "expr": "PARENT_TYPE", "data_type": "VARCHAR"},
            ],
        }
        model["tables"].append(subclass_table)

    # Add verified queries
    if has_subclass_view and concrete_mappings:
        primary = concrete_mappings[0]
        primary_view = f"VW_ONT_{primary['class_name'].upper()}"

        model["verified_queries"].extend([
            {
                "name": "list_entity_types",
                "question": f"What types of {primary['class_name'].lower()} exist in the ontology?",
                "sql": f"SELECT ID, LABEL, DESCRIPTION FROM {primary_view} ORDER BY LABEL LIMIT 50",
                "verified_at": now_ts,
                "verified_by": "Ontology Semantic Modeler",
            },
            {
                "name": "direct_children",
                "question": f"What are the direct children of a given entity?",
                "sql": f"SELECT CHILD_ID, CHILD_NAME FROM VW_ONT_SUBCLASS_OF WHERE PARENT_NAME = '{{entity_name}}' ORDER BY CHILD_NAME",
                "verified_at": now_ts,
                "verified_by": "Ontology Semantic Modeler",
            },
            {
                "name": "direct_parents",
                "question": f"What are the parents of a given entity?",
                "sql": f"SELECT PARENT_ID, PARENT_NAME FROM VW_ONT_SUBCLASS_OF WHERE CHILD_NAME = '{{entity_name}}' ORDER BY PARENT_NAME",
                "verified_at": now_ts,
                "verified_by": "Ontology Semantic Modeler",
            },
            {
                "name": "descendants_recursive",
                "question": f"What are all descendants of a given entity?",
                "sql": textwrap.dedent(f"""\
                    WITH RECURSIVE descendants AS (
                      SELECT ID AS NODE_ID, LABEL AS NODE_NAME, 0 AS depth
                      FROM {primary_view} WHERE LABEL = '{{entity_name}}'
                      UNION ALL
                      SELECT c.CHILD_ID, c.CHILD_NAME, d.depth + 1
                      FROM VW_ONT_SUBCLASS_OF c
                      JOIN descendants d ON c.PARENT_ID = d.NODE_ID
                      WHERE d.depth < 10
                    )
                    SELECT NODE_ID, NODE_NAME, depth FROM descendants ORDER BY depth, NODE_NAME"""),
                "verified_at": now_ts,
                "verified_by": "Ontology Semantic Modeler",
            },
            {
                "name": "most_children",
                "question": f"Which entities have the most direct children?",
                "sql": f"SELECT PARENT_NAME, COUNT(DISTINCT CHILD_ID) AS child_count FROM VW_ONT_SUBCLASS_OF GROUP BY PARENT_NAME ORDER BY child_count DESC LIMIT 20",
                "verified_at": now_ts,
                "verified_by": "Ontology Semantic Modeler",
            },
        ])

    return yaml.dump(model, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)


def load_mappings_file(path: str) -> tuple[list[dict], list[dict]]:
    """Load the mappings configuration JSON file.

    Expected format:
    {
      "class_mappings": [
        {"class_name": "CellType", "source_table": "DB.SCHEMA.TABLE", "id_column": "NODE_ID", ...},
        ...
      ],
      "relation_mappings": [
        {"rel_name": "subClassOf", "source_table": "DB.SCHEMA.EDGE_TABLE", "src_column": "SRC_ID", "dst_column": "DST_ID", ...},
        ...
      ],
      "node_table": "DB.SCHEMA.NODE_TABLE",  // optional
      "edge_table": "DB.SCHEMA.EDGE_TABLE"   // optional
    }
    """
    with open(path) as f:
        data = json.load(f)
    return (
        data.get("class_mappings", []),
        data.get("relation_mappings", []),
        data.get("node_table"),
        data.get("edge_table"),
    )


def main():
    parser = argparse.ArgumentParser(description="Generate SQL + YAML from parsed OWL ontology")
    parser.add_argument("--classes-json", required=True, help="Path to classes.json from parse_owl.py")
    parser.add_argument("--relations-json", required=True, help="Path to relations.json from parse_owl.py")
    parser.add_argument("--mappings-json", required=True, help="Path to mappings configuration JSON")
    parser.add_argument("--database", required=True, help="Target Snowflake database")
    parser.add_argument("--schema", required=True, help="Target Snowflake schema")
    parser.add_argument("--ontology-name", required=True, help="Short ontology identifier")
    parser.add_argument("--output-dir", required=True, help="Directory for generated files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load inputs
    with open(args.classes_json) as f:
        classes = json.load(f)
    with open(args.relations_json) as f:
        relations = json.load(f)

    class_mappings, rel_mappings, node_table, edge_table = load_mappings_file(args.mappings_json)

    print(f"Loaded {len(classes)} classes, {len(relations)} relations")
    print(f"Loaded {len(class_mappings)} class mappings, {len(rel_mappings)} relation mappings")

    # Generate metadata SQL
    metadata_sql = generate_metadata_sql(
        classes, relations, class_mappings, rel_mappings,
        args.database, args.schema, args.ontology_name,
    )
    meta_path = output_dir / "01_metadata_tables.sql"
    meta_path.write_text(metadata_sql)
    print(f"Wrote {meta_path}")

    # Generate views SQL
    views_sql = generate_views_sql(
        classes, relations, class_mappings, rel_mappings,
        args.database, args.schema, args.ontology_name,
        node_table=node_table, edge_table=edge_table,
    )
    views_path = output_dir / "02_abstract_views.sql"
    views_path.write_text(views_sql)
    print(f"Wrote {views_path}")

    # Generate semantic model YAML
    has_subclass = any(rm["rel_name"].lower() == "subclassof" for rm in rel_mappings)
    yaml_content = generate_semantic_model_yaml(
        classes, relations, class_mappings,
        args.database, args.schema, args.ontology_name,
        has_subclass_view=has_subclass,
        has_unified_view=len(class_mappings) > 1,
        has_stats_view=has_subclass,
    )
    yaml_path = output_dir / "03_ontology_semantic_model.yaml"
    yaml_path.write_text(yaml_content)
    print(f"Wrote {yaml_path}")

    print(f"\nGeneration complete. Review files in {output_dir}/ before deploying to Snowflake.")


if __name__ == "__main__":
    main()
