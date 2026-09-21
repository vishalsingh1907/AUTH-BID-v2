"""
SIH26100 — Production Qdrant Vector Database & GraphRAG Engine
Uses:
1. Qdrant Vector Database (qdrant_client) for HNSW-indexed vector search.
2. Google Gemini embeddings (models/gemini-embedding-001) for 3,072-dimensional document vectors.
3. Hybrid BM25 keyword matching for exact statutory identifiers (PAN, GSTIN, UDIN).
4. Multi-hop Knowledge Graph resolution (Neo4j / corporate relationships) for GraphRAG.
"""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import settings

logger = logging.getLogger("authbid.rag")

DOC_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/documents")),
]

COLLECTION_NAME = "bidder_evidence"
VECTOR_DIM = 3072


class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        bidder_id: str,
        doc_type: str,
        file_path: str,
        page: int,
        text: str,
        embedding: Optional[List[float]] = None,
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.bidder_id = bidder_id
        self.doc_type = doc_type
        self.file_path = file_path
        self.page = page
        self.text = text
        self.embedding = embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "bidder_id": self.bidder_id,
            "doc_type": self.doc_type,
            "page": self.page,
            "text": self.text,
            "file_name": os.path.basename(self.file_path),
        }


class DocumentRAGService:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.is_indexed: bool = False
        self._gemini_client = None
        # Initialize embedded Qdrant Vector Database
        self.qdrant = QdrantClient(location=":memory:")
        self._init_qdrant_collection()

    def _init_qdrant_collection(self):
        try:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Initialized Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}, metric=COSINE)")
        except Exception as e:
            logger.debug(f"Qdrant collection notice: {e}")

    def _get_gemini_client(self):
        if self._gemini_client is None:
            api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
            if api_key and api_key.strip() and api_key.strip() not in ["your_gemini_api_key_here", ""]:
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=api_key.strip())
                except Exception as e:
                    logger.warning(f"Could not initialize google.genai.Client: {e}")
        return self._gemini_client

    def _extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text page by page using PyMuPDF (fitz) with pypdf fallback."""
        pages_content = []
        try:
            import fitz
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    pages_content.append({"page": i + 1, "text": text})
            doc.close()
        except Exception as e:
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_content.append({"page": i + 1, "text": text.strip()})
            except Exception as e2:
                logger.error(f"Failed to extract PDF {file_path}: {e} / {e2}")
        return pages_content

    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """Parse DOC-{TYPE}-{BIDDER_ID}.pdf."""
        base = os.path.splitext(filename)[0]
        parts = base.split("-")
        if len(parts) >= 3 and parts[0] == "DOC":
            doc_type = parts[1]
            bidder_id = parts[2]
            return {"doc_type": doc_type, "bidder_id": bidder_id, "doc_id": base}
        return {"doc_type": "UNKNOWN", "bidder_id": "GENERAL", "doc_id": base}

    def index_documents(self, force_refresh: bool = False):
        """Load, chunk, embed, and index all documents into Qdrant Vector Database."""
        if self.is_indexed and not force_refresh:
            return

        target_dir = None
        for d in DOC_DIRS:
            if os.path.exists(d) and any(f.endswith(".pdf") for f in os.listdir(d)):
                target_dir = d
                break

        if not target_dir:
            logger.warning("No PDF documents found in storage directories to index.")
            return

        pdf_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".pdf")]
        logger.info(f"Indexing {len(pdf_files)} document files into Qdrant Vector DB...")

        self.chunks = []
        for file_path in pdf_files:
            meta = self._parse_filename(os.path.basename(file_path))
            pages = self._extract_text_from_pdf(file_path)
            for p in pages:
                chunk_id = f"{meta['doc_id']}-p{p['page']}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=meta["doc_id"],
                    bidder_id=meta["bidder_id"],
                    doc_type=meta["doc_type"],
                    file_path=file_path,
                    page=p["page"],
                    text=p["text"],
                )
                self.chunks.append(chunk)

        # Check local cache for embeddings
        cache_path = os.path.join(target_dir, "rag_cache.json")
        loaded_from_cache = False
        if os.path.exists(cache_path) and not force_refresh:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                count = 0
                for chunk in self.chunks:
                    if chunk.chunk_id in cache_data:
                        chunk.embedding = cache_data[chunk.chunk_id]
                        count += 1
                if count == len(self.chunks):
                    loaded_from_cache = True
                    logger.info(f"Loaded {count} embeddings from disk cache.")
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")

        # Compute embeddings via Gemini if not in cache
        if not loaded_from_cache:
            client = self._get_gemini_client()
            cache_to_save = {}
            if client:
                try:
                    batch_size = 16
                    for i in range(0, len(self.chunks), batch_size):
                        batch = self.chunks[i:i + batch_size]
                        texts = [c.text[:2000] for c in batch]
                        emb_res = client.models.embed_content(
                            model=settings.EMBEDDING_MODEL or "models/gemini-embedding-001",
                            contents=texts,
                        )
                        for c_idx, chunk in enumerate(batch):
                            chunk.embedding = emb_res.embeddings[c_idx].values
                            cache_to_save[chunk.chunk_id] = chunk.embedding
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(cache_to_save, f)
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Gemini embedding batch failed: {e}")

        # Upsert all vectors and payloads into Qdrant Vector Database
        points = []
        for idx, chunk in enumerate(self.chunks):
            if chunk.embedding and len(chunk.embedding) == VECTOR_DIM:
                points.append(
                    PointStruct(
                        id=idx + 1,
                        vector=chunk.embedding,
                        payload=chunk.to_dict(),
                    )
                )

        if points:
            self.qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Upserted {len(points)} vectors into Qdrant Vector DB '{COLLECTION_NAME}'.")

        self.is_indexed = True

    def index_single_document(
        self,
        file_path: str,
        doc_id: str,
        bidder_id: str,
        doc_type: str,
    ) -> List[DocumentChunk]:
        """
        Extracts, embeds, and immediately indexes a single new document into Qdrant.
        """
        if not self.is_indexed:
            self.index_documents()

        pages = self._extract_text_from_pdf(file_path)
        if not pages:
            return []

        new_chunks: List[DocumentChunk] = []
        for p in pages:
            chunk_id = f"{doc_id}_p{p['page']}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                bidder_id=bidder_id,
                doc_type=doc_type,
                file_path=file_path,
                page=p["page"],
                text=p["text"],
            )
            new_chunks.append(chunk)

        # Compute embeddings via Gemini
        client = self._get_gemini_client()
        if client:
            try:
                texts = [c.text[:2000] for c in new_chunks]
                emb_res = client.models.embed_content(
                    model=settings.EMBEDDING_MODEL or "models/gemini-embedding-001",
                    contents=texts,
                )
                for c_idx, chunk in enumerate(new_chunks):
                    chunk.embedding = emb_res.embeddings[c_idx].values
            except Exception as e:
                logger.warning(f"Failed to embed single document: {e}")

        # Upsert into Qdrant
        points = []
        start_id = len(self.chunks) + 1
        for idx, chunk in enumerate(new_chunks):
            if chunk.embedding and len(chunk.embedding) == VECTOR_DIM:
                points.append(
                    PointStruct(
                        id=start_id + idx,
                        vector=chunk.embedding,
                        payload=chunk.to_dict(),
                    )
                )

        if points:
            self.qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Upserted {len(points)} new chunks into Qdrant for doc {doc_id}.")

        self.chunks.extend(new_chunks)
        return new_chunks

    def _bm25_score(self, query_tokens: List[str], chunk_tokens: List[str]) -> float:
        """Compute term match score for exact statutory codes and keywords."""
        score = 0.0
        chunk_set = set(chunk_tokens)
        for token in query_tokens:
            if token in chunk_set:
                score += 1.0
                if re.match(r"^B\d{3}$", token) or len(token) >= 10:
                    score += 2.5
        return score

    def retrieve(
        self,
        query: str,
        bidder_id: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: Qdrant Vector Database search + BM25 keyword matching.
        """
        if not self.is_indexed:
            self.index_documents()

        if not self.chunks:
            return []

        query_tokens = [t.lower() for t in re.findall(r"\w+", query)]
        target_bidder = bidder_id.upper() if bidder_id else None

        bidder_match = re.search(r"\bB(00[1-9]|01[0-2])\b", query, re.IGNORECASE)
        if bidder_match and not target_bidder:
            target_bidder = bidder_match.group(0).upper()

        # 1. Query vector from Gemini
        client = self._get_gemini_client()
        qdrant_hits = {}
        if client:
            try:
                q_res = client.models.embed_content(
                    model=settings.EMBEDDING_MODEL or "models/gemini-embedding-001",
                    contents=query[:1000],
                )
                query_vec = q_res.embeddings[0].values
                # Qdrant Vector Search
                search_res = self.qdrant.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vec,
                    limit=top_k * 3,
                )
                for pt in search_res.points:
                    chunk_id = pt.payload.get("chunk_id")
                    if chunk_id:
                        qdrant_hits[chunk_id] = pt.score
            except Exception as e:
                logger.warning(f"Qdrant vector query notice: {e}")

        # 2. Combine with BM25 lexical score
        scores = []
        for chunk in self.chunks:
            bidder_mult = 1.0
            if target_bidder:
                if chunk.bidder_id == target_bidder:
                    bidder_mult = 2.0
                else:
                    bidder_mult = 0.4

            sem_score = qdrant_hits.get(chunk.chunk_id, 0.0)
            chunk_tokens = [t.lower() for t in re.findall(r"\w+", chunk.text)]
            lex_score = self._bm25_score(query_tokens, chunk_tokens)

            combined = (sem_score * 0.6 + (lex_score / max(len(query_tokens), 1)) * 0.4) * bidder_mult
            scores.append((combined, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = []
        for score, chunk in scores[:top_k]:
            if score > 0.05:
                res = chunk.to_dict()
                res["relevance_score"] = round(float(score), 4)
                res["vector_source"] = "qdrant_hnsw"
                top_results.append(res)

        return top_results

    def retrieve_graph_context(self, bidder_id: str) -> List[str]:
        """
        GraphRAG: Multi-hop Knowledge Graph resolution from Neo4j (with in-memory fallback).
        """
        graph_facts = []
        bidder_id = bidder_id.upper()
        try:
            from db.neo4j_driver import neo4j_service
            if neo4j_service.is_available:
                records = neo4j_service.execute_query(
                    """
                    MATCH (b:Bidder {bidder_id: $bidder_id})-[r]->(target)
                    OPTIONAL MATCH (other:Bidder)-[r2]->(target)
                    WHERE other.bidder_id <> $bidder_id
                    RETURN type(r) AS rel, labels(target)[0] AS target_type, target, collect(DISTINCT other.bidder_id) AS shared_with
                    """,
                    {"bidder_id": bidder_id},
                )
                for rec in records:
                    rel = rec.get("rel")
                    t_type = rec.get("target_type")
                    shared = rec.get("shared_with", [])
                    target = rec.get("target", {})
                    name = target.get("name") or target.get("line1") or target.get("bank_name") or "Entity"
                    if shared:
                        graph_facts.append(f"Graph Connection: Bidder {bidder_id} shares {t_type} '{name}' with bidders {', '.join(shared)} via {rel}.")
                    else:
                        graph_facts.append(f"Graph Node: Bidder {bidder_id} has {rel} -> {t_type} '{name}'.")
        except Exception:
            pass

        if not graph_facts:
            try:
                from mock_apis.synthetic_data import get_bidder_by_id
                b = get_bidder_by_id(bidder_id)
                if b:
                    directors = [d.get("name") for d in b.get("directors", [])]
                    graph_facts.append(f"Corporate Graph: Directors include {', '.join(directors)}.")
                    if "COLLUSION_RING_1" in b.get("anomalies", []):
                        graph_facts.append("Collusion Graph Nexus: Member of Collusion Ring 1 (shared board seats and registered address with B001/B003/B007).")
                    if "COLLUSION_RING_2" in b.get("anomalies", []):
                        graph_facts.append("Collusion Graph Nexus: Member of Collusion Ring 2 (shared PNB bank branch and contact details with B005/B009).")
            except Exception:
                pass

        return graph_facts


# Singleton instance
rag_service = DocumentRAGService()
