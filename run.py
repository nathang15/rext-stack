import datetime
import json
import os
import pickle
import typing
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from crawler import hackernews, pipeline, tags
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

def initialize_knowledge_base():
    """Initialize the knowledge base before starting the server"""
    data = {}

    try:
        if os.path.exists("database/database.json"):
            with open("database/database.json", "r") as f:
                data = json.load(f)
            logger.info(f"Loaded existing database with {len(data)} entries")
    except Exception as e:
        logger.error(f"Error loading existing database: {e}")
        data = {}

    try:
        logger.info("Fetching Hackernews knowledge")
        knowledge_crawler = hackernews.HackerNews(
            username=os.getenv('HACKERNEWS_USERNAME'),
            password=os.getenv('HACKERNEWS_PASSWORD'),
        )
        
        knowledge = knowledge_crawler()
        
        for url, document in knowledge.items():
            if url not in data:
                data[url] = document
            else:
                existing_extra_tags = data[url].get('extra-tags', [])
                data[url].update(document)
                if 'tags' in document:
                    combined_tags = list(set(
                        document.get('tags', []) + 
                        data[url].get('tags', []) + 
                        existing_extra_tags
                    ))
                    data[url]['tags'] = combined_tags
        
        logger.info(f"Found {len(knowledge)} new Hackernews documents")
    
    except Exception as e:
        logger.error(f"Error fetching Hackernews knowledge: {e}")

    # Data Normalization
    for url, document in list(data.items()):
        required_fields = ["title", "tags", "summary", "date"]
        for field in required_fields:
            if field not in document or document[field] is None:
                document[field] = ""
        
        if not isinstance(document.get('tags'), list):
            document['tags'] = []
        
        document['tags'] = list(set(document['tags']))
        
        if len(document.get('summary', '')) > 500:
            document['summary'] = document['summary'][:500] + '...'

    # Add Extra Tags
    logger.info("Adding extra tags")
    try:
        data = tags.get_extra_tags(data=data)
    except Exception as e:
        logger.error(f"Error adding extra tags: {e}")

    # Save Database
    try:
        os.makedirs("database", exist_ok=True)
        with open("database/database.json", "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Saved database with {len(data)} entries")
    except Exception as e:
        logger.error(f"Error saving database: {e}")

    # Export Tags Triples
    try:
        excluded_tags = {
            "hackernews": True,
        }

        logger.info("Exporting tree of tags.")
        triples = tags.get_tags_triples(data=data, excluded_tags=excluded_tags)
        with open("database/triples.json", "w") as f:
            json.dump(triples, f, indent=4)
        logger.info("Exported tags triples")
    except Exception as e:
        logger.error(f"Error exporting tags triples: {e}")

    # Serialize Pipeline
    try:
        knowledge_pipeline = pipeline.Pipeline(
            documents=data,
            triples=triples,
        )
        with open("database/pipeline.pkl", "wb") as f:
            pickle.dump(knowledge_pipeline, f)
        logger.info("Serialized knowledge pipeline")
    except Exception as e:
        logger.error(f"Error serializing pipeline: {e}")

    logger.info("Knowledge acquisition and processing complete")
    return True

# Initialize knowledge base before creating the FastAPI app
initialize_knowledge_base()

# Create FastAPI app
app = FastAPI(
    description="Personal knowledge graph.",
    title="FactGPT",
    version="0.0.1",
)

# CORS setup
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Knowledge:
    """This class is a wrapper around the pipeline."""

    def __init__(self) -> None:
        self.pipeline = None
        self.is_ready = False

    def start(self):
        """Load the pipeline."""
        with open("database/pipeline.pkl", "rb") as f:
            self.pipeline = pickle.load(f)
        self.is_ready = True
        return self

    def search(
        self,
        q: str,
        tags: str,
    ) -> typing.Dict:
        """Returns the documents."""
        return self.pipeline.search(q=q, tags=tags)

    def plot(
        self,
        q: str,
        k_tags: int,
        k_yens: int = 1,
        k_walk: int = 3,
    ) -> typing.Dict:
        """Returns the graph."""
        nodes, links = self.pipeline.plot(
            q=q,
            k_tags=k_tags,
            k_yens=k_yens,
            k_walk=k_walk,
        )
        return {"nodes": nodes, "links": links}

knowledge = Knowledge()

@app.get("/status")
async def get_status():
    """Check if the backend is ready."""
    return {"status": "ready" if knowledge.is_ready else "loading"}

@app.get("/search/{sort}/{tags}/{k_tags}/{q}")
def search(k_tags: int, tags: str, sort: bool, q: str):
    """Search for documents."""
    if not knowledge.is_ready:
        return {"error": "System is still initializing"}
    
    tags = tags != "null"
    documents = knowledge.search(q=q, tags=tags)
    if bool(sort):
        documents = [
            document
            for _, document in sorted(
                [(document["date"], document) for document in documents],
                key=lambda document: datetime.datetime.strptime(
                    document[0], "%Y-%m-%d"
                ),
                reverse=True,
            )
        ]
    return {"documents": documents}

@app.get("/plot/{k_tags}/{q}", response_class=ORJSONResponse)
def plot(k_tags: int, q: str):
    """Plot tags."""
    if not knowledge.is_ready:
        return {"error": "System is still initializing"}
    
    return knowledge.plot(q=q, k_tags=k_tags)

@app.on_event("startup")
def start():
    """Initialize the pipeline."""
    return knowledge.start()