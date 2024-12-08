import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';

const PaginationComponent = ({ totalItems, itemsPerPage, currentPage, onPageChange }) => {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);
  
  const getPageRange = () => {
    const range = [];
    const maxVisiblePages = 5;
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, start + maxVisiblePages - 1);
    
    if (end - start + 1 < maxVisiblePages) {
      start = Math.max(1, end - maxVisiblePages + 1);
    }
    
    for (let i = start; i <= end; i++) {
      range.push(i);
    }
    return range;
  };

  if (totalPages <= 1) return null;

  return (
    <div className="pagination-wrapper">
      <div className="results-count">
        Showing {startItem}-{endItem} of {totalItems} results
      </div>
      <div className="pagination">
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="pagination-button"
        >
          First
        </button>
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="pagination-button"
        >
          Previous
        </button>
        {getPageRange().map(page => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`pagination-button ${currentPage === page ? 'active' : ''}`}
          >
            {page}
          </button>
        ))}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="pagination-button"
        >
          Next
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="pagination-button"
        >
          Last
        </button>
      </div>
    </div>
  );
};

// Document Component
const Document = React.memo(({ doc, hoveredNode, onTagClick, highlight }) => (
  <div className={`document ${hoveredNode && doc.tags.includes(hoveredNode.id) ? 'highlighted' : ''}`}>
    <a href={doc.url} target="_blank" rel="noopener noreferrer">
      {highlight(doc.title)}
    </a>
    <div className="date">{highlight(doc.date)}</div>
    <div className="summary">{highlight(doc.summary)}</div>
    <div className="tags">
      {[...doc.tags, ...(doc['extra-tags'] || [])].map((tag, tagIndex) => (
        <span 
          key={tagIndex} 
          className="tag" 
          onClick={() => onTagClick(tag)}
        >
          {highlight(tag)}
        </span>
      ))}
    </div>
  </div>
));

const Graph = React.memo(({ graphData, hoveredNode, onNodeHover, onNodeClick }) => {
  const rendererConfig = useCallback(canvas => {
    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: false,
      powerPreference: "high-performance",
      logarithmicDepthBuffer: false,
    });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio));
    return renderer;
  }, []);

  const controlsRef = useRef();
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.maxDistance = 300;
      controlsRef.current.minDistance = 20;
      controlsRef.current.zoomSpeed = 0.5;
      controlsRef.current.rotateSpeed = 0.5;
    }
  }, []);

  return (
    <ForceGraph3D
      ref={controlsRef}
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
      linkDirectionalParticleSpeed={0.005}
      linkColor={(link) => hoveredNode 
        ? (link.source.id === hoveredNode.id || link.target.id === hoveredNode.id) 
          ? "#60AA91FF" 
          : "rgba(255, 255, 255, 0.4)"
        : "rgba(255, 255, 255, 0.6)"
      }
      nodeRelSize={6}
      nodeResolution={16}
      nodeOpacity={0.9}
      rendererConfig={rendererConfig}
      d3AlphaMin={0.001}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.3}
      warmupTicks={50}
      cooldownTicks={1000}
      cooldownTime={2000}
      onEngineStop={() => {
        if (controlsRef.current) {
          controlsRef.current.enableZoom = true;
        }
      }}
      onZoom={zoom => {
        const detail = zoom < 1.5 ? 8 : zoom < 2.5 ? 12 : 16;
        return {
          nodeResolution: detail,
          linkResolution: Math.max(6, detail - 4)
        };
      }}
      linkThreeObjectExtend={true}
      linkThreeObject={(link) => {
        if (!hoveredNode || (link.source.id === hoveredNode.id || link.target.id === hoveredNode.id)) {
          const sprite = new SpriteText(link.relation);
          sprite.color = '#FFFFFF';
          sprite.textHeight = 1.5;
          sprite.fontSize = 0;
          sprite.fontFace = "Inter";
          return sprite;
        }
        return null;
      }}
      nodeThreeObject={(node) => {
        const sprite = new SpriteText(node.id);
        sprite.color = node.color;
        sprite.textHeight = 3.5;
        sprite.fontSize = hoveredNode === node ? 75 : 55;
        sprite.fontFace = "Inter";
        return sprite;
      }}
      onNodeHover={onNodeHover}
      onNodeClick={onNodeClick}
      enableNodeDrag={true}
      enableNavigationControls={true}
    />
  );
});

// Main Search Component
const Search = () => {
  const [query, setQuery] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [node, setNode] = useState(null);
  const k = 40;
  const [documents, setDocuments] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [spellingSuggestion, setSpellingSuggestion] = useState(null);
  const itemsPerPage = 20;
  const documentsRef = useRef(null);
  const spellCheckTimeoutRef = useRef(null);

  // URL parameter handling
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const page = parseInt(params.get("page")) || 1;
    setCurrentPage(page);
    const urlQuery = params.get("query") || "";
    const urlNode = params.get("node") || null;

    if (urlQuery.length > 0) {
      setInputValue(urlQuery);
      setQuery(urlQuery);
      handlePlot(urlQuery, k, false);
      
      if (urlNode) {
        setNode(urlNode);
        handleSearch(urlQuery + " " + urlNode, k);
      }
    }
  }, []);

  const checkSpelling = useCallback((text) => {
    if (!text.trim()) {
      setSpellingSuggestion(null);
      return;
    }
    if (spellCheckTimeoutRef.current) {
      clearTimeout(spellCheckTimeoutRef.current);
    }
    spellCheckTimeoutRef.current = setTimeout(() => {
      fetch(`http://localhost:5000/spelling/${encodeURIComponent(text)}`)
        .then(res => res.json())
        .then(data => {
          if (data.suggestion && data.suggestion !== text) {
            setSpellingSuggestion(data.suggestion);
          } else {
            setSpellingSuggestion(null);
          }
        })
        .catch(error => {
          console.error('Spelling check error:', error);
          setSpellingSuggestion(null);
        });
    }, 500);
  }, []);

  const processGraphData = useCallback((data) => {
    const maxNodes = 75;
    const nodes = (data.nodes || [])
      .slice(0, maxNodes)
      .map((node, index) => ({
        ...node,
        id: node.id || node.name || `node_${index}`,
        color: node.color || `hsl(${index * 360 / maxNodes}, 70%, 50%)`,
        group: node.group || index,
        size: data.links?.filter(link => 
          link.source === node.id || link.target === node.id
        ).length || 1
      }));

    const nodeIds = new Set(nodes.map(n => n.id));
    const links = (data.links || data.edges || [])
      .filter(link => 
        nodeIds.has(link.source || link.from) && 
        nodeIds.has(link.target || link.to)
      )
      .map((link, index) => ({
        ...link,
        source: link.source || link.from,
        target: link.target || link.to,
        relation: link.relation || link.label || `relation_${index}`
      }));

    return { nodes, links };
  }, []);

  const handlePlot = useCallback((queryText, k, timer = true) => {
    if (!queryText.trim()) return;
    
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

  const handlePageChange = useCallback((page) => {
    setCurrentPage(page);
    if (documentsRef.current) {
      documentsRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
    window.history.pushState(
      {}, 
      null, 
      `?query=${encodeURIComponent(query)}&page=${page}${node ? `&node=${encodeURIComponent(node)}` : ''}`
    );
  }, [query, node]);

  const handleSearch = useCallback((searchQuery, k, sort = false) => {
    setIsLoading(true);
    fetch(`http://localhost:5000/search/${sort}/${node}/${k}/${searchQuery.replace("/", "")}`)
      .then(res => res.json())
      .then(data => {
        setDocuments(Object.values(data.documents));
        setCurrentPage(1);
      })
      .catch(error => console.error('Search error:', error))
      .finally(() => setIsLoading(false));
  }, [node]);

  const plotGraph = useCallback((queryText, k) => {
    fetch(`http://localhost:5000/plot/${k}/${queryText.replace("/", "")}`)
      .then(res => res.json())
      .then(data => {
        const processedData = processGraphData(data);
        setGraphData(processedData);
      })
      .catch(error => console.error('Graph plot error:', error));
  }, [processGraphData]);

  const handleInputChange = (event) => {
    const newValue = event.target.value.toLowerCase();
    setInputValue(newValue);
    checkSpelling(newValue);
  };

  const handleSuggestionClick = () => {
    if (spellingSuggestion) {
      setInputValue(spellingSuggestion);
      setSpellingSuggestion(null);
      executeSearch(spellingSuggestion);
    }
  };

  const executeSearch = useCallback((searchText = inputValue) => {
    if (!searchText.trim()) return;
    
    setQuery(searchText);
    setNode(null);
    setCurrentPage(1);
    setSpellingSuggestion(null);
    window.history.pushState({}, null, `?query=${encodeURIComponent(searchText)}`);
    handlePlot(searchText, k);
  }, [inputValue, k, handlePlot]);

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      executeSearch();
    }
  };

  const highlight = useCallback((text) => {
    if (query.length <= 1) return text;

    const keywords = [...new Set([...query.split(/\s/), ...(node ? [node] : [])])].filter(token => token.length > 2);
    const parts = text.split(new RegExp(`(${keywords.join("|")})`, 'gi'));

    return parts.map((part, index) => 
      keywords.some(keyword => part.toLowerCase() === keyword.toLowerCase()) 
        ? <span key={index} className="highlight">{part}</span> 
        : part
    );
  }, [query, node]);

  const handleClickTag = useCallback((tag) => {
    const newQuery = `${query} ${tag}`;
    setInputValue(newQuery);
    setQuery(newQuery);
    handlePlot(newQuery, k);
  }, [query, k, handlePlot]);

  const handleClickNode = useCallback((node) => {
    if (node) {
      setNode(node.id);
      handleSearch(query + " " + node.id, k);
      window.history.pushState({}, null, `?query=${encodeURIComponent(query)}&node=${encodeURIComponent(node.id)}`);
    }
  }, [query, k, handleSearch]);

  const paginatedDocuments = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return documents.slice(startIndex, startIndex + itemsPerPage);
  }, [documents, currentPage]);

  return (
    <div className="search-container">
      <div className="search-wrapper">
        <div className="search-input-container">
            <input
              id="search"
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyPress}
              autoFocus
            />
            {spellingSuggestion && (
              <div className="spelling-suggestion">
                Did you mean:{' '}
                <button onClick={handleSuggestionClick} className="suggestion-button">
                  {spellingSuggestion}
                </button>
              </div>
            )}
          </div>
         <button 
          className="search-button"
          onClick={executeSearch}
        >
          Search
        </button>
      </div>
      
      <div className="content-container">
        <div className="documents" ref={documentsRef}>
          {isLoading ? (
            <div className="loading">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="no-results">
              <p>Start exploring neural connections</p>
              <p>Enter a query to discover related documents</p>
            </div>
          ) : (
            <>
              {paginatedDocuments.map((doc, index) => (
                <Document
                  key={index}
                  doc={doc}
                  hoveredNode={hoveredNode}
                  onTagClick={handleClickTag}
                  highlight={highlight}
                />
              ))}
              <PaginationComponent
                totalItems={documents.length}
                itemsPerPage={itemsPerPage}
                currentPage={currentPage}
                onPageChange={handlePageChange}
              />
            </>
          )}
        </div>
        
        <div className="graph">
          <Graph
            graphData={graphData}
            hoveredNode={hoveredNode}
            onNodeHover={setHoveredNode}
            onNodeClick={handleClickNode}
          />
        </div>
      </div>
    </div>
  );
};

export default Search;