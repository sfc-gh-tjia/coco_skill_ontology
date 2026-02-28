-- ============================================================================
-- Ontology Metadata Tables for CL_PRISM
-- Generated: 2026-02-24 04:19 UTC
-- ============================================================================

USE SCHEMA TEMP.ONTOLOGY_POC;

-- ONT_CLASS: Class hierarchy from OWL
CREATE TABLE IF NOT EXISTS ONT_CLASS (
    CLASS_NAME          STRING NOT NULL PRIMARY KEY,
    PARENT_CLASS_NAME   STRING,
    IS_ABSTRACT         BOOLEAN DEFAULT FALSE,
    DESCRIPTION         STRING,
    ONTOLOGY_NAME       STRING DEFAULT 'CL_PRISM',
    TYPE_CLASS          STRING DEFAULT 'ANALYTICAL',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO ONT_CLASS (CLASS_NAME, PARENT_CLASS_NAME, IS_ABSTRACT, DESCRIPTION, ONTOLOGY_NAME, TYPE_CLASS)
SELECT * FROM VALUES
    ('AnatomicalEntity', 'BiomedicalEntity', TRUE, 'An anatomical structure or region in the body.', 'CL_PRISM', 'ANALYTICAL'),
    ('BiomedicalEntity', 'Thing', TRUE, 'Abstract superclass for all biomedical domain concepts.', 'CL_PRISM', 'ANALYTICAL'),
    ('BreastEpithelialCell', 'GlandularEpithelialCell', FALSE, 'An epithelial cell of the mammary gland. Maps to PRISM PRIMARY_TISSUE=''breast''.', 'CL_PRISM', 'OPERATIONAL'),
    ('CellLine', 'BiomedicalEntity', FALSE, 'A cancer cell line used in the PRISM drug screen.', 'CL_PRISM', 'OPERATIONAL'),
    ('CellType', 'BiomedicalEntity', TRUE, 'A cell type defined in the Cell Ontology (CL). Represents a class of cells sharing common characteristics.', 'CL_PRISM', 'ANALYTICAL'),
    ('ColonicEpithelialCell', 'EpithelialCell', FALSE, 'An epithelial cell of the colon. Maps to PRISM PRIMARY_TISSUE=''colorectal''.', 'CL_PRISM', 'OPERATIONAL'),
    ('ConnectiveTissueCell', 'CellType', TRUE, 'A cell that is part of connective tissue.', 'CL_PRISM', 'ANALYTICAL'),
    ('EpithelialCell', 'CellType', TRUE, 'A cell that is usually found in a two-dimensional sheet with a free surface. Epithelial cells line body surfaces and cavities.', 'CL_PRISM', 'ANALYTICAL'),
    ('EsophagealEpithelialCell', 'SquamousEpithelialCell', FALSE, 'A squamous epithelial cell of the esophagus. Maps to PRISM PRIMARY_TISSUE=''esophagus''.', 'CL_PRISM', 'OPERATIONAL'),
    ('Fibroblast', 'ConnectiveTissueCell', FALSE, 'A connective tissue cell which secretes an extracellular matrix rich in collagen and other macromolecules.', 'CL_PRISM', 'OPERATIONAL'),
    ('GastricEpithelialCell', 'GlandularEpithelialCell', FALSE, 'An epithelial cell of the stomach. Maps to PRISM PRIMARY_TISSUE=''gastric''.', 'CL_PRISM', 'OPERATIONAL'),
    ('GlandularEpithelialCell', 'EpithelialCell', TRUE, 'An epithelial cell that is part of a gland and is specialized for secretion.', 'CL_PRISM', 'ANALYTICAL'),
    ('Hepatocyte', 'GlandularEpithelialCell', FALSE, 'The main structural component of the liver. Maps to PRISM PRIMARY_TISSUE=''liver''.', 'CL_PRISM', 'OPERATIONAL'),
    ('KidneyEpithelialCell', 'EpithelialCell', FALSE, 'An epithelial cell of the kidney. Maps to PRISM PRIMARY_TISSUE=''kidney''.', 'CL_PRISM', 'OPERATIONAL'),
    ('Leukocyte', 'CellType', TRUE, 'An achromatic cell of the myeloid or lymphoid lineages capable of ameboid movement, found in blood or other tissue.', 'CL_PRISM', 'ANALYTICAL'),
    ('LungEpithelialCell', 'EpithelialCell', FALSE, 'An epithelial cell of the lung. Maps to PRISM PRIMARY_TISSUE=''lung''.', 'CL_PRISM', 'OPERATIONAL'),
    ('Lymphocyte', 'Leukocyte', FALSE, 'A cell of the lymphoid lineage including T cells, B cells, and NK cells.', 'CL_PRISM', 'OPERATIONAL'),
    ('Melanocyte', 'NeuralCell', FALSE, 'A pigment cell derived from the neural crest. Maps to PRISM PRIMARY_TISSUE=''skin''.', 'CL_PRISM', 'OPERATIONAL'),
    ('MyeloidCell', 'Leukocyte', FALSE, 'A cell of the myeloid lineage, including granulocytes, monocytes, macrophages, and dendritic cells.', 'CL_PRISM', 'OPERATIONAL'),
    ('NeuralCell', 'CellType', TRUE, 'A cell that is part of the nervous system.', 'CL_PRISM', 'ANALYTICAL'),
    ('NeuralCrestCell', 'NeuralCell', FALSE, 'A cell derived from the neural crest that migrates to various tissues. Maps to PRISM PRIMARY_TISSUE=''central_nervous_system''.', 'CL_PRISM', 'OPERATIONAL'),
    ('Osteoblast', 'ConnectiveTissueCell', TRUE, 'A bone-forming cell which secretes the organic matrix of bone (osteoid).', 'CL_PRISM', 'ANALYTICAL'),
    ('OsteosarcomaCell', 'Osteoblast', FALSE, 'A malignant osteoblast-derived cell. Maps to PRISM PRIMARY_TISSUE=''bone''.', 'CL_PRISM', 'OPERATIONAL'),
    ('OvarianEpithelialCell', 'EpithelialCell', FALSE, 'An epithelial cell of the ovary. Maps to PRISM PRIMARY_TISSUE=''ovary''.', 'CL_PRISM', 'OPERATIONAL'),
    ('PancreaticEpithelialCell', 'GlandularEpithelialCell', FALSE, 'An epithelial cell of the pancreas. Maps to PRISM PRIMARY_TISSUE=''pancreas''.', 'CL_PRISM', 'OPERATIONAL'),
    ('ProgenitorCell', 'CellType', FALSE, 'A cell that retains the ability to divide and can differentiate into a limited range of cell types.', 'CL_PRISM', 'OPERATIONAL'),
    ('SecretoryCell', 'CellType', FALSE, 'A cell whose primary function is the production and release of substances.', 'CL_PRISM', 'OPERATIONAL'),
    ('SquamousEpithelialCell', 'EpithelialCell', TRUE, 'A flat, scale-like epithelial cell found lining surfaces subject to abrasion.', 'CL_PRISM', 'ANALYTICAL'),
    ('Thing', NULL, TRUE, 'Root class of all entities.', 'CL_PRISM', 'ANALYTICAL'),
    ('ThyroidEpithelialCell', 'GlandularEpithelialCell', FALSE, 'An epithelial cell of the thyroid gland. Maps to PRISM PRIMARY_TISSUE=''thyroid''.', 'CL_PRISM', 'OPERATIONAL'),
    ('Tissue', 'AnatomicalEntity', FALSE, 'A tissue type that maps to PRISM PRIMARY_TISSUE values.', 'CL_PRISM', 'OPERATIONAL'),
    ('Treatment', 'BiomedicalEntity', FALSE, 'A drug or compound used in the PRISM drug screen.', 'CL_PRISM', 'OPERATIONAL'),
    ('UterineEpithelialCell', 'EpithelialCell', FALSE, 'An epithelial cell of the uterus. Maps to PRISM PRIMARY_TISSUE=''uterus''.', 'CL_PRISM', 'OPERATIONAL'),
    ('ViabilityMeasurement', 'BiomedicalEntity', FALSE, 'A drug efficacy measurement (logfold change) from the PRISM screen.', 'CL_PRISM', 'OPERATIONAL')
AS t(CLASS_NAME, PARENT_CLASS_NAME, IS_ABSTRACT, DESCRIPTION, ONTOLOGY_NAME, TYPE_CLASS)
WHERE NOT EXISTS (SELECT 1 FROM ONT_CLASS WHERE CLASS_NAME = t.CLASS_NAME);

-- ONT_RELATION_DEF: Relationship definitions from OWL properties
CREATE TABLE IF NOT EXISTS ONT_RELATION_DEF (
    REL_NAME            STRING NOT NULL PRIMARY KEY,
    DOMAIN_CLASS        STRING NOT NULL,
    RANGE_CLASS         STRING NOT NULL,
    CARDINALITY         STRING DEFAULT 'N:N',
    IS_HIERARCHICAL     BOOLEAN DEFAULT FALSE,
    IS_TRANSITIVE       BOOLEAN DEFAULT FALSE,
    INVERSE_REL_NAME    STRING,
    DESCRIPTION         STRING,
    ONTOLOGY_NAME       STRING DEFAULT 'CL_PRISM',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO ONT_RELATION_DEF (REL_NAME, DOMAIN_CLASS, RANGE_CLASS, CARDINALITY, IS_HIERARCHICAL, IS_TRANSITIVE, INVERSE_REL_NAME, DESCRIPTION)
SELECT * FROM VALUES
    ('derives_from', 'Tissue', 'CellType', 'N:N', FALSE, FALSE, NULL, 'Maps a tissue type to a cell ontology class. Used to bridge PRISM PRIMARY_TISSUE values to the Cell Ontology hierarchy.'),
    ('hasSubClass', 'Thing', 'Thing', 'N:N', FALSE, FALSE, NULL, 'Inverse of subClassOf.'),
    ('part_of', 'AnatomicalEntity', 'AnatomicalEntity', 'N:N', TRUE, TRUE, NULL, 'Anatomical containment. X part_of Y means X is a structural component of Y.'),
    ('subClassOf', 'Thing', 'Thing', 'N:N', TRUE, TRUE, 'hasSubClass', 'Taxonomic subsumption (is-a hierarchy). A subClassOf B means every instance of A is also an instance of B.')
AS t(REL_NAME, DOMAIN_CLASS, RANGE_CLASS, CARDINALITY, IS_HIERARCHICAL, IS_TRANSITIVE, INVERSE_REL_NAME, DESCRIPTION)
WHERE NOT EXISTS (SELECT 1 FROM ONT_RELATION_DEF WHERE REL_NAME = t.REL_NAME);

-- ONT_CLASS_MAPPING: Map OWL classes to physical Snowflake tables
CREATE TABLE IF NOT EXISTS ONT_CLASS_MAPPING (
    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,
    CLASS_NAME          STRING NOT NULL,
    SOURCE_TABLE        STRING NOT NULL,
    FILTER_CONDITION    STRING,
    ID_COLUMN           STRING NOT NULL,
    NAME_COLUMN         STRING,
    DESCRIPTION_COLUMN  STRING,
    PROPS_COLUMN        STRING,
    ONTOLOGY_NAME       STRING DEFAULT 'CL_PRISM',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (CLASS_NAME) REFERENCES ONT_CLASS(CLASS_NAME)
);

INSERT INTO ONT_CLASS_MAPPING (CLASS_NAME, SOURCE_TABLE, FILTER_CONDITION, ID_COLUMN, NAME_COLUMN, DESCRIPTION_COLUMN, PROPS_COLUMN)
SELECT * FROM VALUES
    ('CellType', 'TEMP.ONTOLOGY_POC.KG_NODE', 'NODE_TYPE IN (''CellType'', ''cl'')', 'NODE_ID', 'NAME', 'DESCRIPTION', 'PROPS'),
    ('AnatomicalEntity', 'TEMP.ONTOLOGY_POC.KG_NODE', 'NODE_TYPE = ''AnatomicalEntity''', 'NODE_ID', 'NAME', 'DESCRIPTION', 'PROPS'),
    ('Treatment', 'TEMP.ONTOLOGY_POC.PRISM_TREATMENTS', NULL, 'BROAD_ID', 'NAME', NULL, NULL),
    ('CellLine', 'TEMP.ONTOLOGY_POC.PRISM_CELL_LINES', NULL, 'DEPMAP_ID', 'CCLE_NAME', NULL, NULL),
    ('ViabilityMeasurement', 'TEMP.ONTOLOGY_POC.PRISM_VIABILITY', NULL, 'ROW_NAME || ''::'' || COLUMN_NAME', NULL, NULL, NULL)
AS t(CLASS_NAME, SOURCE_TABLE, FILTER_CONDITION, ID_COLUMN, NAME_COLUMN, DESCRIPTION_COLUMN, PROPS_COLUMN)
WHERE NOT EXISTS (SELECT 1 FROM ONT_CLASS_MAPPING WHERE CLASS_NAME = t.CLASS_NAME AND SOURCE_TABLE = t.SOURCE_TABLE);

-- ONT_RELATION_MAPPING: Map relationships to physical edge sources
CREATE TABLE IF NOT EXISTS ONT_RELATION_MAPPING (
    MAPPING_ID          STRING DEFAULT UUID_STRING() PRIMARY KEY,
    REL_NAME            STRING NOT NULL,
    SOURCE_TABLE        STRING NOT NULL,
    FILTER_CONDITION    STRING,
    SRC_COLUMN          STRING NOT NULL,
    DST_COLUMN          STRING NOT NULL,
    PROPS_COLUMN        STRING,
    ONTOLOGY_NAME       STRING DEFAULT 'CL_PRISM',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (REL_NAME) REFERENCES ONT_RELATION_DEF(REL_NAME)
);

INSERT INTO ONT_RELATION_MAPPING (REL_NAME, SOURCE_TABLE, FILTER_CONDITION, SRC_COLUMN, DST_COLUMN, PROPS_COLUMN)
SELECT * FROM VALUES
    ('subClassOf', 'TEMP.ONTOLOGY_POC.KG_EDGE', 'EDGE_TYPE = ''subClassOf''', 'SRC_ID', 'DST_ID', 'PROPS'),
    ('derives_from', 'TEMP.ONTOLOGY_POC.PRISM_TISSUE_TO_CL', NULL, 'PRIMARY_TISSUE', 'CL_NODE_ID', NULL)
AS t(REL_NAME, SOURCE_TABLE, FILTER_CONDITION, SRC_COLUMN, DST_COLUMN, PROPS_COLUMN)
WHERE NOT EXISTS (SELECT 1 FROM ONT_RELATION_MAPPING WHERE REL_NAME = t.REL_NAME AND SOURCE_TABLE = t.SOURCE_TABLE);
