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
          svg.querySelector("g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_") ||
          svg.querySelector("#REGION_TILES_418_divisions_A_Z_") ||
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

      // --- START of Click vs. Drag state ---
      let isDragging = false;
      let lastPoint = { x: 0, y: 0 };
      // --- END of Click vs. Drag state ---


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

      // --- Zoom/Pan Helpers ---
      function ensureViewBox(s) {
          if (s.hasAttribute("viewBox")) return;
          try {
              const bb = s.getBBox();
              if (bb && bb.width && bb.height) {
                  s.setAttribute("viewBox", `${bb.x} ${bb.y} ${bb.width} ${bb.height}`);
                  return;
              }
          } catch (e) { }
          const w = parseFloat(s.getAttribute("width")) || s.clientWidth || 1000;
          const h = parseFloat(s.getAttribute("height")) || s.clientHeight || 1000;
          s.setAttribute("viewBox", `0 0 ${w} ${h}`);
      }

      function getVB() {
          const [x, y, w, h] = (svg.getAttribute("viewBox") || "0 0 1000 1000").split(/\s+/).map(Number);
          return { x, y, w, h };
      }

      function setVB(b) {
          svg.setAttribute("viewBox", `${b.x} ${b.y} ${b.w} ${b.h}`);
      }

      function clientToSvgPoint(clientX, clientY) {
          const rect = svg.getBoundingClientRect();
          const tX = (clientX - rect.left) / rect.width;
          const tY = (clientY - rect.top) / rect.height;
          const vb = getVB();
          return { x: vb.x + tX * vb.w, y: vb.y + tY * vb.h };
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

      function clearSelection() {
          selectedLabels.clear();
          syncStyles();
          const detail = {
              region_str: "",
              selected_labels: []
          };
          const ev = new CustomEvent("regionclick_simple", { detail, bubbles: true, cancelable: true });
          (document.getElementById("listener") || host).dispatchEvent(ev);
      }

      function handleClick(e) {
          // NEW: If we were just dragging, don't process this as a selection click.
          if (isDragging) {
              isDragging = false;
              return;
          }

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
      ensureViewBox(svg);
      
      function onWheel(e) {
          e.preventDefault();
          const vb = getVB();
          const mouse = clientToSvgPoint(e.clientX, e.clientY);
          const k = 1.0015;
          const factor = Math.pow(k, e.deltaY);
          const newW = vb.w * factor, newH = vb.h * factor;
          const sx = (mouse.x - vb.x) / vb.w, sy = (mouse.y - vb.y) / vb.h;
          const newX = mouse.x - newW * sx, newY = mouse.y - newH * sy;
          setVB({ x: newX, y: newY, w: newW, h: newH });
      }


      try {
          const style = document.createElement("style");
          style.textContent = `
            .selected-region {
              stroke: #ff006e !important; stroke-width: 0.6px !important;
              fill: #ff006e !important; fill-opacity: 0.18 !important;
            }
            svg * { cursor: default; }
            svg { cursor: grab; }
            svg:active { cursor: grabbing; }
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_ * { pointer-events: auto; }
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_ path,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_ polygon,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_ circle,
            g#CNS_Division_TILES_rat_ g#REGION_TILES_418_divisions_A_Z_ ellipse {
              cursor: pointer;
            }
          `;
          svg.appendChild(style);
      } catch (e) { }

      host.addEventListener("click", handleClick);
      window.addEventListener("keydown", (e) => { if (e.key === "Escape") clearSelection(); });

      const btnContainer = document.getElementById('clear-btn-container');
      if (btnContainer && !btnContainer.hasChildNodes()) {
          const clearBtn = document.createElement('button');
          clearBtn.textContent = 'Clear Selection';
          clearBtn.style.fontSize = '12px';
          clearBtn.addEventListener('click', clearSelection);
          btnContainer.appendChild(clearBtn);
      }
      
      host.addEventListener("wheel", onWheel, { passive: false });
      
      // --- NEW Pan/Drag Logic ---
      let isPanning = false;
      svg.addEventListener("mousedown", (e) => {
          if (e.button !== 0) return;
          isPanning = true;
          isDragging = false; // Reset dragging flag
          lastPoint = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener("mousemove", (e) => {
          if (!isPanning) return;

          const dx = e.clientX - lastPoint.x;
          const dy = e.clientY - lastPoint.y;

          // If the mouse has moved more than a few pixels, we consider it a drag
          if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
              isDragging = true;
          }

          if (isDragging) {
              const vb = getVB();
              const rect = svg.getBoundingClientRect();
              const dxSvg = (dx / rect.width) * vb.w;
              const dySvg = (dy / rect.height) * vb.h;
              setVB({ x: vb.x - dxSvg, y: vb.y - dySvg, w: vb.w, h: vb.h });
          }

          lastPoint = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener("mouseup", () => {
          isPanning = false;
      });
      // --- End of new Pan/Drag Logic ---

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