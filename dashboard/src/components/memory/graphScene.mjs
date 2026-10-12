export function graphScene(memoryGraph, caseGraph) {
  if (!caseGraph) return memoryGraph;
  const nodes = new Map(caseGraph.nodes.map((node) => [node.id, node]));
  for (const node of memoryGraph.nodes) nodes.set(node.id, node);
  const edgeKey = (edge) => [edge.source, edge.target].sort().join(":");
  const edges = new Map(caseGraph.edges.map((edge) => [edgeKey(edge), edge]));
  for (const edge of memoryGraph.edges) edges.set(edgeKey(edge), edge);
  return {
    ...memoryGraph,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
  };
}
