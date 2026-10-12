import test from "node:test";
import assert from "node:assert/strict";
import { graphScene } from "./graphScene.mjs";

test("case playback retains saved memories and only overlays its own nodes and edges", () => {
  const memories = {
    nodes: Array.from({ length: 35 }, (_, i) => ({ id: `saved-${i}` })),
    edges: [{ source: "saved-0", target: "saved-1", weight: 0.7 }],
    revision: 4,
  };
  const caseGraph = {
    nodes: ["M89", "M20", "M40", "M70", "M15"].map((id) => ({ id })),
    edges: [{ source: "M89", target: "M15", weight: 0.52 }],
  };
  const original = structuredClone({ memories, caseGraph });
  const scene = graphScene(memories, caseGraph);
  assert.equal(scene.nodes.length, 40);
  assert.deepEqual(scene.edges, [...caseGraph.edges, ...memories.edges]);
  assert.deepEqual({ memories, caseGraph }, original);
  assert.equal(scene.revision, 4);
});

test("installed case nodes retain saved provenance without duplicate circles or edges", () => {
  const saved = {
    nodes: [{ id: "M15", origin: { session_id: "chat" } }],
    edges: [{ source: "M89", target: "M15", weight: 0.6 }],
  };
  const scene = graphScene(saved, {
    nodes: [{ id: "M15" }],
    edges: [{ source: "M15", target: "M89", weight: 0.52 }],
  });
  assert.deepEqual(scene.nodes, saved.nodes);
  assert.deepEqual(scene.edges, saved.edges);
});

test("ordinary recall keeps the original memory graph", () => {
  const memories = { nodes: [{ id: "saved-0" }], edges: [] };
  assert.equal(graphScene(memories), memories);
});
