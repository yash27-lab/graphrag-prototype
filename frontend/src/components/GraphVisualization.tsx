import React, { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface GraphData {
  nodes: Array<{ id: string; label: string; group?: string }>;
  links: Array<{ source: string; target: string; label?: string }>;
}

interface GraphVisualizationProps {
  data: GraphData | null;
  theme?: 'light' | 'dark';
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({ data, theme = 'light' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
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
      // Zoom to fit on new data
      setTimeout(() => {
        fgRef.current.zoomToFit(400, 50);
      }, 500);
    }
  }, [data]);

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
        nodeCanvasObject={(node, ctx, globalScale) => {
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
          ctx.strokeStyle = (node as any).color || (theme === 'dark' ? '#ededed' : '#111111');
          ctx.lineWidth = 1.5 / globalScale;
          ctx.stroke();

          // Text
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = theme === 'dark' ? '#ededed' : '#111111';
          ctx.fillText(label, node.x!, node.y!);
          
          (node as any).__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          const bckgDimensions = (node as any).__bckgDimensions;
          if (bckgDimensions) {
            ctx.fillStyle = color;
            ctx.fillRect(node.x! - bckgDimensions[0] / 2, node.y! - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
          }
        }}
      />
    </div>
  );
};
