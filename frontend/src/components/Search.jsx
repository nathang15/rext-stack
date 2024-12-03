import React, { useState, useEffect, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';

const Search = () => {
  const [query, setQuery] = useState('');
  const [node, setNode] = useState(null);
  const [k, setK] = useState(40);
  const [documents, setDocuments] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [hoveredNode, setHoveredNode] = useState(null);

  // URL parameter handling
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlQuery = params.get("query") || "";
    const urlNode = params.get("node") || null;

    if (urlQuery.length > 0) {
      setQuery(urlQuery);
      handlePlot(urlQuery, k, false);
      
      if (urlNode) {
        setNode(urlNode);
        handleSearch(urlQuery + " " + urlNode, k);
      }
    }
  }, []);

  const handlePlot = useCallback((queryText, k, timer = true) => {
    handleSearch(queryText, k);
    
    if (timer) {
      const plotTimer = setTimeout(() => {
        plotGraph(queryText, k);
      }, 600);
      
      return () => clearTimeout(plotTimer);
    } else {
      plotGraph(queryText, k);
    }
  }, []);

  const handleSearch = useCallback((searchQuery, k, sort = false) => {
    fetch(`http://localhost:5000/search/${sort}/${node}/${k}/${searchQuery.replace("/", "")}`)
      .then(res => res.json())
      .then(data => {
        setDocuments(Object.values(data.documents));
      })
      .catch(error => console.error('Search error:', error));
  }, [node]);

  const plotGraph = useCallback((queryText, k) => {
    fetch(`http://localhost:5000/plot/${k}/${queryText.replace("/", "")}`)
      .then(res => res.json())
      .then(data => {
        const processedGraphData = {
          nodes: (data.nodes || []).map((node, index) => ({
            ...node,
            id: node.id || node.name || `node_${index}`,
            color: node.color || `hsl(${index * 360 / data.nodes.length}, 70%, 50%)`,
            group: node.group || index
          })),
          links: (data.links || data.edges || []).map((link, index) => ({
            ...link,
            source: link.source || link.from,
            target: link.target || link.to,
            relation: link.relation || link.label || `relation_${index}`
          }))
        };

        setGraphData(processedGraphData);
      })
      .catch(error => console.error('Graph plot error:', error));
  }, []);

  const handleChangeText = (event) => {
    const newQuery = event.target.value.toLowerCase();
    setQuery(newQuery);
    setNode(null);

    window.history.pushState({}, null, `?query=${encodeURIComponent(newQuery)}`);

    if (newQuery.trim().length > 0) {
      handlePlot(newQuery, k);
    }
  };

  const handleHoverNode = (node) => {
    setHoveredNode(node);
  };

  const handleClickNode = (node) => {
    if (node) {
      setNode(node.id);
      handleSearch(query + " " + node.id, k);
      window.history.pushState({}, null, `?query=${encodeURIComponent(query)}&node=${encodeURIComponent(node.id)}`);
    }
  };


  const highlight = (text) => {
    if (query.length <= 1) return text;

    const keywords = [...new Set([...query.split(/\s/), ...(node ? [node] : [])])].filter(token => token.length > 2);
    const parts = text.split(new RegExp(`(${keywords.join("|")})`, 'gi'));

    return parts.map((part, index) => 
      keywords.some(keyword => part.toLowerCase() === keyword.toLowerCase()) 
        ? <span key={index} className="highlight">{part}</span> 
        : part
    );
  };

  const handleClickTag = (tag) => {
    const newQuery = `${query} ${tag}`;
    setQuery(newQuery);
    handlePlot(newQuery, k);
  };

  return (
    <div className="search-container">
      <div className="search-wrapper">
        <input
          id="search"
          type="text"
          placeholder="Explore Neural Connections"
          value={query}
          onChange={handleChangeText}
          autoFocus
        />
      </div>
      
      <div className="content-container">
        <div className="documents">
          {documents.length === 0 ? (
            <div className="no-results">
              <p>Start exploring neural connections</p>
              <p>Enter a query to discover related documents</p>
            </div>
          ) : (
            documents.map((doc, index) => (
              <div 
                key={index} 
                className={`document ${hoveredNode && doc.tags.includes(hoveredNode.id) ? 'highlighted' : ''}`}
              >
                <a href={doc.url} target="_blank" rel="noopener noreferrer">{highlight(doc.title)}</a>
                <div className="date">{highlight(doc.date)}</div>
                <div className="summary">{highlight(doc.summary)}</div>
                <div className="tags">
                  {[...doc.tags, ...(doc['extra-tags'] || [])].map((tag, tagIndex) => (
                    <span 
                      key={tagIndex} 
                      className="tag" 
                      onClick={() => handleClickTag(tag)}
                    >
                      {highlight(tag)}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
        
          <div className="graph">
            <ForceGraph3D
              graphData={graphData}
              backgroundColor="rgba(19, 19, 23, 0)"
              width={window.innerWidth / 2}
              height={window.innerHeight}
              showNavInfo={false}
              nodeAutoColorBy="group"
              linkOpacity={0.8}
              linkWidth={0.3}
              linkResolution={12}
              linkDirectionalParticleColor={() => "#E6F4FF"}
              linkDirectionalParticles={3}
              linkDirectionalParticleWidth={0.4}
              linkDirectionalParticleResolution={10}
              linkDirectionalParticleSpeed={0.01}
              linkColor={(link) => hoveredNode 
                ? (link.source.id === hoveredNode.id || link.target.id === hoveredNode.id) 
                  ? "#60AA91FF" 
                  : "rgba(255, 255, 255, 0.4)"
                : "rgba(255, 255, 255, 0.6)"
              }
              nodeRelSize={6}
              nodeResolution={16}
              nodeOpacity={0.9}
              linkThreeObjectExtend={true}
              linkThreeObject={(link) => {
                const sprite = new SpriteText(link.relation);
                sprite.color = '#FFFFFF';
                sprite.textHeight = 1.5;
                sprite.fontSize = 0;
                sprite.fontFace = "Inter";
                return sprite;
              }}
              nodeThreeObject={(node) => {
                const sprite = new SpriteText(node.id);
                sprite.color = node.color;
                sprite.textHeight = 3.5;
                sprite.fontSize = hoveredNode === node ? 75 : 55;
                sprite.fontFace = "Inter";
                return sprite;
              }}
              onNodeHover={handleHoverNode}
              onNodeClick={handleClickNode}
              cooldownTime={2000}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              enableNodeDrag={true}
              enableNavigationControls={true}
            />
          </div>
      </div>
    </div>
  );
};

export default Search;