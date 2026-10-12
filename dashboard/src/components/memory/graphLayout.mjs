export const memoryKinds = {
  episodic: { label: "经历", color: "#7fd6bf" },
  semantic: { label: "知识", color: "#a7c8fa" },
  profile: { label: "画像", color: "#c4a4ec" },
  pattern: { label: "规律", color: "#efc184" },
};

export function memoryTitle(node) {
  if (node.origin?.title) return node.origin.title;
  const text = node.content
    .replace(/^User:\s*/i, "")
    .split(/\nAssistant:|[。\n]/)[0];
  return text.length > 14 ? text.slice(0, 14) + "…" : text;
}

export function graphLayout(nodes, edges, width, height) {
  const topics = [
    ...new Set(
      nodes.map((n) => n.origin?.topic || memoryKinds[n.kind]?.label || "记忆"),
    ),
  ];
  const centers = topics.map((topic, i) => {
    const angle = -Math.PI * 0.8 + (i * 2 * Math.PI) / topics.length;
    return {
      topic,
      x: width * 0.5 + (topics.length > 1 ? Math.cos(angle) * width * 0.26 : 0),
      y:
        height * 0.48 +
        (topics.length > 1 ? Math.sin(angle) * height * 0.24 : 0),
    };
  });
  const placed = nodes.map((node, i) => {
    const group = centers.find(
      (c) =>
        c.topic ===
        (node.origin?.topic || memoryKinds[node.kind]?.label || "记忆"),
    );
    const angle = i * 2.399963;
    return {
      ...node,
      x: group.x + Math.cos(angle) * 55,
      y: group.y + Math.sin(angle) * 55,
      vx: 0,
      vy: 0,
      group,
      radius: node.kind === "episodic" ? 5.5 : 9,
    };
  });
  const map = new Map(placed.map((n) => [n.id, n]));
  const validEdges = edges.filter(
    (e) => map.has(e.source) && map.has(e.target),
  );
  const padding = Math.min(78, width * 0.15);
  for (let tick = 0; tick < 180; tick++) {
    const cooling = 1 - tick / 220;
    for (let i = 0; i < placed.length; i++) {
      const a = placed[i];
      for (let j = i + 1; j < placed.length; j++) {
        const b = placed[j];
        const dx = a.x - b.x || 0.01,
          dy = a.y - b.y || 0.01;
        const dist = Math.max(12, Math.hypot(dx, dy));
        const force = Math.min(8, 2300 / (dist * dist));
        a.vx += (dx / dist) * force;
        a.vy += (dy / dist) * force;
        b.vx -= (dx / dist) * force;
        b.vy -= (dy / dist) * force;
      }
    }
    for (const edge of validEdges) {
      const a = map.get(edge.source),
        b = map.get(edge.target);
      const dx = b.x - a.x,
        dy = b.y - a.y,
        dist = Math.max(1, Math.hypot(dx, dy));
      const desired = a.group === b.group ? 90 : Math.min(width, height) * 0.35;
      const force = (dist - desired) * 0.008;
      a.vx += (dx / dist) * force;
      a.vy += (dy / dist) * force;
      b.vx -= (dx / dist) * force;
      b.vy -= (dy / dist) * force;
    }
    for (const node of placed) {
      node.vx += (node.group.x - node.x) * 0.008;
      node.vy += (node.group.y - node.y) * 0.008;
      node.x = Math.max(
        padding,
        Math.min(width - padding, node.x + node.vx * cooling),
      );
      node.y = Math.max(85, Math.min(height - 105, node.y + node.vy * cooling));
      node.vx *= 0.65;
      node.vy *= 0.65;
    }
  }
  // Separate label boxes after settling the graph, without inventing edges.
  const labelWidths = placed.map((node) =>
    [...memoryTitle(node)].reduce(
      (size, char) => size + (char.charCodeAt(0) > 255 ? 12 : 6.5),
      16,
    ),
  );
  for (let pass = 0; pass < 24; pass++) {
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        const a = placed[i],
          b = placed[j];
        const dx = a.x - b.x,
          dy = a.y + a.radius - b.y - b.radius;
        const overlapX = (labelWidths[i] + labelWidths[j]) / 2 - Math.abs(dx);
        const overlapY = 23 - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        if (overlapX < overlapY) {
          const shift = (overlapX + 1) * 0.5 * (dx >= 0 ? 1 : -1);
          a.x += shift;
          b.x -= shift;
        } else {
          const shift = (overlapY + 1) * 0.5 * (dy >= 0 ? 1 : -1);
          a.y += shift;
          b.y -= shift;
        }
        for (const node of [a, b]) {
          node.x = Math.max(padding, Math.min(width - padding, node.x));
          node.y = Math.max(85, Math.min(height - 105, node.y));
        }
      }
    }
  }
  return { nodes: placed, centers };
}

export function edgeCurve(a, b) {
  const dx = b.x - a.x,
    dy = b.y - a.y;
  return `M ${a.x} ${a.y} Q ${(a.x + b.x) / 2 - dy * 0.1} ${
    (a.y + b.y) / 2 + dx * 0.1
  } ${b.x} ${b.y}`;
}
