# Ontology Semantic Modeler — End-to-End Test

End-to-end test of the `ontology-semantic-modeler` Cortex Code skill using a Cell Ontology (CL) subset mapped to the PRISM drug repurposing dataset on Snowflake.

## What This Tests

This test exercises the full 6-step skill workflow (as defined in `../ontology-semantic-modeler/SKILL.md`):

1. **Gather Inputs** — OWL file, mappings JSON, baseline semantic model YAML
2. **Parse OWL** — Extract class hierarchy, relationships, and statistics
3. **Map Ontology to Tables** — Verify OWL classes align with Snowflake tables
4. **Generate Artifacts** — Produce metadata SQL, abstract views SQL, and semantic model YAML
5. **Deploy to Snowflake** — Execute against `TEMP.ONTOLOGY_POC`, create semantic view
6. **Visualize** — Optional Streamlit visualization

## Directory Structure

```
test/
├── README.md
├── input/                                  # Test inputs (created manually)
│   ├── cell_ontology_prism.owl             # OWL file: Cell Ontology subset for PRISM
│   ├── cell_ontology_prism.ttl             # Turtle format (alternative)
│   ├── prism_biomed_mappings.json          # OWL class → Snowflake table mappings
│   └── prism_drug_efficacy.yaml            # Baseline PRISM semantic model (no ontology)
├── parsed/                                 # Step 2 output (from parse_owl.py)
│   ├── classes.json                        # 34 parsed OWL classes
│   ├── relations.json                      # 4 parsed object properties
│   ├── individuals.json                    # Named individuals (empty for this ontology)
│   └── stats.json                          # Ontology summary statistics
└── generated/                              # Step 4 output (from generate_artifacts.py)
    ├── 01_metadata_tables.sql              # ONT_CLASS, ONT_RELATION_DEF, ONT_CLASS_MAPPING, ONT_RELATION_MAPPING
    ├── 02_abstract_views.sql               # VW_ONT_* views (hierarchy, entity, unified, stats)
    ├── 03_ontology_semantic_model.yaml     # Cortex Analyst semantic model (unprefixed view names)
    └── 03_ontology_semantic_model_prefixed.yaml  # Prefixed variant (TEST_COCO_SKILL_VW_ONT_*)
```

## Input Files

### `input/cell_ontology_prism.owl`

OWL/XML file representing a subset of the [Cell Ontology](http://obofoundry.org/ontology/cl.html) relevant to PRISM data. Contains:

- **34 classes** across 5 hierarchy levels (11 abstract, 23 concrete)
- **Root:** `Thing` → `BiomedicalEntity` → branches: `CellType`, `AnatomicalEntity`, `Treatment`, `CellLine`, `ViabilityMeasurement`
- **Cell type hierarchy:** `CellType` → major lineages (epithelial, neural, connective tissue, leukocyte, secretory, progenitor) → sub-lineages → tissue-specific leaf types
- **14 tissue-specific leaf classes** mapped to PRISM `PRIMARY_TISSUE` values:

| OWL Class | PRISM Tissue |
|---|---|
| Hepatocyte | liver |
| Melanocyte | skin |
| OsteosarcomaCell | bone |
| BreastEpithelialCell | breast |
| LungEpithelialCell | lung |
| GastricEpithelialCell | gastric |
| KidneyEpithelialCell | kidney |
| OvarianEpithelialCell | ovary |
| ThyroidEpithelialCell | thyroid |
| ColonicEpithelialCell | colorectal |
| EsophagealEpithelialCell | esophagus |
| UterineEpithelialCell | uterus |
| PancreaticEpithelialCell | pancreas |
| NeuralCrestCell | central_nervous_system |

- **4 object properties:** `subClassOf` (transitive, hierarchical), `hasSubClass` (inverse), `derives_from` (tissue→cell type), `part_of` (transitive, hierarchical, anatomical containment)

### `input/prism_drug_efficacy.yaml`

Baseline Cortex Analyst semantic model for the PRISM dataset (no ontology layer). Contains:

- **3 tables:** TREATMENTS, CELL_LINES, VIABILITY
- **16 dimensions** (drug metadata, cell line info, viability keys)
- **2 facts:** DOSE, LOGFOLD_CHANGE
- **6 metrics:** AVG_EFFICACY, BEST_RESPONSE, CELL_LINES_TESTED, DRUGS_TESTED, MEASUREMENTS, RESPONSE_VARIABILITY
- **7 filters:** launched_drugs, clinical_phase_drugs, kinase_inhibitors, bcl_inhibitors, lung_cancer, breast_cancer, liver_cancer
- **2 relationships:** viability→treatments (many_to_one), viability→cell_lines (many_to_one)
- **5 verified queries:** effective drugs by tissue, MOA efficacy comparison, tissue sensitivity, kinase inhibitors for lung, launched drug efficacy

### `input/prism_biomed_mappings.json`

Maps OWL classes to physical Snowflake tables in `TEMP.ONTOLOGY_POC`:

| OWL Class | Source Table | Filter | ID Column |
|---|---|---|---|
| CellType | KG_NODE | `NODE_TYPE IN ('CellType', 'cl')` | NODE_ID |
| AnatomicalEntity | KG_NODE | `NODE_TYPE = 'AnatomicalEntity'` | NODE_ID |
| Treatment | PRISM_TREATMENTS | — | BROAD_ID |
| CellLine | PRISM_CELL_LINES | — | DEPMAP_ID |
| ViabilityMeasurement | PRISM_VIABILITY | — | `ROW_NAME \|\| '::' \|\| COLUMN_NAME` |

Relationship mappings:

| Relationship | Source Table | Src Column | Dst Column | Filter |
|---|---|---|---|---|
| subClassOf | KG_EDGE | SRC_ID | DST_ID | `EDGE_TYPE = 'subClassOf'` |
| derives_from | PRISM_TISSUE_TO_CL | PRIMARY_TISSUE | CL_NODE_ID | — |

Key patterns demonstrated:
- Multiple OWL classes sharing one table (`KG_NODE`) with different `NODE_TYPE` filters
- Composite ID expression for ViabilityMeasurement
- Separate domain tables for operational classes (PRISM_TREATMENTS, PRISM_CELL_LINES)

## Parsed Output

### `parsed/stats.json` — Summary

| Metric | Value |
|---|---|
| Total classes | 34 |
| Abstract classes | 11 |
| Concrete classes | 23 |
| Root classes | 1 (Thing) |
| Max hierarchy depth | 5 |
| Total relations | 4 |
| Hierarchical relations | 2 (subClassOf, part_of) |
| Transitive relations | 2 (subClassOf, part_of) |
| Namespace | `http://purl.obolibrary.org/obo/cl` |

## Generated Artifacts

### `generated/01_metadata_tables.sql`

Creates and populates 4 metadata tables in `TEMP.ONTOLOGY_POC`:

- **ONT_CLASS** — 34 rows (full class hierarchy with parent references and abstract flags)
- **ONT_RELATION_DEF** — 4 rows (subClassOf, hasSubClass, derives_from, part_of)
- **ONT_CLASS_MAPPING** — 5 rows (one per mapped concrete class)
- **ONT_RELATION_MAPPING** — 2 rows (subClassOf → KG_EDGE, derives_from → PRISM_TISSUE_TO_CL)

All INSERTs use idempotent `WHERE NOT EXISTS` guards. All CREATEs use `IF NOT EXISTS`.

### `generated/02_abstract_views.sql`

Creates 10 views in `TEMP.ONTOLOGY_POC`:

| View | Purpose |
|---|---|
| `VW_ONT_SUBCLASS_OF` | Resolved subClassOf edges with human-readable names (JOINs KG_EDGE with KG_NODE) |
| `VW_DESCENDANTS` | Helper for descendant traversal (recursive CTE base) |
| `VW_ANCESTORS` | Helper for ancestor traversal (inverse direction) |
| `VW_ONT_CELLTYPE` | Cell type entities from KG_NODE (filtered by NODE_TYPE) |
| `VW_ONT_ANATOMICALENTITY` | Anatomical entities from KG_NODE |
| `VW_ONT_TREATMENT` | Treatments from PRISM_TREATMENTS |
| `VW_ONT_CELLLINE` | Cell lines from PRISM_CELL_LINES |
| `VW_ONT_VIABILITYMEASUREMENT` | Viability measurements from PRISM_VIABILITY |
| `VW_ONT_ALL_ENTITIES` | Unified UNION ALL across all 5 entity views |
| `VW_ONT_HIERARCHY_STATS` | Direct children/parent counts per node |

### `generated/03_ontology_semantic_model.yaml`

Cortex Analyst semantic model (`CL_PRISM_ONTOLOGY_SEMANTIC_VIEW`) with:

- **6 tables:** VW_ONT_CELLTYPE, VW_ONT_ANATOMICALENTITY, VW_ONT_TREATMENT, VW_ONT_CELLLINE, VW_ONT_VIABILITYMEASUREMENT, VW_ONT_SUBCLASS_OF
- **5 verified queries:**
  - `list_entity_types` — List cell types in the ontology
  - `direct_children` — Direct children of a given entity
  - `direct_parents` — Parents of a given entity
  - `descendants_recursive` — All descendants via recursive CTE (depth limit 10)
  - `most_children` — Entities with the most direct children

### `generated/03_ontology_semantic_model_prefixed.yaml`

Same semantic model with `TEST_COCO_SKILL_` prefix on all view names and fully-qualified table references. Used for deployment to avoid name collisions during testing.

## Deployment Target

- **Snowflake schema:** `TEMP.ONTOLOGY_POC`
- **Semantic view name:** `CL_PRISM_ONTOLOGY_SEMANTIC_VIEW` (or `TEST_COCO_SKILL_CL_PRISM_ONTOLOGY_SEMANTIC_VIEW` for prefixed variant)
- **Source tables required:**
  - `TEMP.ONTOLOGY_POC.KG_NODE` — Knowledge graph node table
  - `TEMP.ONTOLOGY_POC.KG_EDGE` — Knowledge graph edge table
  - `TEMP.ONTOLOGY_POC.PRISM_TREATMENTS` — Drug/compound metadata
  - `TEMP.ONTOLOGY_POC.PRISM_CELL_LINES` — Cancer cell line metadata
  - `TEMP.ONTOLOGY_POC.PRISM_VIABILITY` — Drug efficacy measurements (logfold change)
  - `TEMP.ONTOLOGY_POC.PRISM_TISSUE_TO_CL` — Tissue-to-cell-type mapping

## Reproducing the Test

This test is designed to be reproduced through natural-language prompts in [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) using the `ontology-semantic-modeler` skill. The prompts below produce all the artifacts in this directory.

### Prompt 1 — Provide inputs and parse the ontology (Steps 1-2)

> I have an OWL ontology at `test/input/cell_ontology_prism.owl` modeling the Cell Ontology hierarchy for our PRISM drug screening data. I also have a baseline semantic model at `test/input/prism_drug_efficacy.yaml`.
>
> Generate an ontology semantic model that bridges the cell type hierarchy with our Snowflake tables in `TEMP.ONTOLOGY_POC`. Use ontology name `CL_PRISM`. Source tables: `KG_NODE`, `KG_EDGE`, `PRISM_TREATMENTS`, `PRISM_CELL_LINES`, `PRISM_VIABILITY`, `PRISM_TISSUE_TO_CL`.

**Expected result:** Parses 34 classes (11 abstract, 23 concrete), 4 object properties, max hierarchy depth 5.

**Output:** `parsed/classes.json`, `parsed/relations.json`, `parsed/stats.json`

### Prompt 2 — Confirm mappings and generate artifacts (Steps 3-4)

> Map CellType and AnatomicalEntity to `KG_NODE` with NODE_TYPE filters. Map Treatment to `PRISM_TREATMENTS`, CellLine to `PRISM_CELL_LINES`, ViabilityMeasurement to `PRISM_VIABILITY`. For relationships, map subClassOf to `KG_EDGE` filtered by `EDGE_TYPE = 'subClassOf'`, and derives_from to `PRISM_TISSUE_TO_CL`.

**Expected result:** Generates 3 files — metadata tables SQL (4 tables, 34 class rows), abstract views SQL (10 views), semantic model YAML (6 tables, 5 verified queries).

**Output:** `generated/01_metadata_tables.sql`, `generated/02_abstract_views.sql`, `generated/03_ontology_semantic_model.yaml`

### Prompt 3 — Deploy to Snowflake (Step 5)

> Deploy everything to Snowflake in `TEMP.ONTOLOGY_POC`.

**Expected result:** Creates 4 metadata tables, 10 views, and semantic view `CL_PRISM_ONTOLOGY_SEMANTIC_VIEW` in `TEMP.ONTOLOGY_POC`.

### Prompt 4 — Visualize (Step 6, optional)

> Show me the ontology visualization.

**Expected result:** Launches Streamlit app with class hierarchy tree, force-directed ontology graph, and coverage matrix.

## Expected Queries Enabled

The deployed ontology semantic model enables natural-language queries through Cortex Analyst such as:

- **"What are all descendants of epithelial cell?"** — Recursive CTE traversal returning glandular, squamous, lung, breast, gastric, kidney, ovarian, thyroid, colonic, esophageal, uterine, pancreatic epithelial cells and hepatocyte
- **"What cell types are related to lung cancer?"** — Hierarchy traversal from LungEpithelialCell up through EpithelialCell → CellType
- **"Which entities have the most direct children?"** — Hub node identification (CellType and EpithelialCell expected to rank highest)
- **"Show drug efficacy for all epithelial-derived cancers"** — When combined with the baseline `prism_drug_efficacy.yaml` semantic model, enables cohort expansion via descendant lookup joined to viability data
