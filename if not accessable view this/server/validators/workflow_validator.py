def validate_workflow(nodes, edges):
    errors = []
    node_ids = {n["id"] for n in nodes if "id" in n}
    if len(node_ids) != len(nodes):
        errors.append("Duplicate node IDs detected.")

    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if src not in node_ids:
            errors.append(f"Edge source '{src}' does not exist")
        if tgt not in node_ids:
            errors.append(f"Edge target '{tgt}' does not exist")

    # Cycle detection (optional warning)
    adjacency = {nid: [] for nid in node_ids}
    for e in edges:
        if e["source"] in node_ids and e["target"] in node_ids:
            adjacency[e["source"]].append(e["target"])

    visited = set()
    stack = set()
    def has_cycle(node):
        visited.add(node)
        stack.add(node)
        for nei in adjacency.get(node, []):
            if nei not in visited:
                if has_cycle(nei):
                    return True
            elif nei in stack:
                return True
        stack.remove(node)
        return False

    cycle = False
    for n in node_ids:
        if n not in visited:
            if has_cycle(n):
                cycle = True
                break
    if cycle:
        errors.append("Workflow contains cycles (loops) – this is allowed for repeating workflows.")

    broken_edges = [e for e in errors if "does not exist" in e]
    return {"is_valid": len(broken_edges) == 0, "errors": errors}