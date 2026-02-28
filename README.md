# Ontology Semantic Modeler — Cortex Code Skill

A [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) skill that generates Snowflake Cortex Analyst semantic models from OWL/RDF ontologies mapped to existing tables. Automates the bridge between domain ontologies (class hierarchies, object properties) and relational data so that Cortex Analyst can answer natural-language questions like *"What are all descendants of epithelial cell?"* using recursive CTEs it would otherwise have no knowledge of.

## Repository Structure

```
coco_skill/
├── ontology-semantic-modeler/      # The Cortex Code skill
│   ├── SKILL.md                    # Skill definition and 6-step workflow
│   ├── scripts/                    # Python scripts (parse, generate, visualize)
│   ├── assets/                     # Mapping template
│   └── references/                 # SQL/YAML templates and worked example
└── test/                           # End-to-end test with PRISM data
    ├── input/                      # OWL file, mappings JSON, baseline semantic model
    ├── parsed/                     # Parsed ontology JSON (34 classes, 4 relations)
    └── generated/                  # Generated SQL and semantic model YAML
```

## What It Does

Given an OWL/RDF ontology file and Snowflake tables containing domain data, the skill:

1. **Parses** the ontology into structured JSON (classes, relationships, hierarchy)
2. **Maps** OWL classes to physical Snowflake tables (with optional filter conditions for shared tables)
3. **Generates** three artifacts:
   - Metadata tables SQL (4 normalized tables capturing the ontology structure)
   - Abstract views SQL (hierarchy views, per-class entity views, unified entity view)
   - Cortex Analyst semantic model YAML (with verified queries for hierarchy traversal)
4. **Deploys** to Snowflake as a semantic view
5. **Visualizes** the ontology with an interactive Streamlit app (optional)

```
OWL file + Snowflake tables
    |
    v
parse_owl.py  -->  classes.json, relations.json
    |
    v
generate_artifacts.py  +  mappings.json
    |
    ├── 01_metadata_tables.sql
    ├── 02_abstract_views.sql
    └── 03_ontology_semantic_model.yaml
    |
    v
CREATE SEMANTIC VIEW  -->  Cortex Analyst queries
```

## Quick Start

**Prerequisites:** Python >= 3.10, [uv](https://docs.astral.sh/uv/), Snowflake account with CREATE TABLE/VIEW privileges, Cortex Analyst enabled.

```bash
# 1. Parse an OWL ontology
uv run --script ontology-semantic-modeler/scripts/parse_owl.py -- \
  --owl-file /path/to/ontology.owl \
  --output-dir /tmp/parsed

# 2. Fill in the mappings template (OWL classes -> Snowflake tables)
cp ontology-semantic-modeler/assets/mappings_template.json my_mappings.json
# edit my_mappings.json

# 3. Generate SQL + YAML artifacts
uv run --script ontology-semantic-modeler/scripts/generate_artifacts.py -- \
  --classes-json /tmp/parsed/classes.json \
  --relations-json /tmp/parsed/relations.json \
  --mappings-json my_mappings.json \
  --database MY_DB --schema MY_SCHEMA --ontology-name MY_ONT \
  --output-dir /tmp/generated

# 4. Deploy to Snowflake (run the two SQL files, then create the semantic view)

# 5. Visualize (optional)
uv run --script ontology-semantic-modeler/scripts/visualize_ontology.py -- \
  --classes-json /tmp/parsed/classes.json \
  --relations-json /tmp/parsed/relations.json \
  --semantic-model /tmp/generated/03_ontology_semantic_model.yaml
```

See [`ontology-semantic-modeler/README.md`](ontology-semantic-modeler/README.md) for full documentation.

## End-to-End Test

The [`test/`](test/) directory contains a complete test using a Cell Ontology (CL) subset mapped to the [PRISM drug repurposing dataset](https://www.theprismlab.org/) on Snowflake:

- **Input:** 34-class OWL hierarchy (14 tissue-specific cell types), 5 class mappings to `TEMP.ONTOLOGY_POC` tables, baseline PRISM semantic model
- **Output:** 4 metadata tables, 10 abstract views, semantic model with 5 verified queries
- **Enables queries like:**
  - "What are all descendants of epithelial cell?" (recursive CTE)
  - "Which entities have the most direct children?" (hub node identification)
  - "Show drug efficacy for all epithelial-derived cancers" (cohort expansion via hierarchy)

See [`test/README.md`](test/README.md) for reproduction steps and detailed artifact descriptions.

## Using as a Cortex Code Skill

Place the `ontology-semantic-modeler/` directory in your Cortex Code skills path. The skill provides a guided 6-step workflow via `SKILL.md` — gather inputs, parse OWL, map to tables, generate artifacts, deploy, visualize.

## License

Internal use.
