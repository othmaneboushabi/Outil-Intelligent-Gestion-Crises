import networkx as nx
from pyvis.network import Network
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models import Problem, Report, Department, ProblemDependency


# ─── CONSTRUCTION DU GRAPHE ──────────────────────────────

def build_dependency_graph(
    db: Session,
    week_number: int,
    year: int
) -> nx.DiGraph:
    """
    Construit un graphe orienté depuis les dépendances
    de la semaine donnée.
    - Nœud  : département
    - Arc   : dépendance déclarée dans ProblemDependency
    - Poids : criticality_score du problème associé
    """
    graph = nx.DiGraph()

    # Ajouter tous les départements comme nœuds
    departments = db.query(Department).all()
    for dept in departments:
        graph.add_node(dept.id, name=dept.name)

    # Ajouter les arcs depuis les dépendances
    problems = (
        db.query(Problem)
        .join(Report)
        .filter(
            Report.week_number == week_number,
            Report.year        == year
        )
        .all()
    )

    for problem in problems:
        report = db.query(Report).filter(Report.id == problem.report_id).first()
        if not report:
            continue

        from models import User
        user = db.query(User).filter(User.id == report.submitted_by).first()
        if not user or not user.department_id:
            continue

        source_dept_id = user.department_id
        score          = problem.criticality_score or 0.0

        for dep in problem.dependencies:
            target_dept_id = dep.dependent_department_id
            if source_dept_id != target_dept_id:
                if graph.has_edge(source_dept_id, target_dept_id):
                    # Additionner les scores si l'arc existe déjà
                    graph[source_dept_id][target_dept_id]["weight"] += score
                    graph[source_dept_id][target_dept_id]["problems"].append(problem.id)
                else:
                    graph.add_edge(
                        source_dept_id,
                        target_dept_id,
                        weight   = score,
                        problems = [problem.id]
                    )

    return graph


# ─── ANALYSE DU GRAPHE ───────────────────────────────────

def find_bottleneck(graph: nx.DiGraph, db: Session) -> Optional[Dict]:
    """
    Identifie le département goulot d'étranglement
    via la betweenness centrality.
    """
    if len(graph.nodes) == 0:
        return None

    centrality = nx.betweenness_centrality(graph, weight="weight")

    if not centrality:
        return None

    bottleneck_id    = max(centrality, key=centrality.get)
    bottleneck_score = centrality[bottleneck_id]

    dept = db.query(Department).filter(Department.id == bottleneck_id).first()

    return {
        "department_id"   : bottleneck_id,
        "department_name" : dept.name if dept else "Inconnu",
        "centrality_score": round(bottleneck_score, 4),
        "all_centralities": {
            db.query(Department).filter(Department.id == k).first().name: round(v, 4)
            for k, v in centrality.items()
            if db.query(Department).filter(Department.id == k).first()
        }
    }


def get_node_colors(graph: nx.DiGraph) -> Dict[int, str]:
    """
    Colorie les nœuds selon leur rôle :
    - Rouge   : département bloquant (out_degree > 0)
    - Orange  : département impacté (in_degree > 0)
    - Vert    : département neutre
    """
    colors = {}
    for node in graph.nodes:
        out_deg = graph.out_degree(node)
        in_deg  = graph.in_degree(node)
        if out_deg > 0 and in_deg == 0:
            colors[node] = "#f44336"  # Rouge — bloquant
        elif in_deg > 0 and out_deg == 0:
            colors[node] = "#ff9800"  # Orange — impacté
        elif out_deg > 0 and in_deg > 0:
            colors[node] = "#ff5722"  # Rouge-orange — bloquant ET impacté
        else:
            colors[node] = "#4caf50"  # Vert — neutre
    return colors


# ─── SIMULATION DE DÉBLOCAGE ─────────────────────────────

def simulate_unblock(
    graph: nx.DiGraph,
    dept_id: int,
    db: Session
) -> Dict:
    """
    Simule le déblocage d'un département.
    Retourne les problèmes qui disparaîtraient en cascade.
    """
    if dept_id not in graph.nodes:
        return {"message": "Département non trouvé dans le graphe", "freed_problems": []}

    dept = db.query(Department).filter(Department.id == dept_id).first()
    dept_name = dept.name if dept else "Inconnu"

    # Trouver tous les arcs sortants du département
    outgoing_edges  = list(graph.out_edges(dept_id, data=True))
    freed_problems  = []
    impacted_depts  = []

    for _, target, data in outgoing_edges:
        target_dept = db.query(Department).filter(Department.id == target).first()
        if target_dept:
            impacted_depts.append(target_dept.name)
        freed_problems.extend(data.get("problems", []))

    # Supprimer le nœud et recalculer
    graph_copy = graph.copy()
    graph_copy.remove_node(dept_id)

    # Compter les arcs libérés en cascade
    cascade_count = len(freed_problems)

    return {
        "unblocked_department" : dept_name,
        "freed_problems_ids"   : freed_problems,
        "freed_count"          : cascade_count,
        "impacted_departments" : impacted_depts,
        "message"              : (
            f"Débloquer {dept_name} libèrerait "
            f"{cascade_count} problème(s) en cascade "
            f"dans : {', '.join(impacted_depts) or 'aucun département'}"
        )
    }


# ─── EXPORT HTML PYVIS ───────────────────────────────────

def export_graph_html(
    graph: nx.DiGraph,
    db: Session,
    output_path: str = "domino_graph.html"
) -> str:
    """
    Génère un graphe interactif PyVis en HTML.
    """
    net = Network(
        height     = "600px",
        width      = "100%",
        directed   = True,
        bgcolor    = "#1e2430",
        font_color = "#ffffff"
    )

    colors = get_node_colors(graph)

    # Ajouter les nœuds
    for node in graph.nodes:
        dept = db.query(Department).filter(Department.id == node).first()
        name = dept.name if dept else f"Dept {node}"
        color = colors.get(node, "#4caf50")
        net.add_node(
            node,
            label = name,
            color = color,
            size  = 30,
            title = f"Département : {name}\nCouleur : {'Bloquant' if color == '#f44336' else 'Impacté' if color == '#ff9800' else 'Neutre'}"
        )

    # Ajouter les arcs
    for source, target, data in graph.edges(data=True):
        weight = round(data.get("weight", 1.0), 2)
        net.add_edge(
            source,
            target,
            value = weight,
            title = f"Score : {weight}",
            color = "#ff5252"
        )

    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "stabilization": {"iterations": 100}
        },
        "edges": {
            "arrows": {"to": {"enabled": true}},
            "smooth": {"type": "curvedCW"}
        }
    }
    """)

    net.save_graph(output_path)
    return output_path


# ─── RÉSUMÉ COMPLET DU GRAPHE ────────────────────────────

def get_domino_summary(
    db: Session,
    week_number: int,
    year: int
) -> Dict:
    """
    Retourne un résumé complet du graphe domino
    pour la semaine donnée.
    """
    graph      = build_dependency_graph(db, week_number, year)
    bottleneck = find_bottleneck(graph, db)
    colors     = get_node_colors(graph)

    nodes = []
    for node in graph.nodes:
        dept  = db.query(Department).filter(Department.id == node).first()
        color = colors.get(node, "#4caf50")
        nodes.append({
            "id"    : node,
            "name"  : dept.name if dept else "Inconnu",
            "color" : color,
            "role"  : (
                "bloquant" if color == "#f44336"
                else "impacté" if color == "#ff9800"
                else "bloquant_impacté" if color == "#ff5722"
                else "neutre"
            )
        })

    edges = []
    for source, target, data in graph.edges(data=True):
        source_dept = db.query(Department).filter(Department.id == source).first()
        target_dept = db.query(Department).filter(Department.id == target).first()
        edges.append({
            "source"      : source_dept.name if source_dept else source,
            "target"      : target_dept.name if target_dept else target,
            "weight"      : round(data.get("weight", 0), 2),
            "problem_ids" : data.get("problems", [])
        })

    return {
        "week_number" : week_number,
        "year"        : year,
        "nodes"       : nodes,
        "edges"       : edges,
        "bottleneck"  : bottleneck,
        "total_nodes" : len(nodes),
        "total_edges" : len(edges)
    }