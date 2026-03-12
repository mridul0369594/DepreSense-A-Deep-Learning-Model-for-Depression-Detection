import { useEffect, useRef } from "react";

const BrainVisualization = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Neural network visualization
    const nodes: { x: number; y: number; vx: number; vy: number; radius: number }[] = [];
    const connections: { from: number; to: number; alpha: number }[] = [];
    
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    
    // Create nodes
    for (let i = 0; i < 60; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: Math.random() * 3 + 2,
      });
    }

    // Create connections
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (Math.random() > 0.95) {
          connections.push({ from: i, to: j, alpha: Math.random() * 0.5 + 0.1 });
        }
      }
    }

    let animationId: number;
    let pulsePhase = 0;

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      pulsePhase += 0.02;

      // Update and draw connections
      connections.forEach((conn) => {
        const fromNode = nodes[conn.from];
        const toNode = nodes[conn.to];
        const distance = Math.hypot(fromNode.x - toNode.x, fromNode.y - toNode.y);
        
        if (distance < 200) {
          const alpha = (1 - distance / 200) * conn.alpha * (0.5 + 0.5 * Math.sin(pulsePhase + conn.from));
          ctx.beginPath();
          ctx.moveTo(fromNode.x, fromNode.y);
          ctx.lineTo(toNode.x, toNode.y);
          ctx.strokeStyle = `rgba(214, 51, 132, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });

      // Update and draw nodes
      nodes.forEach((node, i) => {
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off edges
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Draw node
        const pulse = 0.5 + 0.5 * Math.sin(pulsePhase + i * 0.2);
        const gradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, node.radius * 2
        );
        gradient.addColorStop(0, `rgba(214, 51, 132, ${0.8 * pulse})`);
        gradient.addColorStop(1, "rgba(214, 51, 132, 0)");

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(214, 51, 132, ${0.6 + 0.4 * pulse})`;
        ctx.fill();

        // Glow effect
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 3, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <div className="relative h-full w-full overflow-hidden bg-sidebar">
      <canvas
        ref={canvasRef}
        className="h-full w-full"
        style={{ width: "100%", height: "100%" }}
      />
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <h1 className="mb-4 text-5xl font-bold text-primary">DepreSense</h1>
        <p className="max-w-md text-lg text-sidebar-foreground/80">
          Deep Learning EEG Analysis System for Depression Detection
        </p>
      </div>
    </div>
  );
};

export default BrainVisualization;
