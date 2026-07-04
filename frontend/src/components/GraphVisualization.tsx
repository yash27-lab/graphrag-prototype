import { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods, NodeObject } from 'react-force-graph-2d';

export interface GraphData {
  nodes: Array<{ id: string; label: string; group?: string }>;
  links: Array<{ source: string; target: string; label?: string }>;
}

interface GraphVisualizationProps {
  data: GraphData | null;
  theme?: 'light' | 'dark';
  repulsion?: number;
}

// Runtime-only properties the force-graph library attaches to nodes,
// plus the pill dimensions we cache between the two canvas passes.
type PillNode = NodeObject & {
  label?: string;
  color?: string;
  __bckgDimensions?: number[];
};

interface ChargeForce {
  strength: (value: number) => void;
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({ data, theme = 'light', repulsion = 400 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (data && fgRef.current) {
      const charge = fgRef.current.d3Force('charge') as unknown as ChargeForce | undefined;
      charge?.strength(-repulsion);
      // Zoom to fit on new data
      setTimeout(() => {
        fgRef.current?.zoomToFit(400, 50);
      }, 500);
    }
  }, [data, repulsion]);

  if (!data || data.nodes.length === 0) {
    return (
      <div className="empty-state" ref={containerRef}>
        <p>No graph data to display. Ingest text and ask a question.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ flexGrow: 1, width: '100%', position: 'relative', overflow: 'hidden' }}>
      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={data}
        nodeLabel="label"
        nodeAutoColorBy="group"
        nodeRelSize={6}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.25}
        linkLabel="label"
        linkColor={() => theme === 'dark' ? '#444444' : '#cccccc'}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={1.5}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleColor={() => theme === 'dark' ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.7)'}
        nodeCanvasObject={(rawNode, ctx, globalScale) => {
          const node = rawNode as PillNode;
          const label = node.label || '';
          const fontSize = 12/globalScale;
          ctx.font = `500 ${fontSize}px Inter, sans-serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth + (fontSize * 1.2), fontSize + (fontSize * 0.8)]; // some padding

          // Node pill background
          ctx.fillStyle = theme === 'dark' ? '#222222' : '#ffffff';
          ctx.beginPath();
          if (ctx.roundRect) {
            ctx.roundRect(
              node.x! - bckgDimensions[0] / 2, 
              node.y! - bckgDimensions[1] / 2, 
              bckgDimensions[0], 
              bckgDimensions[1], 
              4 / globalScale
            );
          } else {
            ctx.rect(
              node.x! - bckgDimensions[0] / 2, 
              node.y! - bckgDimensions[1] / 2, 
              bckgDimensions[0], 
              bckgDimensions[1]
            );
          }
          ctx.fill();

          // Node pill border
          ctx.strokeStyle = node.color || (theme === 'dark' ? '#ededed' : '#111111');
          ctx.lineWidth = 1.5 / globalScale;
          ctx.stroke();

          // Text
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = theme === 'dark' ? '#ededed' : '#111111';
          ctx.fillText(label, node.x!, node.y!);
          
          node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
        }}
        nodePointerAreaPaint={(rawNode, color, ctx) => {
          const node = rawNode as PillNode;
          const bckgDimensions = node.__bckgDimensions;
          if (bckgDimensions) {
            ctx.fillStyle = color;
            ctx.fillRect(node.x! - bckgDimensions[0] / 2, node.y! - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
          }
        }}
      />
    </div>
  );
};
