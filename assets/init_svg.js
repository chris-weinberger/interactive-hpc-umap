// // assets/init_svg.js
// (function () {
//     // --- wait until inline SVG is present ---
//     function waitForSvg(cb) {
//       const obs = new MutationObserver(() => {
//         const host = document.getElementById("svg-root");
//         if (!host) return;
//         const svg = host.querySelector("svg");
//         if (svg) {
//           obs.disconnect();
//           cb(host, svg);
//         }
//       });
//       obs.observe(document.documentElement, { childList: true, subtree: true });
//     }
  
//     waitForSvg(function (host, svg) {
//       // -------- limit interaction to your region layer --------
//       const SCOPE =
//         svg.querySelector("g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_") ||
//         svg.querySelector("#REGION_TILES_418_divisions_A-Z_");
//       const inScope = (n) => (SCOPE ? SCOPE.contains(n) : true);
  
//       // -------- styling: selection highlight & hit-testing --------
//       try {
//         const style = document.createElement("style");
//         style.textContent = `
//           /* default: nothing interactive */
//           svg * { pointer-events: none; }
  
//           /* enable interactivity only in the region scope */
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ * { pointer-events: auto; }
  
//           /* geometry should catch clicks even with fill:none */
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ path,
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ polygon,
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ circle,
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ ellipse {
//             pointer-events: visiblePainted;
//             cursor: pointer;
//           }
  
//           /* labels not clickable */
//           svg g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ text { pointer-events: none !important; }
  
//           /* === selection highlight === */
//           .selected-region {
//             /* tweak these to taste */
//             stroke: #ff006e !important;
//             stroke-width: 0.6px !important;  /* original strokes are tiny; bump slightly */
//             fill: #ff006e !important;
//             fill-opacity: 0.18 !important;    /* translucent fill so you can still see underlying map */
//           }
//         `;
//         svg.appendChild(style);
//       } catch (e) {}
  
//       // -------- ensure viewBox for pan/zoom --------
//       function ensureViewBox(s) {
//         if (s.hasAttribute("viewBox")) return;
//         try {
//           const bb = s.getBBox();
//           if (bb && bb.width && bb.height) {
//             s.setAttribute("viewBox", `${bb.x} ${bb.y} ${bb.width} ${bb.height}`);
//             return;
//           }
//         } catch (e) {}
//         const w = parseFloat(s.getAttribute("width")) || s.clientWidth || 1000;
//         const h = parseFloat(s.getAttribute("height")) || s.clientHeight || 1000;
//         s.setAttribute("viewBox", `0 0 ${w} ${h}`);
//       }
//       ensureViewBox(svg);
  
//       function getVB() {
//         const [x, y, w, h] = (svg.getAttribute("viewBox") || "0 0 1000 1000").split(/\s+/).map(Number);
//         return { x, y, w, h };
//       }
//       function setVB(b) { svg.setAttribute("viewBox", `${b.x} ${b.y} ${b.w} ${b.h}`); }
  
//       function clientToSvgPoint(clientX, clientY) {
//         const rect = svg.getBoundingClientRect();
//         const tX = (clientX - rect.left) / rect.width;
//         const tY = (clientY - rect.top) / rect.height;
//         const vb = getVB();
//         return { x: vb.x + tX * vb.w, y: vb.y + tY * vb.h };
//       }
  
//       // -------- region picking (returns {label, node}) --------
//       const SKIP_TAGS = new Set(["svg", "rect", "text", "line", "polyline"]);
//       const PREFER_TAGS = new Set(["path", "polygon", "circle", "ellipse"]);
//       const BAD_LABEL = /(border|frame|rectangle|figure)/i;
  
//       const isEl = (n) => n && n.nodeType === 1;
//       const labelOf = (n) => {
//         if (!isEl(n)) return "";
//         const ds = n.dataset || {};
//         return ds.name || ds.label || n.id || "";
//       };
  
//       function pickRegionHit(e) {
//         const path = typeof e.composedPath === "function" ? e.composedPath() : [e.target];
//         const stack = (path && path.length ? path : [e.target]).filter((n) => isEl(n) && svg.contains(n) && inScope(n));
  
//         // Prefer direct geometry hit
//         for (const n of stack) {
//           const tag = n.tagName.toLowerCase();
//           if (!PREFER_TAGS.has(tag)) continue;
//           const lbl = labelOf(n);
//           if (lbl && !BAD_LABEL.test(lbl.toLowerCase())) return { label: lbl, node: n };
//         }
  
//         // Otherwise climb ancestors to find labeled container
//         for (const start of stack) {
//           let n = start;
//           while (isEl(n) && n !== svg && inScope(n)) {
//             const tag = n.tagName.toLowerCase();
//             if (!SKIP_TAGS.has(tag)) {
//               const lbl = labelOf(n);
//               if (lbl && !BAD_LABEL.test(lbl.toLowerCase())) return { label: lbl, node: n };
//             }
//             n = n.parentElement;
//           }
//         }
//         return null;
//       }
  
//       // -------- selection state --------
//       const selected = new Set(); // Set<SVGElement>
  
//       function clearSelection() {
//         for (const el of Array.from(selected)) {
//           el.classList.remove("selected-region");
//           selected.delete(el);
//         }
//       }
//       function toggleSelection(el) {
//         if (selected.has(el)) {
//           el.classList.remove("selected-region");
//           selected.delete(el);
//         } else {
//           el.classList.add("selected-region");
//           selected.add(el);
//         }
//       }
//       function selectOnly(el) {
//         if (!selected.has(el) || selected.size !== 1) {
//           clearSelection();
//           el.classList.add("selected-region");
//           selected.add(el);
//         }
//       }
  
//       // -------- click handler: select + notify Dash --------
//       function handleClick(e) {
//         const hit = pickRegionHit(e);
//         if (!hit) {
//           // Clicked empty area → clear selection (only if no modifiers)
//           if (!e.shiftKey && !e.ctrlKey && !e.metaKey) clearSelection();
//           return;
//         }
//         // Multi-select modifiers toggle; otherwise single-select
//         if (e.shiftKey || e.ctrlKey || e.metaKey) {
//           toggleSelection(hit.node);
//         } else {
//           selectOnly(hit.node);
//         }
  
//         // Notify Dash with a simple, serializable payload
//         const ev = new CustomEvent("regionclick_simple", {
//           detail: { region_str: String(hit.label) },
//           bubbles: true,
//           cancelable: true,
//         });
//         (document.getElementById("listener") || host).dispatchEvent(ev);
//       }
  
//       host.addEventListener("click", handleClick);
//       svg.addEventListener("click", handleClick);
  
//       // -------- keyboard: Escape clears selection --------
//       window.addEventListener("keydown", (e) => {
//         if (e.key === "Escape") clearSelection();
//       });
  
//       // -------- Zoom (wheel) & Pan (drag) --------
//       function onWheel(e) {
//         e.preventDefault();
//         const vb = getVB();
//         const mouse = clientToSvgPoint(e.clientX, e.clientY);
//         const k = 1.0015;
//         const factor = Math.pow(k, e.deltaY); // >1 out, <1 in
//         const newW = vb.w * factor, newH = vb.h * factor;
//         const sx = (mouse.x - vb.x) / vb.w, sy = (mouse.y - vb.y) / vb.h;
//         const newX = mouse.x - newW * sx, newY = mouse.y - newH * sy;
//         setVB({ x: newX, y: newY, w: newW, h: newH });
//       }
//       host.addEventListener("wheel", onWheel, { passive: false });
//       svg.addEventListener("wheel", onWheel, { passive: false });
  
//       let isPanning = false, last = { x: 0, y: 0 };
//       svg.addEventListener("mousedown", (e) => {
//         if (e.button !== 0) return;
//         isPanning = true;
//         last = { x: e.clientX, y: e.clientY };
//         e.preventDefault();
//       });
//       window.addEventListener("mousemove", (e) => {
//         if (!isPanning) return;
//         const vb = getVB();
//         const rect = svg.getBoundingClientRect();
//         const dxSvg = ((e.clientX - last.x) / rect.width) * vb.w;
//         const dySvg = ((e.clientY - last.y) / rect.height) * vb.h;
//         setVB({ x: vb.x - dxSvg, y: vb.y - dySvg, w: vb.w, h: vb.h });
//         last = { x: e.clientX, y: e.clientY };
//       });
//       window.addEventListener("mouseup", () => { isPanning = false; });
//     });
//   })();
  
// assets/init_svg.js
(function () {
  // STATE: This Set persists across Dash re-renders.
  const selectedLabels = new Set();

  // This function is called every time an SVG appears in the DOM.
  function initializeSvg(host, svg) {
      if (svg.dataset.initialized) {
          syncStyles(svg);
          return;
      }

      const SCOPE =
          svg.querySelector("g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_") ||
          svg.querySelector("#REGION_TILES_418_divisions_A-Z_") ||
          svg;
      const inScope = (n) => (SCOPE ? SCOPE.contains(n) : true);

      // --- Helper functions ---
      const isEl = (n) => n && n.nodeType === 1;
      const labelOf = (n) => {
          if (!isEl(n)) return "";
          const ds = n.dataset || {};
          return ds.name || ds.label || n.id || "";
      };
      const SKIP_TAGS = new Set(["svg", "rect", "text", "line", "polyline"]);
      const BAD_LABEL = /(border|frame|rectangle|figure)/i;

      function getLabelForNodeInHierarchy(startNode) {
          let n = startNode;
          while (isEl(n) && n !== svg && inScope(n)) {
              const tag = n.tagName.toLowerCase();
              if (!SKIP_TAGS.has(tag)) {
                  const lbl = labelOf(n);
                  if (lbl && !BAD_LABEL.test(lbl.toLowerCase())) return lbl;
              }
              n = n.parentElement;
          }
          return "";
      }

      // --- Core Logic ---
      function syncStyles() {
          const allRegions = SCOPE.querySelectorAll("path, polygon, circle, ellipse");
          allRegions.forEach(regionNode => {
              const regionLabel = getLabelForNodeInHierarchy(regionNode);
              if (regionLabel && selectedLabels.has(regionLabel)) {
                  regionNode.classList.add("selected-region");
              } else {
                  regionNode.classList.remove("selected-region");
              }
          });
      }

      function toggleSelection(node) {
          const label = getLabelForNodeInHierarchy(node);
          if (!label) return;
          if (selectedLabels.has(label)) {
              selectedLabels.delete(label);
          } else {
              selectedLabels.add(label);
          }
      }

      function currentSelectedLabels() {
          return Array.from(selectedLabels);
      }
      
      // NEW: Modified clearSelection to notify Dash
      function clearSelection() {
          selectedLabels.clear();
          syncStyles();
          // Dispatch an event to Dash to update chips and UMAP plots
          const detail = {
              region_str: "", // No region was clicked
              selected_labels: [] // The new list is empty
          };
          const ev = new CustomEvent("regionclick_simple", { detail, bubbles: true, cancelable: true });
          (document.getElementById("listener") || host).dispatchEvent(ev);
      }

      function handleClick(e) {
          const hitNode = e.target.closest("path, polygon, circle, ellipse");
          if (!hitNode || !inScope(hitNode)) return;

          toggleSelection(hitNode);
          syncStyles();

          const detail = {
              region_str: getLabelForNodeInHierarchy(hitNode),
              selected_labels: currentSelectedLabels()
          };
          const ev = new CustomEvent("regionclick_simple", { detail, bubbles: true, cancelable: true });
          (document.getElementById("listener") || host).dispatchEvent(ev);
          e.stopPropagation();
      }
      
      // --- Initialization and Event Listeners ---
      try {
          const style = document.createElement("style");
          style.textContent = `
            .selected-region {
              stroke: #ff006e !important; stroke-width: 0.6px !important;
              fill: #ff006e !important; fill-opacity: 0.18 !important;
            }
            svg * { cursor: default; }
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ * { pointer-events: auto; }
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ path,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ polygon,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ circle,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A-Z_ ellipse {
              cursor: pointer;
            }
          `;
          svg.appendChild(style);
      } catch (e) { }

      host.addEventListener("click", handleClick);
      window.addEventListener("keydown", (e) => { if (e.key === "Escape") clearSelection(); });
      
      // NEW: Create and inject the clear button
      const btnContainer = document.getElementById('clear-btn-container');
      if (btnContainer && !btnContainer.hasChildNodes()) {
          const clearBtn = document.createElement('button');
          clearBtn.textContent = 'Clear Selection';
          clearBtn.style.fontSize = '12px';
          clearBtn.addEventListener('click', clearSelection);
          btnContainer.appendChild(clearBtn);
      }

      svg.dataset.initialized = "true";
      syncStyles();
  }

  // This observer finds the SVG on load and after every Dash re-render.
  const obs = new MutationObserver(() => {
      const host = document.getElementById("svg-root");
      if (!host) return;
      const svg = host.querySelector("svg");
      if (svg) {
          initializeSvg(host, svg);
      }
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });

})();