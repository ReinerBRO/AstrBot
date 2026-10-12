import test from "node:test";
import assert from "node:assert/strict";
import { edgeCurve, graphLayout, memoryTitle } from "./graphLayout.mjs";

test("layout is deterministic and keeps graph nodes inside desktop and narrow canvases", () => {
  const nodes = Array.from({ length: 24 }, (_, i) => ({
    id: `n${i}`,
    kind: i % 4 ? "episodic" : "semantic",
    origin: { topic: `topic${i % 3}` },
    content: `记忆 ${i}`,
  }));
  const edges = nodes
    .slice(1)
    .map((node, i) => ({ source: nodes[i].id, target: node.id, weight: 0.5 }));
  for (const width of [360, 680, 1200]) {
    const layout = graphLayout(nodes, edges, width, 520);
    assert.deepEqual(layout, graphLayout(nodes, edges, width, 520));
    assert.equal(layout.nodes.length, nodes.length);
    for (const node of layout.nodes) {
      assert.ok(Number.isFinite(node.x) && Number.isFinite(node.y));
      assert.ok(node.x > 0 && node.x < width && node.y > 0 && node.y < 520);
    }
    assert.match(edgeCurve(layout.nodes[0], layout.nodes[1]), /^M .+ Q .+/);
  }
});

test("empty and single-node graphs work without invented neighbors", () => {
  assert.deepEqual(graphLayout([], [], 500, 520), { nodes: [], centers: [] });
  const layout = graphLayout(
    [{ id: "one", kind: "episodic", content: "一条记忆" }],
    [{ source: "one", target: "missing" }],
    500,
    520,
  );
  assert.equal(layout.nodes.length, 1);
  assert.equal(
    memoryTitle({ content: "User: 喜欢茉莉花茶。\nAssistant: 记住了。" }),
    "喜欢茉莉花茶",
  );
  assert.equal(memoryTitle({ origin: { title: "自定义标题" } }), "自定义标题");
});
