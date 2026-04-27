// Synthwave background — vanilla-JS port of src/components/SynthwaveBackground.tsx
// Renders an animated synthwave scene with a procedurally-drawn R34 silhouette.
// Used as a fixed-position background behind the docs site content.

// ============================================================================
// drawR34Car  — ported from React component (TypeScript types stripped)
// ============================================================================

function drawR34Car(ctx, width, height) {
  const scale = Math.min(width / 440, height / 240);
  const bodyColor = "#2968E8";
  const outline = "#151520";
  const bumperColor = "#1a1a2a";
  const lineWidth = 2.8;

  const roundedRect = (x, y, rectWidth, rectHeight, radius) => {
    ctx.beginPath();
    ctx.roundRect(x, y, rectWidth, rectHeight, radius);
  };

  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(width / 2, height * 0.58);
  ctx.scale(scale, scale);

  ctx.lineWidth = lineWidth;
  ctx.strokeStyle = outline;

  ctx.fillStyle = "#2e2e42";
  ctx.beginPath();
  ctx.moveTo(-182, -130);
  ctx.lineTo(182, -130);
  ctx.lineTo(186, -120);
  ctx.lineTo(-186, -120);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#26263a";
  for (const side of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(side * 180, -134);
    ctx.lineTo(side * 190, -134);
    ctx.lineTo(side * 190, -116);
    ctx.lineTo(side * 178, -116);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  ctx.fillStyle = "#333346";
  ctx.lineWidth = 2;
  for (const supportX of [-108, 108]) {
    ctx.beginPath();
    ctx.moveTo(supportX - 5, -120);
    ctx.lineTo(supportX + 5, -120);
    ctx.lineTo(supportX + 4, -90);
    ctx.lineTo(supportX - 4, -90);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  ctx.lineWidth = lineWidth;
  ctx.strokeStyle = outline;
  ctx.fillStyle = bodyColor;
  ctx.beginPath();
  ctx.moveTo(-186, 68);
  ctx.lineTo(-192, 30);
  ctx.lineTo(-192, -8);
  ctx.lineTo(-186, -42);
  ctx.lineTo(-172, -62);
  ctx.lineTo(-152, -76);
  ctx.lineTo(-128, -86);
  ctx.lineTo(-118, -96);
  ctx.lineTo(118, -96);
  ctx.lineTo(128, -86);
  ctx.lineTo(152, -76);
  ctx.lineTo(172, -62);
  ctx.lineTo(186, -42);
  ctx.lineTo(192, -8);
  ctx.lineTo(192, 30);
  ctx.lineTo(186, 68);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  const bodyFade = ctx.createLinearGradient(0, -50, 0, 70);
  bodyFade.addColorStop(0, "rgba(0,0,0,0)");
  bodyFade.addColorStop(0.6, "rgba(0,0,0,0)");
  bodyFade.addColorStop(1, "rgba(0,0,30,0.2)");
  ctx.fillStyle = bodyFade;
  ctx.fill();

  const leftHighlight = ctx.createLinearGradient(-195, 0, -160, 0);
  leftHighlight.addColorStop(0, "rgba(255,255,255,0.09)");
  leftHighlight.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = leftHighlight;
  ctx.beginPath();
  ctx.moveTo(-192, -8);
  ctx.lineTo(-186, -42);
  ctx.lineTo(-172, -62);
  ctx.lineTo(-160, -62);
  ctx.lineTo(-174, -42);
  ctx.lineTo(-180, -8);
  ctx.lineTo(-180, 30);
  ctx.lineTo(-192, 30);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#080816";
  ctx.strokeStyle = outline;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(-112, -84);
  ctx.lineTo(-100, -94);
  ctx.lineTo(100, -94);
  ctx.lineTo(112, -84);
  ctx.lineTo(104, -63);
  ctx.lineTo(-104, -63);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  const windowGradient = ctx.createLinearGradient(-60, -92, 60, -68);
  windowGradient.addColorStop(0, "rgba(70,110,170,0.12)");
  windowGradient.addColorStop(0.5, "rgba(100,150,200,0.06)");
  windowGradient.addColorStop(1, "rgba(60,100,160,0.1)");
  ctx.fillStyle = windowGradient;
  ctx.fill();

  ctx.strokeStyle = outline;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(-168, -56);
  ctx.lineTo(168, -56);
  ctx.stroke();

  ctx.fillStyle = "#8888a0";
  ctx.strokeStyle = outline;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.arc(0, -21, 9, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-9, -21);
  ctx.lineTo(9, -21);
  ctx.stroke();

  const taillight = (centerX, centerY, radius, color) => {
    const glow = ctx.createRadialGradient(centerX, centerY, radius * 0.3, centerX, centerY, radius * 3);
    glow.addColorStop(0, color === "red" ? "rgba(255,50,30,0.25)" : "rgba(255,160,40,0.18)");
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(centerX - radius * 3.5, centerY - radius * 3.5, radius * 7, radius * 7);

    ctx.fillStyle = "#0c0c1a";
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius + 3, 0, Math.PI * 2);
    ctx.fill();

    const lightGradient = ctx.createRadialGradient(
      centerX - radius * 0.2,
      centerY - radius * 0.25,
      radius * 0.05,
      centerX,
      centerY,
      radius,
    );

    if (color === "red") {
      lightGradient.addColorStop(0, "#ffaaaa");
      lightGradient.addColorStop(0.25, "#ff4040");
      lightGradient.addColorStop(0.6, "#dd1111");
      lightGradient.addColorStop(1, "#880000");
    } else {
      lightGradient.addColorStop(0, "#ffee99");
      lightGradient.addColorStop(0.25, "#ffaa33");
      lightGradient.addColorStop(0.6, "#dd8811");
      lightGradient.addColorStop(1, "#885500");
    }

    ctx.fillStyle = lightGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = outline;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "rgba(255,255,255,0.18)";
    ctx.beginPath();
    ctx.ellipse(centerX - radius * 0.22, centerY - radius * 0.28, radius * 0.4, radius * 0.25, -0.3, 0, Math.PI * 2);
    ctx.fill();
  };

  const tailY = -21;
  const redTailRadius = 17.5;
  const orangeTailRadius = 13.5;
  taillight(-150, tailY, redTailRadius, "red");
  taillight(-106, tailY, orangeTailRadius, "orange");
  taillight(106, tailY, orangeTailRadius, "orange");
  taillight(150, tailY, redTailRadius, "red");

  ctx.fillStyle = "#bbbbd0";
  ctx.font = 'bold 13px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = "center";
  ctx.fillText("S K Y L I N E", 0, 4);

  ctx.fillStyle = "#ee2222";
  ctx.font = 'bold 11px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = "right";
  ctx.fillText("GT-R", 152, -32);

  ctx.fillStyle = "#bbbbd0";
  ctx.font = '9px "Segoe UI", Arial, sans-serif';
  ctx.fillText("V-spec", 158, 2);

  ctx.fillStyle = bumperColor;
  ctx.strokeStyle = outline;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  ctx.moveTo(-186, 68);
  ctx.lineTo(-178, 20);
  ctx.lineTo(-165, 12);
  ctx.lineTo(165, 12);
  ctx.lineTo(178, 20);
  ctx.lineTo(186, 68);
  ctx.lineTo(182, 100);
  ctx.lineTo(-182, 100);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  ctx.strokeStyle = "#333";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-170, 62);
  ctx.lineTo(170, 62);
  ctx.stroke();

  ctx.fillStyle = "#cc1111";
  ctx.strokeStyle = outline;
  ctx.lineWidth = 1.5;
  roundedRect(55, 52, 55, 8, 2);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#cccccc";
  ctx.strokeStyle = outline;
  ctx.lineWidth = 1.5;
  roundedRect(-38, 44, 76, 20, 3);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#eee";
  ctx.fillRect(-33, 48, 66, 12);

  const exhaustX = -58;
  const exhaustY = 88;
  const exhaustRadius = 17;
  ctx.fillStyle = "#9999a8";
  ctx.strokeStyle = outline;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(exhaustX, exhaustY, exhaustRadius, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  const exhaustGradient = ctx.createRadialGradient(exhaustX, exhaustY, 1, exhaustX, exhaustY, exhaustRadius - 3);
  exhaustGradient.addColorStop(0, "#0a0a0a");
  exhaustGradient.addColorStop(0.7, "#1a1a1a");
  exhaustGradient.addColorStop(1, "#444");
  ctx.fillStyle = exhaustGradient;
  ctx.beginPath();
  ctx.arc(exhaustX, exhaustY, exhaustRadius - 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#555";
  ctx.lineWidth = 0.8;
  ctx.stroke();

  ctx.fillStyle = "rgba(255,255,255,0.12)";
  ctx.beginPath();
  ctx.ellipse(exhaustX - 3, exhaustY - 5, exhaustRadius * 0.28, exhaustRadius * 0.16, -0.4, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(10,10,30,0.5)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-178, -52);
  ctx.quadraticCurveTo(-188, 0, -190, 55);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(178, -52);
  ctx.quadraticCurveTo(188, 0, 190, 55);
  ctx.stroke();

  const bodyBottomFade = ctx.createLinearGradient(0, 30, 0, 105);
  bodyBottomFade.addColorStop(0, "rgba(0,0,0,0)");
  bodyBottomFade.addColorStop(1, "rgba(0, 0, 18, 0.26)");
  ctx.fillStyle = bodyBottomFade;
  ctx.beginPath();
  ctx.moveTo(-182, 0);
  ctx.lineTo(182, 0);
  ctx.lineTo(190, 108);
  ctx.lineTo(-190, 108);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.beginPath();
  ctx.moveTo(-182, 100);
  ctx.lineTo(182, 100);
  ctx.lineTo(190, 108);
  ctx.lineTo(-190, 108);
  ctx.closePath();
  ctx.fill();

  ctx.restore();
}


// ============================================================================
// Scene initialisation
// ============================================================================

(function initSynthwave() {
  const SCENE_WIDTH = 300;
  const SCENE_HEIGHT = 250;

  function updateScale() {
    const sceneEl = document.getElementById("synthwave");
    if (!sceneEl) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    const scale = Math.max(w / SCENE_WIDTH, h / SCENE_HEIGHT) * 1.01;
    sceneEl.style.setProperty("--synthwave-scale", scale.toFixed(4));
  }

  function initCarCanvas() {
    const canvas = document.querySelector("canvas.synthwave-r34");
    if (!canvas || !canvas.getContext) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let frameId = 0;

    function render() {
      const bounds = canvas.getBoundingClientRect();
      const width = Math.max(1, Math.round(bounds.width));
      const height = Math.max(1, Math.round(bounds.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawR34Car(context, width, height);
    }

    function scheduleRender() {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(render);
    }

    scheduleRender();

    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(scheduleRender);
      ro.observe(canvas);
    } else {
      window.addEventListener("resize", scheduleRender);
    }
  }

  function init() {
    updateScale();
    initCarCanvas();
    window.addEventListener("resize", updateScale);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
