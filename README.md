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

This is a **Cortex Code skill** — you use it through natural-language prompts in [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code), not by running scripts directly. The skill handles parsing, mapping, code generation, and deployment for you.

**Prerequisites:** [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) with the `ontology-semantic-modeler` skill installed, a Snowflake account with CREATE TABLE/VIEW privileges, Cortex Analyst enabled.

### Example: Cell Ontology + PRISM Drug Data

The following walkthrough shows the exact prompts used to produce the artifacts in [`test/`](test/). Each prompt triggers one step of the skill's 6-step workflow.

---

**Prompt 1 — Kick off the skill and provide inputs**

> I have an OWL ontology file at `test/input/cell_ontology_prism.owl` that models the Cell Ontology hierarchy relevant to our PRISM drug screening data. I also have an existing semantic model at `test/input/prism_drug_efficacy.yaml` for the PRISM tables.
>
> I want to generate an ontology semantic model that bridges the cell type hierarchy with our Snowflake tables in `TEMP.ONTOLOGY_POC`. Use ontology name `CL_PRISM`. The source tables are `KG_NODE`, `KG_EDGE`, `PRISM_TREATMENTS`, `PRISM_CELL_LINES`, `PRISM_VIABILITY`, and `PRISM_TISSUE_TO_CL`.

The skill gathers your inputs (Step 1), then parses the OWL file (Step 2). It reports back:

> *Parsed 34 classes (11 abstract, 23 concrete), 4 object properties, max hierarchy depth 5. Root: Thing → BiomedicalEntity → CellType / AnatomicalEntity / Treatment / CellLine / ViabilityMeasurement.*

Output: `test/parsed/classes.json`, `test/parsed/relations.json`, `test/parsed/stats.json`

---

**Prompt 2 — Review and confirm mappings**

> Map CellType and AnatomicalEntity to `KG_NODE` with NODE_TYPE filters. Map Treatment to `PRISM_TREATMENTS`, CellLine to `PRISM_CELL_LINES`, ViabilityMeasurement to `PRISM_VIABILITY`. For relationships, map subClassOf to `KG_EDGE` filtered by `EDGE_TYPE = 'subClassOf'` and derives_from to `PRISM_TISSUE_TO_CL`.

The skill presents a mapping table for confirmation (Step 3), then generates all SQL and YAML artifacts (Step 4):

> *Generated 3 files: `01_metadata_tables.sql` (4 tables, 34 class rows), `02_abstract_views.sql` (10 views), `03_ontology_semantic_model.yaml` (6 semantic tables, 5 verified queries).*

Output: `test/generated/01_metadata_tables.sql`, `test/generated/02_abstract_views.sql`, `test/generated/03_ontology_semantic_model.yaml`

---

**Prompt 3 — Deploy**

> Deploy everything to Snowflake in `TEMP.ONTOLOGY_POC`.

The skill executes the SQL files in order and creates the semantic view (Step 5):

> *Created 4 metadata tables, 10 views, and semantic view `CL_PRISM_ONTOLOGY_SEMANTIC_VIEW` in `TEMP.ONTOLOGY_POC`.*

---

**Prompt 4 — Visualize (optional)**

> Show me the ontology visualization.

The skill launches the Streamlit app (Step 6) with an interactive class hierarchy tree, force-directed ontology graph, and coverage matrix.

---

See [`ontology-semantic-modeler/README.md`](ontology-semantic-modeler/README.md) for full documentation including architecture details and customization options.

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
