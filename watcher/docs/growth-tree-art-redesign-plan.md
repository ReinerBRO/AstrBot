# Growth Tree Art Redesign Implementation Plan

Updated: 2026-02-07

## 1. Goal
- Replace the current geometric line-tree with a painterly, artistic growth tree.
- Keep existing product value: timeline mapping, category branches, zoom/pan, tooltip, keyboard navigation.
- Add meaningful animation: trunk growth, branch expansion, fruit bloom, ambient sway.

## 2. Current Baseline (from code)
- Tree is rendered on a single `canvas` (`app/web_static/index.html`, `app/web_static/app.js`).
- Render flow is centralized in `drawTree()` and related helpers:
  - layout: `buildFruitLayout()`
  - branch: `drawFruitBranch()`
  - fruit: `drawFruit()`
  - background/time scale: `drawCanvasBackground()`, `drawTimeScale()`
- Interaction already exists and should be preserved:
  - wheel zoom, drag pan, tooltip hover, keyboard focus/arrow navigation.

## 3. Art Direction (frontend-design skill)
- Concept: `Living Watercolor Journal`
  - Tree feels hand-painted, soft-edge, organic, imperfect.
  - Fruits feel like ink + watercolor spots with highlight and tiny leaves.
  - Background has atmosphere layers (sky wash, grain/noise, light bloom).
- Visual tone:
  - Warm natural palette (bark umber, moss green, coral fruit accents).
  - Avoid flat neon geometry and rigid straight-line look.
- Signature memory point:
  - The tree grows on load like a time-lapse painting.

## 4. Technical Strategy
- Keep Canvas 2D (no framework migration) to minimize risk and preserve current interaction model.
- Introduce a renderer pipeline inside `app/web_static/app.js`:
  - `buildTreeScene(data, metrics)` -> normalized scene model
  - `renderTreeFrame(ctx, scene, t)` -> full painterly frame at time `t`
  - `animateTree(scene)` -> intro + idle loop
- Use seeded randomness per date/tree for stable painterly variation:
  - same tree/date => same composition style jitter, not random every redraw.

## 5. Phased Implementation Plan

## Phase 0 - Safety Baseline
- Freeze current behavior with manual checks:
  - tree fetch/switch, zoom, pan, tooltip, keyboard, trim branches, date switch.
- Capture before screenshots for comparison.

Deliverable:
- Short baseline checklist added to PR notes.

## Phase 1 - Render Refactor (No visual change yet)
- Extract current draw path into scene-oriented helpers:
  - `buildFruitLayout()` remains source of positional truth.
  - New `scene` object stores trunk path, branch paths, fruit nodes, visual tokens.
- Separate `layout` from `paint` to support animation progress and layered styles.

Files:
- `app/web_static/app.js`

Exit criteria:
- Output looks same as today but code is split into scene + renderer flow.

## Phase 2 - Painterly Static Visuals
- Replace straight trunk with multi-pass brush strokes:
  - 3-5 layered strokes, variable width, alpha, slight path jitter.
- Replace branch lines with tapered bezier brush:
  - slight curvature, rough-edge overlays, branch shadow wash.
- Upgrade fruit rendering:
  - base pigment, edge darkening ring, soft glow, highlight spot, tiny leaf.
- Add atmospheric background layers:
  - vertical wash gradient, corner light bloom, subtle noise texture.

Files:
- `app/web_static/app.js`
- `app/web_static/style.css` (canvas frame, surrounding panel tone tuning)

Exit criteria:
- Tree reads as painting-like even when animation is disabled.

## Phase 3 - Growth Animation System
- Intro timeline (first 1.8-2.4s after data load):
  - 0-35% trunk grows upward.
  - 30-75% branches extend from trunk.
  - 60-100% fruits pop/bloom in sequence by timeline order.
- Idle loop:
  - subtle branch sway (very low amplitude),
  - fruit micro bob + occasional glint,
  - optional floating pollen particles (bounded count).
- Respect reduced motion:
  - disable non-essential loop if `prefers-reduced-motion` is enabled.

Files:
- `app/web_static/app.js`

Exit criteria:
- Animation is smooth and does not break hover/click hit test.

## Phase 4 - Interaction Compatibility
- Ensure animated positions are used for hit testing:
  - tooltip target radius follows fruit animated location.
- Keep current controls and semantics:
  - `+/-/Today`, mouse wheel zoom, drag pan, arrow navigation.
- Maintain deterministic selected fruit highlight while animation runs.

Files:
- `app/web_static/app.js`
- `app/web_static/index.html` (only if minor aria text updates are needed)

Exit criteria:
- All previous interactions still pass smoke test.

## Phase 5 - Polish, Performance, and QA
- Performance budget:
  - target steady-state draw <= 8ms/frame on normal desktop for typical tree sizes.
  - throttle to redraw only when needed (animation tick, hover change, viewport change).
- Add hard caps:
  - particles count, expensive blur usage, gradient layer count.
- QA matrix:
  - dark/light theme,
  - empty tree/no trees/no fruits in range,
  - high fruit density,
  - mobile width (<720px) and desktop.

Files:
- `app/web_static/app.js`
- `app/web_static/style.css`

Exit criteria:
- No major FPS drop, no interaction regression, no unreadable text in both themes.

## 6. Proposed File-Level Change List
- `app/web_static/app.js`
  - add scene model builder and animation clock.
  - replace primitive line/circle painters with painterly multi-pass renderers.
  - integrate motion-aware hit testing.
- `app/web_static/style.css`
  - tune tree card/canvas shell to match art direction.
  - optional subtle canvas container effects (frame glow/grain overlay).
- `app/web_static/index.html`
  - keep structure; optionally add one wrapper div for decorative overlay if needed.

## 7. Acceptance Criteria
- Visual:
  - tree appears painterly and organic (not just thin lines).
  - fruits look hand-crafted and alive.
- Motion:
  - visible growth sequence on load.
  - gentle ambient life in idle state.
- Product:
  - existing interactions still work as before.
  - no backend API change required.
- Quality:
  - no console errors,
  - no obvious lag in normal usage,
  - mobile and desktop both usable.

## 8. Risk and Mitigation
- Risk: animation loop causes CPU spikes.
  - Mitigation: dirty-flag redraw + capped effects + reduced motion path.
- Risk: painterly randomness hurts readability.
  - Mitigation: seed randomness and keep category-color contrast minimum.
- Risk: hover accuracy drops with motion.
  - Mitigation: compute hit test from animated coordinates each frame.

## 9. Execution Order Recommendation
1. Phase 1 (refactor without changing look)
2. Phase 2 (static art quality)
3. Phase 3 (growth + idle animation)
4. Phase 4 (interaction hardening)
5. Phase 5 (perf and QA gate)
