# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "streamlit>=1.30.0",
#     "streamlit-agraph>=0.0.45",
#     "pyyaml>=6.0",
# ]
# ///
"""
Ontology Visualization App - Interactive exploration of parsed OWL ontology
and generated semantic model.

Usage:
    uv run --script visualize_ontology.py -- \
      --classes-json /tmp/parsed/classes.json \
      --relations-json /tmp/parsed/relations.json \
      --semantic-model /tmp/generated/03_ontology_semantic_model.yaml
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import streamlit as st
import yaml
from streamlit_agraph import agraph, Node, Edge, Config


def load_json(path: str) -> list | dict:
    with open(path) as f:
        return json.load(f)


def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_tree(classes: list[dict]) -> dict:
    """Build a parent->children tree structure."""
    children_map = defaultdict(list)
    roots = []
    name_to_cls = {}
    for cls in classes:
        name_to_cls[cls["name"]] = cls
        parent = cls.get("parent_name")
        if parent:
            children_map[parent].append(cls["name"])
        else:
            roots.append(cls["name"])
    return children_map, roots, name_to_cls


def render_tree_text(name: str, children_map: dict, name_to_cls: dict, depth: int = 0, max_depth: int = 6) -> str:
    """Render a text-based tree."""
    if depth > max_depth:
        return ""
    cls = name_to_cls.get(name, {})
    prefix = "  " * depth + ("|- " if depth > 0 else "")
    label = cls.get("label", name)
    abstract_tag = " [abstract]" if cls.get("is_abstract") else ""
    line = f"{prefix}{label}{abstract_tag}\n"
    for child in sorted(children_map.get(name, [])):
        line += render_tree_text(child, children_map, name_to_cls, depth + 1, max_depth)
    return line


def render_interactive_tree(name: str, children_map: dict, name_to_cls: dict,
                            depth: int = 0, max_depth: int = 6, search: str = "") -> None:
    """Render an interactive Streamlit tree with colored nodes and descriptions."""
    if depth > max_depth:
        return
    cls = name_to_cls.get(name, {})
    label = cls.get("label", name)
    is_abstract = cls.get("is_abstract", False)
    description = cls.get("description", "")
    kids = sorted(children_map.get(name, []))
    has_children = len(kids) > 0

    # Build the display label with icon and styling
    if is_abstract:
        icon = "🔹"
        display = f"{icon} **{label}**  `abstract`"
    else:
        icon = "🟢"
        display = f"{icon} {label}"

    # Highlight search matches
    if search and search.lower() in label.lower():
        display += "  🔍"

    indent_px = depth * 24

    if has_children:
        # Use expander for nodes with children, expanded by default at low depth
        with st.expander(display, expanded=(depth < 2)):
            if description:
                st.caption(description)
            for child in kids:
                render_interactive_tree(child, children_map, name_to_cls,
                                        depth + 1, max_depth, search)
    else:
        # Leaf node: render inline with indentation via markdown
        st.markdown(
            f'<div style="margin-left:{indent_px}px; padding:2px 0;">{display}</div>',
            unsafe_allow_html=True
        )
        if description and search and search.lower() in label.lower():
            st.markdown(
                f'<div style="margin-left:{indent_px + 16}px; color:gray; font-size:0.85em;">{description}</div>',
                unsafe_allow_html=True
            )


def build_coverage_map(classes: list[dict], sem_model: dict | None) -> dict[str, dict]:
    """Classify each OWL class by its coverage status relative to the semantic model.

    Returns a dict keyed by class name with values:
        status: 'mapped' | 'covered' | 'unmapped' | 'abstract'
        view_name: the semantic model view name (only for 'mapped')
        covering_ancestor: label of the ancestor whose view covers this class (only for 'covered')
    """
    result: dict[str, dict] = {}
    if not sem_model:
        for cls in classes:
            result[cls["name"]] = {"status": "abstract" if cls.get("is_abstract") else "unmapped"}
        return result

    tables_in_model = sem_model.get("tables", [])
    # Build suffix -> full view name mapping
    suffix_to_view: dict[str, str] = {}
    for tbl in tables_in_model:
        tname = tbl["name"]
        upper = tname.upper()
        if "VW_ONT_" in upper:
            suffix = upper.split("VW_ONT_", 1)[1]
            suffix_to_view[suffix] = tname

    name_to_cls = {c["name"]: c for c in classes}

    def get_matched_view(cls: dict) -> str | None:
        name_upper = cls["name"].upper()
        for suffix, view_name in suffix_to_view.items():
            if suffix == name_upper or suffix in name_upper or name_upper in suffix:
                return view_name
        return None

    def find_covering_ancestor(cls: dict) -> tuple[str, str] | None:
        """Returns (ancestor_label, ancestor_view_name) or None."""
        visited = set()
        current = cls.get("parent_name")
        while current and current not in visited:
            visited.add(current)
            parent_cls = name_to_cls.get(current)
            if parent_cls:
                view = get_matched_view(parent_cls)
                if view:
                    return (parent_cls.get("label", current), view)
                current = parent_cls.get("parent_name")
            else:
                break
        return None

    for cls in classes:
        view = get_matched_view(cls)
        if view:
            result[cls["name"]] = {"status": "mapped", "view_name": view}
        elif cls.get("is_abstract"):
            result[cls["name"]] = {"status": "abstract"}
        else:
            ancestor = find_covering_ancestor(cls)
            if ancestor:
                result[cls["name"]] = {
                    "status": "covered",
                    "covering_ancestor": ancestor[0],
                    "covering_view": ancestor[1],
                }
            else:
                result[cls["name"]] = {"status": "unmapped"}

    return result


def build_agraph_nodes_edges(classes: list[dict], relations: list[dict],
                              coverage_map: dict[str, dict],
                              max_nodes: int = 100,
                              show_relations: bool = True) -> tuple[list, list]:
    """Build streamlit-agraph Node and Edge lists with coverage coloring."""

    # Color scheme matching coverage status
    colors = {
        "mapped":   {"background": "#2ecc71", "border": "#27ae60", "font": "#ffffff"},
        "covered":  {"background": "#3498db", "border": "#2980b9", "font": "#ffffff"},
        "unmapped": {"background": "#e74c3c", "border": "#c0392b", "font": "#ffffff"},
        "abstract": {"background": "#ecf0f1", "border": "#95a5a6", "font": "#2c3e50"},
    }

    name_to_cls = {c["name"]: c for c in classes}
    nodes = []
    edges = []
    displayed = set()

    for cls in classes[:max_nodes]:
        name = cls["name"]
        label = cls.get("label", name)
        cov = coverage_map.get(name, {"status": "unmapped"})
        status = cov["status"]
        c = colors[status]

        # Build hover tooltip
        tooltip_parts = [f"<b>{label}</b>"]
        if cls.get("is_abstract"):
            tooltip_parts.append("<i>Abstract class</i>")
        if cls.get("description"):
            tooltip_parts.append(cls["description"][:150])
        tooltip_parts.append(f"<br/>Coverage: <b>{status.upper()}</b>")
        if status == "mapped":
            vn = cov.get("view_name", "")
            short = vn
            if "VW_ONT_" in vn.upper():
                short = "VW_ONT_" + vn.upper().split("VW_ONT_", 1)[1]
            tooltip_parts.append(f"View: <code>{short}</code>")
        elif status == "covered":
            tooltip_parts.append(f"Covered via: {cov.get('covering_ancestor', '?')}")
        tooltip = "<br/>".join(tooltip_parts)

        # Node shape: box for concrete, diamond for abstract
        shape = "diamond" if cls.get("is_abstract") else "box"

        nodes.append(Node(
            id=name,
            label=label,
            title=tooltip,
            color={"background": c["background"], "border": c["border"]},
            shape=shape,
            size=20 if cls.get("is_abstract") else 25,
            font={"color": c["font"], "size": 12},
            borderWidth=2,
        ))
        displayed.add(name)

    # subClassOf edges (hierarchy)
    for cls in classes[:max_nodes]:
        parent = cls.get("parent_name")
        if parent and cls["name"] in displayed:
            if parent not in displayed:
                # Add missing parent as a ghost node
                parent_cls = name_to_cls.get(parent, {})
                nodes.append(Node(
                    id=parent,
                    label=parent_cls.get("label", parent),
                    title=f"<b>{parent_cls.get('label', parent)}</b><br/><i>Not in visible set</i>",
                    color={"background": "#ecf0f1", "border": "#bdc3c7"},
                    shape="diamond",
                    size=18,
                    font={"color": "#95a5a6", "size": 11},
                    borderWidth=1,
                ))
                displayed.add(parent)
            edges.append(Edge(
                source=cls["name"],
                target=parent,
                color="#5dade2",
                label="subClassOf",
                width=1.5,
                arrows="to",
                dashes=False,
                font={"size": 8, "color": "#5dade2", "strokeWidth": 0},
            ))

    # Other relation edges
    if show_relations:
        for rel in relations:
            if rel["name"] == "subClassOf":
                continue
            domain = rel.get("domain_class", "")
            rng = rel.get("range_class", "")
            if domain in displayed and rng in displayed:
                edge_color = "#e67e22" if rel.get("is_hierarchical") else "#9b59b6"
                edges.append(Edge(
                    source=domain,
                    target=rng,
                    color=edge_color,
                    label=rel["name"],
                    width=1.0,
                    arrows="to",
                    dashes=True,
                    font={"size": 8, "color": edge_color, "strokeWidth": 0},
                ))

    return nodes, edges


def render_node_detail(cls_name: str, classes: list[dict], relations: list[dict],
                       coverage_map: dict[str, dict], sem_model: dict | None) -> None:
    """Render the detail inspector panel for a clicked node."""
    name_to_cls = {c["name"]: c for c in classes}
    cls = name_to_cls.get(cls_name)
    if not cls:
        st.warning(f"Class '{cls_name}' not found.")
        return

    label = cls.get("label", cls_name)
    cov = coverage_map.get(cls_name, {"status": "unmapped"})
    status = cov["status"]

    # --- Header with coverage badge ---
    badge_colors = {
        "mapped": "#2ecc71", "covered": "#3498db",
        "unmapped": "#e74c3c", "abstract": "#95a5a6",
    }
    badge_labels = {
        "mapped": "MAPPED TO VIEW", "covered": "COVERED AS ROWS",
        "unmapped": "UNMAPPED", "abstract": "ABSTRACT",
    }
    bc = badge_colors.get(status, "#95a5a6")
    bl = badge_labels.get(status, status.upper())
    st.markdown(
        f'<h3 style="margin-bottom:0;">{label}</h3>'
        f'<span style="background:{bc};color:white;padding:2px 10px;border-radius:10px;'
        f'font-size:0.75em;font-weight:bold;">{bl}</span>',
        unsafe_allow_html=True,
    )

    # Description
    if cls.get("description"):
        st.caption(cls["description"])

    st.divider()

    # --- Class info ---
    type_label = "Abstract" if cls.get("is_abstract") else "Concrete"
    st.markdown(f"**Type:** {type_label}")
    if cls.get("parent_name"):
        parent_cls = name_to_cls.get(cls["parent_name"], {})
        st.markdown(f"**Parent:** {parent_cls.get('label', cls['parent_name'])}")

    # Children
    children = [c for c in classes if c.get("parent_name") == cls_name]
    if children:
        child_labels = ", ".join(sorted(c.get("label", c["name"]) for c in children))
        st.markdown(f"**Children ({len(children)}):** {child_labels}")

    st.divider()

    # --- Snowflake Implementation ---
    st.markdown("#### Snowflake Implementation")

    # Find the subClassOf edge table in semantic model (used by multiple sections)
    subclass_table_info = None
    if sem_model:
        for tbl in sem_model.get("tables", []):
            if "SUBCLASS" in tbl["name"].upper():
                bt = tbl.get("base_table", {})
                subclass_table_info = {
                    "name": tbl["name"],
                    "fqn": f"{bt.get('database', '')}.{bt.get('schema', '')}.{bt.get('table', '')}",
                    "dims": tbl.get("dimensions", []),
                }
                break

    if status == "mapped":
        view_name = cov.get("view_name", "")
        short = view_name
        if "VW_ONT_" in view_name.upper():
            short = "VW_ONT_" + view_name.upper().split("VW_ONT_", 1)[1]
        st.markdown(f"**View:** `{short}`")

        # Find the table definition in the semantic model
        if sem_model:
            for tbl in sem_model.get("tables", []):
                if tbl["name"].upper() == view_name.upper():
                    bt = tbl.get("base_table", {})
                    fqn = f"{bt.get('database', '')}.{bt.get('schema', '')}.{bt.get('table', '')}"
                    st.markdown(f"**Base table:** `{fqn}`")

                    dims = tbl.get("dimensions", [])
                    if dims:
                        st.markdown("**Dimensions:**")
                        for d in dims:
                            desc = f" — {d['description']}" if d.get("description") else ""
                            st.markdown(f"- `{d['name']}` ({d.get('data_type', 'VARCHAR')}){desc}")

                    facts = tbl.get("facts", [])
                    if facts:
                        st.markdown("**Facts:**")
                        for f_item in facts:
                            st.markdown(f"- `{f_item['name']}` ({f_item.get('data_type', 'FLOAT')})")
                    break

    elif status == "covered":
        ancestor = cov.get("covering_ancestor", "?")
        covering_view = cov.get("covering_view", "")
        short_cv = covering_view
        if "VW_ONT_" in covering_view.upper():
            short_cv = "VW_ONT_" + covering_view.upper().split("VW_ONT_", 1)[1]
        st.markdown(f"**Covered by ancestor:** {ancestor}")
        st.markdown(f"**Ancestor's view:** `{short_cv}`")
        st.info(f"Rows for *{label}* exist as typed rows (ENTITY_TYPE column) within the ancestor's view.")

    elif status == "unmapped":
        st.error("No view or ancestor view covers this class.")
        st.caption("To add coverage, create a mapping in the ontology mappings file.")

    elif status == "abstract":
        st.markdown("**No dedicated view** — abstract classes are structural groupings.")
        if subclass_table_info:
            st.markdown(f"Appears as parent/child references in the hierarchy edge table:")
            st.markdown(f"- `{subclass_table_info['fqn']}`")
        if children:
            st.info(f"This class organizes {len(children)} child classes. "
                     "It exists in the hierarchy edge table as PARENT_NAME values.")
        else:
            st.info("Structural node with no children — leaf abstract class.")

    # --- Hierarchy edge (subClassOf) implementation ---
    if cls.get("parent_name") and subclass_table_info:
        st.divider()
        st.markdown("#### Hierarchy Edge (subClassOf)")
        st.markdown(f"**Edge table:** `{subclass_table_info['fqn']}`")
        parent_label = name_to_cls.get(cls["parent_name"], {}).get("label", cls["parent_name"])
        st.code(
            f"-- Row in edge table:\n"
            f"CHILD_NAME = '{label}'\n"
            f"PARENT_NAME = '{parent_label}'\n"
            f"REL_TYPE = 'subClassOf'",
            language="sql",
        )
        dim_names = [d["name"] for d in subclass_table_info.get("dims", [])]
        if dim_names:
            st.caption(f"Columns: {', '.join(dim_names)}")

    # --- Relations involving this class ---
    involved_rels = [r for r in relations
                     if r.get("domain_class") == cls_name or r.get("range_class") == cls_name]
    if involved_rels:
        st.divider()
        st.markdown("#### Relations")
        for r in involved_rels:
            direction = "domain" if r.get("domain_class") == cls_name else "range"
            other = r.get("range_class") if direction == "domain" else r.get("domain_class")
            other_label = name_to_cls.get(other, {}).get("label", other)
            arrow = f"{label} —[{r['name']}]→ {other_label}" if direction == "domain" else f"{other_label} —[{r['name']}]→ {label}"
            st.markdown(f"- {arrow}")
            if r.get("description"):
                st.caption(f"  {r['description'][:120]}")

            # Show edge table if in semantic model
            if sem_model:
                if r["name"] == "subClassOf" and subclass_table_info:
                    st.markdown(f"  Edge table: `{subclass_table_info['fqn']}`")
                elif r["name"] != "subClassOf":
                    for tbl in sem_model.get("tables", []):
                        tname_upper = tbl["name"].upper()
                        rel_upper = r["name"].upper().replace(" ", "_")
                        if rel_upper in tname_upper and "VW_ONT_" in tname_upper:
                            bt = tbl.get("base_table", {})
                            fqn = f"{bt.get('database','')}.{bt.get('schema','')}.{bt.get('table','')}"
                            st.markdown(f"  Edge table: `{fqn}`")
                            break


def render_default_detail(classes: list[dict], relations: list[dict],
                          coverage_map: dict[str, dict], sem_model: dict | None) -> None:
    """Render the default detail panel when no node is selected."""
    st.markdown("#### Click a node to inspect")
    st.caption("Click any node in the graph to see its Snowflake implementation details.")

    st.divider()

    # Quick stats
    status_counts = defaultdict(int)
    for cov in coverage_map.values():
        status_counts[cov["status"]] += 1

    cols = st.columns(4)
    cols[0].metric("Mapped", status_counts.get("mapped", 0))
    cols[1].metric("Covered", status_counts.get("covered", 0))
    cols[2].metric("Unmapped", status_counts.get("unmapped", 0))
    cols[3].metric("Abstract", status_counts.get("abstract", 0))

    # Relations summary
    if relations:
        st.divider()
        st.markdown("#### Relations")
        for r in relations:
            props = []
            if r.get("is_hierarchical"):
                props.append("hierarchical")
            if r.get("is_transitive"):
                props.append("transitive")
            prop_str = f" ({', '.join(props)})" if props else ""
            domain = r.get("domain_class", "?")
            rng = r.get("range_class", "?")
            st.markdown(f"- **{r['name']}**: {domain} → {rng}{prop_str}")

    # Semantic model summary
    if sem_model:
        st.divider()
        st.markdown("#### Semantic Model")
        st.markdown(f"**{sem_model.get('name', 'Unknown')}**")
        for tbl in sem_model.get("tables", []):
            short = tbl["name"]
            if "VW_ONT_" in short.upper():
                short = "VW_ONT_" + short.upper().split("VW_ONT_", 1)[1]
            ndims = len(tbl.get("dimensions", []))
            nfacts = len(tbl.get("facts", []))
            st.markdown(f"- `{short}` — {ndims} dims, {nfacts} facts")

        vqs = sem_model.get("verified_queries", [])
        if vqs:
            st.divider()
            st.markdown(f"#### Verified Queries ({len(vqs)})")
            for vq in vqs:
                with st.expander(f"Q: {vq.get('question', vq.get('name', ''))}"):
                    st.code(vq.get("sql", ""), language="sql")


def main():
    # Parse args before Streamlit takes over
    # Use sys.argv to find our custom args (after --)
    custom_args = []
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        custom_args = sys.argv[idx + 1:]
    else:
        # Try parsing directly
        custom_args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--classes-json", required=True)
    parser.add_argument("--relations-json", required=True)
    parser.add_argument("--semantic-model", default=None)
    parser.add_argument("--stats-json", default=None)
    parser.add_argument("--port", default="8501")
    args, _ = parser.parse_known_args(custom_args)

    # Load data
    classes = load_json(args.classes_json)
    relations = load_json(args.relations_json)
    stats = load_json(args.stats_json) if args.stats_json and Path(args.stats_json).exists() else None
    sem_model = load_yaml(args.semantic_model) if args.semantic_model and Path(args.semantic_model).exists() else None

    # --- Streamlit App ---
    st.set_page_config(page_title="Ontology Viewer", layout="wide")
    st.title("Ontology Semantic Modeler - Visualization")

    # Sidebar: Summary stats
    st.sidebar.header("Ontology Summary")
    if stats:
        st.sidebar.metric("Total Classes", stats["total_classes"])
        st.sidebar.metric("Abstract", stats["abstract_classes"])
        st.sidebar.metric("Concrete", stats["concrete_classes"])
        st.sidebar.metric("Relations", stats["total_relations"])
        st.sidebar.metric("Max Depth", stats["max_hierarchy_depth"])
        if stats.get("total_individuals"):
            st.sidebar.metric("Individuals", stats["total_individuals"])
    else:
        st.sidebar.metric("Classes", len(classes))
        st.sidebar.metric("Relations", len(relations))

    # Tab layout (3 tabs: Hierarchy, Graph, Coverage)
    tab_tree, tab_graph, tab_coverage = st.tabs([
        "Class Hierarchy", "Ontology Graph", "Coverage"
    ])

    # Build coverage map once (shared across tabs)
    coverage_map = build_coverage_map(classes, sem_model)

    # --- Tab 1: Class Hierarchy ---
    with tab_tree:
        st.header("Class Hierarchy")
        children_map, roots, name_to_cls = build_tree(classes)

        col_ctrl1, col_ctrl2 = st.columns([1, 1])
        with col_ctrl1:
            max_depth = st.slider("Max display depth", 1, 15, 6)
        with col_ctrl2:
            view_mode = st.radio("View", ["Interactive", "Text"], horizontal=True)

        # Search
        search = st.text_input("Search classes", "", placeholder="Type to filter...")

        # Legend
        st.markdown(
            "🔹 = abstract (no data rows) &nbsp;&nbsp; 🟢 = concrete (has data) &nbsp;&nbsp; 🔍 = search match",
            unsafe_allow_html=True
        )
        st.divider()

        if search:
            matches = [c for c in classes if search.lower() in c.get("label", "").lower() or search.lower() in c["name"].lower()]
            st.write(f"**{len(matches)} matches** for \"{search}\":")
            for m in matches[:50]:
                # Build full ancestry path
                path_parts = []
                current = m.get("parent_name")
                while current:
                    path_parts.insert(0, name_to_cls.get(current, {}).get("label", current))
                    current = name_to_cls.get(current, {}).get("parent_name")
                path_str = " → ".join(path_parts) if path_parts else "root"

                icon = "🔹" if m.get("is_abstract") else "🟢"
                st.markdown(f"{icon} **{m.get('label', m['name'])}**")
                st.caption(f"Path: {path_str}")
                if m.get("description"):
                    st.caption(m["description"][:200])
        elif view_mode == "Interactive":
            for root in sorted(roots):
                render_interactive_tree(root, children_map, name_to_cls,
                                        max_depth=max_depth, search=search)
        else:
            tree_text = ""
            for root in sorted(roots):
                tree_text += render_tree_text(root, children_map, name_to_cls, max_depth=max_depth)
            if tree_text:
                st.code(tree_text, language=None)
            else:
                st.info("No root classes found. The ontology may use a flat structure.")

    # --- Tab 2: Ontology Graph (merged Graph + Relations + Semantic Model) ---
    with tab_graph:
        st.header("Ontology Graph")

        # Controls row
        col_g1, col_g2, col_g3 = st.columns([1, 1, 1])
        with col_g1:
            max_nodes = st.slider("Max nodes", 10, 500, min(len(classes), 50), key="graph_max")
        with col_g2:
            show_rels = st.checkbox("Show relation edges", value=True, key="graph_rels")
        with col_g3:
            physics_on = st.checkbox("Physics simulation", value=True, key="graph_physics")

        # Legend bar
        st.markdown(
            '<div style="display:flex;gap:16px;flex-wrap:wrap;margin:4px 0 8px 0;font-size:0.85em;">'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:14px;height:14px;background:#2ecc71;border:2px solid #27ae60;border-radius:3px;display:inline-block;"></span>'
            ' Mapped to View</span>'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:14px;height:14px;background:#3498db;border:2px solid #2980b9;border-radius:3px;display:inline-block;"></span>'
            ' Covered as Rows</span>'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:14px;height:14px;background:#e74c3c;border:2px solid #c0392b;border-radius:3px;display:inline-block;"></span>'
            ' Unmapped</span>'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:14px;height:14px;background:#ecf0f1;border:2px solid #95a5a6;'
            'transform:rotate(45deg);display:inline-block;"></span>'
            ' Abstract</span>'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:20px;border-top:2px solid #5dade2;display:inline-block;"></span>'
            ' subClassOf</span>'
            '<span style="display:inline-flex;align-items:center;gap:4px;">'
            '<span style="width:20px;border-top:2px dashed #9b59b6;display:inline-block;"></span>'
            ' relation</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Two-panel layout: graph (left) + detail (right)
        col_graph, col_detail = st.columns([3, 2])

        with col_graph:
            # Build nodes and edges
            ag_nodes, ag_edges = build_agraph_nodes_edges(
                classes, relations, coverage_map,
                max_nodes=max_nodes, show_relations=show_rels,
            )

            config = Config(
                width=700,
                height=600,
                physics=physics_on,
                layout={"hierarchical": False},
            )

            # agraph returns the clicked node ID
            selected_node = agraph(nodes=ag_nodes, edges=ag_edges, config=config)

        with col_detail:
            if selected_node:
                render_node_detail(selected_node, classes, relations, coverage_map, sem_model)
            else:
                render_default_detail(classes, relations, coverage_map, sem_model)

    # --- Tab 3: Coverage Matrix ---
    with tab_coverage:
        st.header("Ontology-to-Table Coverage")
        if sem_model:
            cov_map = coverage_map  # reuse

            directly_mapped = [c for c in classes if cov_map[c["name"]]["status"] == "mapped"]
            covered_by_parent = [
                (c, cov_map[c["name"]]["covering_ancestor"])
                for c in classes if cov_map[c["name"]]["status"] == "covered"
            ]
            truly_unmapped = [c for c in classes if cov_map[c["name"]]["status"] == "unmapped"]

            # Summary metrics
            total_concrete = sum(1 for c in classes if not c.get("is_abstract"))
            total_abstract = sum(1 for c in classes if c.get("is_abstract"))
            concrete_mapped = [c for c in directly_mapped if not c.get("is_abstract")]
            concrete_covered_count = len(concrete_mapped) + len(covered_by_parent)

            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Total Classes", len(classes))
            mcol2.metric("Abstract (no view needed)", total_abstract)
            mcol3.metric("Concrete Covered", concrete_covered_count)
            mcol4.metric("Truly Unmapped", len(truly_unmapped))

            if total_concrete > 0:
                ratio = min(concrete_covered_count / total_concrete, 1.0)
                st.progress(ratio,
                            text=f"{concrete_covered_count}/{total_concrete} concrete classes covered "
                                 f"({100 * ratio:.0f}%)")

            # Three-column detail view
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader(f"Mapped to View ({len(directly_mapped)})")
                st.caption("Has a dedicated view in the semantic model")
                for c in sorted(directly_mapped, key=lambda x: x.get("label", x["name"])):
                    view_name = cov_map[c["name"]].get("view_name", "")
                    short = view_name
                    if "VW_ONT_" in view_name.upper():
                        short = "VW_ONT_" + view_name.upper().split("VW_ONT_", 1)[1]
                    st.write(f"- **{c.get('label', c['name'])}** → `{short}`")
            with col2:
                st.subheader(f"Covered as Rows ({len(covered_by_parent)})")
                st.caption("No own view, but included as rows in a parent view")
                by_ancestor: dict[str, list] = defaultdict(list)
                for cls, ancestor in covered_by_parent:
                    by_ancestor[ancestor].append(cls)
                for ancestor in sorted(by_ancestor.keys()):
                    children = by_ancestor[ancestor]
                    with st.expander(f"via **{ancestor}** ({len(children)} classes)"):
                        for c in sorted(children, key=lambda x: x.get("label", x["name"])):
                            st.write(f"- {c.get('label', c['name'])}")
            with col3:
                st.subheader(f"Unmapped ({len(truly_unmapped)})")
                st.caption("No view and no ancestor view covers this class")
                for c in sorted(truly_unmapped, key=lambda x: x.get("label", x["name"])):
                    st.write(f"- {c.get('label', c['name'])}")
                if not truly_unmapped:
                    st.success("All concrete classes are covered!")
        else:
            # Show class-level coverage without model
            abstract_count = sum(1 for c in classes if c.get("is_abstract"))
            concrete_count = len(classes) - abstract_count
            st.metric("Abstract Classes (no table needed)", abstract_count)
            st.metric("Concrete Classes (need table mapping)", concrete_count)


if __name__ == "__main__":
    main()
