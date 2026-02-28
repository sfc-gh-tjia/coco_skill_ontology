# Ontology Semantic Modeler

A [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) skill that bridges OWL/RDF ontologies with Snowflake tables through Cortex Analyst semantic models. Given a domain ontology and existing Snowflake tables, it generates metadata tables, SQL views for hierarchy traversal, and a semantic model YAML — enabling natural-language queries like *"What are all descendants of CellType X?"* through Cortex Analyst.

## Problem

Domain ontologies (OWL/RDF) encode rich class hierarchies and relationships, but querying them against relational data requires hand-written recursive CTEs, manual view layering, and deep knowledge of both the ontology and the physical schema. This skill automates that bridge.

## How It Works

```
OWL/RDF file + Snowflake tables
        |
        v
   parse_owl.py          --> classes.json, relations.json, stats.json
        |
        v
   mappings.json          <-- user maps OWL classes to tables
        |
        v
   generate_artifacts.py  --> 01_metadata_tables.sql
                              02_abstract_views.sql
                              03_ontology_semantic_model.yaml
        |
        v
   Deploy to Snowflake    --> CREATE SEMANTIC VIEW
        |
        v
   visualize_ontology.py  --> interactive Streamlit dashboard (optional)
```

## Project Structure

```
ontology-semantic-modeler/
├── SKILL.md                                  # Cortex Code skill definition (6-step workflow)
├── assets/
│   └── mappings_template.json                # Blank OWL-to-table mapping template
├── references/
│   ├── metadata_tables_template.sql          # SQL template: 4 ontology metadata tables
│   ├── abstract_views_template.sql           # SQL template: hierarchy & entity views
│   ├── semantic_model_template.yaml          # YAML template: Cortex Analyst semantic model
│   └── example_biomed_output/
│       └── biomed_mappings.json              # Worked example (biomedical domain)
└── scripts/
    ├── parse_owl.py                          # OWL/RDF parser -> structured JSON
    ├── generate_artifacts.py                 # JSON + mappings -> SQL + YAML artifacts
    └── visualize_ontology.py                 # Streamlit visualization app
```

## Prerequisites

- **Python** >= 3.10
- **[uv](https://docs.astral.sh/uv/)** — used to run scripts with inline dependency resolution (PEP 723). No `pyproject.toml` or virtual environment setup required.
- **Snowflake** account with `CREATE TABLE` and `CREATE VIEW` privileges on the target schema
- **Cortex Analyst** enabled for semantic view creation

## Quick Start

### 1. Parse an OWL ontology

```bash
uv run --script scripts/parse_owl.py -- \
  --owl-file /path/to/ontology.owl \
  --output-dir /tmp/ontology_parsed
```

Outputs `classes.json`, `relations.json`, `individuals.json`, and `stats.json` to the output directory. Supports `.owl` (OWL/XML), `.rdf` (RDF/XML), and `.ttl` (Turtle) formats with auto-detection.

**Options:**
- `--format` — Override format auto-detection (`xml`, `turtle`, `n3`, `nt`)
- `--exclude-deprecated` — Skip deprecated OWL classes
- `--namespace-filter` — Only include classes from a specific namespace prefix

### 2. Create a mappings file

Copy `assets/mappings_template.json` and fill in your OWL class-to-table mappings. See `references/example_biomed_output/biomed_mappings.json` for a complete example.

Each class mapping specifies:

| Field | Description |
|---|---|
| `class_name` | OWL class name (must match parsed output) |
| `source_table` | Fully-qualified Snowflake table (`DB.SCHEMA.TABLE`) |
| `filter_condition` | Optional WHERE clause when multiple classes share one table |
| `id_column` | Primary key column |
| `name_column` | Display name column |
| `description_column` | Description column (nullable) |

Each relation mapping specifies the edge source table with `src_column` and `dst_column`.

### 3. Generate SQL and YAML artifacts

```bash
uv run --script scripts/generate_artifacts.py -- \
  --classes-json /tmp/ontology_parsed/classes.json \
  --relations-json /tmp/ontology_parsed/relations.json \
  --mappings-json /path/to/my_mappings.json \
  --database MY_DATABASE \
  --schema MY_SCHEMA \
  --ontology-name DOMAIN \
  --output-dir /tmp/generated
```

Produces three files:

| File | Contents |
|---|---|
| `01_metadata_tables.sql` | `CREATE TABLE` + idempotent `INSERT` for `ONT_CLASS`, `ONT_RELATION_DEF`, `ONT_CLASS_MAPPING`, `ONT_RELATION_MAPPING` |
| `02_abstract_views.sql` | `CREATE OR REPLACE VIEW` for hierarchy views, per-class entity views, unified entity view, and stats views |
| `03_ontology_semantic_model.yaml` | Cortex Analyst semantic model with verified queries for hierarchy traversal |

### 4. Deploy to Snowflake

Execute the generated SQL files in order, then create the semantic view:

```sql
-- Run 01_metadata_tables.sql
-- Run 02_abstract_views.sql

CREATE OR REPLACE SEMANTIC VIEW MY_DATABASE.MY_SCHEMA.DOMAIN_ONTOLOGY_SEMANTIC_VIEW
  AS SEMANTIC MODEL '<contents of 03_ontology_semantic_model.yaml>';
```

### 5. Visualize (optional)

```bash
uv run --script scripts/visualize_ontology.py -- \
  --classes-json /tmp/ontology_parsed/classes.json \
  --relations-json /tmp/ontology_parsed/relations.json \
  --semantic-model /tmp/generated/03_ontology_semantic_model.yaml
```

The Streamlit app provides three tabs:

- **Class Hierarchy** — expandable tree view with search and ancestry path display
- **Ontology Graph** — force-directed graph with coverage-based coloring (green = mapped, blue = covered by ancestor, red = unmapped, gray = abstract)
- **Coverage Matrix** — breakdown of mapped, covered, and unmapped classes with progress bar

## Architecture

### 4-Table Metadata Pattern

The ontology structure is persisted in four normalized Snowflake tables:

| Table | Purpose |
|---|---|
| `ONT_CLASS` | OWL class hierarchy (name, parent, is_abstract, description) |
| `ONT_RELATION_DEF` | Object properties (domain/range, cardinality, transitivity) |
| `ONT_CLASS_MAPPING` | Maps each OWL class to a physical Snowflake table + filter |
| `ONT_RELATION_MAPPING` | Maps each OWL relationship to an edge table |

### Abstract View Layer

The semantic model references `VW_ONT_*` views rather than physical tables, providing a stable query interface:

- **`VW_ONT_SUBCLASS_OF`** — Resolved hierarchy edges with human-readable names
- **`VW_ONT_{ClassName}`** — Per-class entity views with standardized columns (`ID`, `ENTITY_TYPE`, `LABEL`, `DESCRIPTION`)
- **`VW_ONT_ALL_ENTITIES`** — `UNION ALL` across all entity views for polymorphic queries
- **`VW_DESCENDANTS` / `VW_ANCESTORS`** — Helpers for recursive CTE traversal
- **`VW_ONT_HIERARCHY_STATS`** — Direct children/parent counts per node

### Verified Query Patterns

The generated semantic model includes verified queries that Cortex Analyst can use as templates:

| Pattern | Description |
|---|---|
| `direct_children` | Simple `WHERE` on `PARENT_NAME` |
| `descendants_recursive` | Recursive CTE with configurable depth limit (default 10) |
| `most_children` | `GROUP BY` aggregation to find hub nodes |
| `entity_search` | `ILIKE` keyword search across entity labels |

### Shared Physical Tables

Multiple OWL classes can map to the same physical table differentiated by `filter_condition` (e.g., `NODE_TYPE = 'CellType'`). This is common in knowledge graph schemas where a single node table stores all entity types.

## Using as a Cortex Code Skill

This project is designed to run as a Cortex Code skill. The `SKILL.md` file defines the skill metadata and a guided 6-step workflow:

1. **Gather inputs** — OWL file path, target DB.SCHEMA, source tables, ontology name
2. **Parse OWL** — Run `parse_owl.py`
3. **Map ontology to tables** — Match OWL classes to Snowflake tables, confirm with user
4. **Generate artifacts** — Run `generate_artifacts.py` or generate manually
5. **Deploy to Snowflake** — Execute SQL, create semantic view
6. **Visualize** — Launch Streamlit app (optional)

To install the skill, place the `ontology-semantic-modeler/` directory in your Cortex Code skills path.

## Example: Biomedical Domain

The `references/example_biomed_output/biomed_mappings.json` file shows a complete mapping for a biomedical ontology with 6 classes and 3 relationships:

**Classes:** CellType, AnatomicalEntity, GeneOntologyTerm, Treatment, CellLine, ViabilityMeasurement

**Relationships:** subClassOf, derives_from, tested_on

Key patterns demonstrated:
- Multiple OWL classes (`CellType`, `AnatomicalEntity`, `GeneOntologyTerm`) sharing one `KG_NODE` table with different `NODE_TYPE` filters
- Separate domain tables (`PRISM_TREATMENTS`, `PRISM_CELL_LINES`, `PRISM_VIABILITY`) for operational classes
- Composite ID expressions (`ROW_NAME || '::' || COLUMN_NAME`) for tables without a single primary key

## Customization

| Option | Default | Description |
|---|---|---|
| Class filtering | All non-deprecated | Filter by namespace, depth, or explicit list |
| View prefix | `VW_ONT_` | Customizable naming convention |
| Hierarchy depth limit | 10 | Max recursion depth for descendant CTEs |
| Semantic model name | `{NAME}_ONTOLOGY_SEMANTIC_VIEW` | Customizable |
| Verified queries | 5 built-in patterns | Add domain-specific query templates |

## Troubleshooting

| Issue | Resolution |
|---|---|
| OWL parse failure | Check file format — parser supports OWL/XML, Turtle, and RDF/XML. Use `--format` to override auto-detection. |
| No table matches | Provide explicit mappings. Not all OWL classes need physical tables — abstract classes are structural. |
| SQL execution errors | Check `CREATE TABLE` / `CREATE VIEW` grants on the target schema. |
| Empty views | Verify `filter_condition` values in mappings match actual data in the source tables. |

## License

Internal use.
