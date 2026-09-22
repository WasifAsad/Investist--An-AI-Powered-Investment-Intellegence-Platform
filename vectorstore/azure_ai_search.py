import hashlib
import logging
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class AzureAISearchVectorStore:
    """
    Azure AI Search vector store manager for indexing and querying chunks.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str,
        vector_dimensions: int = 3072,
    ):
        if not endpoint or not api_key or not index_name:
            raise ValueError(
                "Azure Search endpoint, api_key, and index_name must be provided."
            )

        self.endpoint = endpoint.strip().strip('"').strip("'")
        self.api_key = api_key.strip().strip('"').strip("'")
        self.index_name = index_name.strip().strip('"').strip("'")
        self.vector_dimensions = vector_dimensions

        self.credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
        self.client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create the Azure AI Search index if it does not already exist."""
        try:
            existing_indexes = list(self.index_client.list_index_names())
            if self.index_name in existing_indexes:
                logger.info(f"Index '{self.index_name}' already exists.")
                return

            print(f"Index '{self.index_name}' not found. Creating index...")
            algorithm_config_name = "hnsw-config"
            profile_name = "vector-profile"

            algo = HnswAlgorithmConfiguration(name=algorithm_config_name)
            profile = VectorSearchProfile(
                name=profile_name,
                algorithm_configuration_name=algorithm_config_name,
            )
            vector_search = VectorSearch(
                algorithms=[algo],
                profiles=[profile],
            )

            fields = [
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                    sortable=True,
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                ),
                SearchableField(
                    name="company",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    facetable=True,
                ),
                SearchableField(
                    name="year",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    facetable=True,
                ),
                SearchableField(
                    name="source_file",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="chunk_index",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                    sortable=True,
                ),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.vector_dimensions,
                    vector_search_profile_name=profile_name,
                ),
            ]

            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
            )
            self.index_client.create_index(index)
            print(f"Successfully created Azure AI Search index '{self.index_name}'.")
        except Exception as e:
            logger.warning(
                f"Could not verify or create index '{self.index_name}': {e}"
            )
            print(f"Warning: Index verification/creation encountered: {e}")

    def upload_chunks(
        self,
        chunks: List[Any],
        embeddings: Any,
        company: str,
        year: str,
        source_file: str,
        batch_size: int = 50,
    ) -> None:
        """
        Embed chunks and upload them to Azure AI Search index.

        Args:
            chunks: List of Document objects or strings.
            embeddings: Embeddings model with embed_documents method.
            company: Company name.
            year: Fiscal or report year.
            source_file: Name of the source file.
            batch_size: Batch size for document upload.
        """
        if not chunks:
            print("No chunks provided to upload.")
            return

        texts = [
            chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
            for chunk in chunks
        ]

        print(f"Generating embeddings for {len(texts)} chunks...")
        vectors = embeddings.embed_documents(texts)

        documents: List[Dict[str, Any]] = []
        for idx, (chunk_text, vector) in enumerate(zip(texts, vectors)):
            # Deterministic, unique ID conforming to Azure Search key constraints
            seed = f"{source_file}_{company}_{year}_{idx}"
            doc_id = hashlib.md5(seed.encode("utf-8")).hexdigest()

            documents.append(
                {
                    "id": doc_id,
                    "content": chunk_text,
                    "company": str(company),
                    "year": str(year),
                    "source_file": str(source_file),
                    "chunk_index": idx,
                    "embedding": vector,
                }
            )

        total_batches = (len(documents) + batch_size - 1) // batch_size
        print(
            f"Uploading {len(documents)} chunks to index '{self.index_name}' "
            f"in {total_batches} batch(es)..."
        )

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            results = self.client.merge_or_upload_documents(documents=batch)
            succeeded = sum(1 for r in results if r.succeeded)
            print(
                f"Batch {i // batch_size + 1}/{total_batches}: "
                f"{succeeded}/{len(batch)} documents indexed."
            )


class Retriever:
    """
    Retriever class for querying document chunks from Azure AI Search.
    """

    def __init__(self, client: SearchClient, embeddings: Optional[Any] = None):
        self.client = client
        self.embeddings = embeddings

    def search(
        self,
        query: str,
        top: int = 5,
        filter: Optional[str] = None,
        vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search documents using vector, hybrid, or full-text search.
        """
        vector_queries = []
        if vector is not None:
            vector_queries.append(
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=top,
                    fields="embedding",
                )
            )
        elif self.embeddings is not None and hasattr(self.embeddings, "embed_query"):
            try:
                emb = self.embeddings.embed_query(query)
                vector_queries.append(
                    VectorizedQuery(
                        vector=emb,
                        k_nearest_neighbors=top,
                        fields="embedding",
                    )
                )
            except Exception as e:
                logger.warning(f"Error computing query embedding: {e}")

        results = self.client.search(
            search_text=query if query else None,
            vector_queries=vector_queries if vector_queries else None,
            filter=filter,
            top=top,
        )

        return [dict(doc) for doc in results]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k matching chunks as dictionaries."""
        return self.search(query=query, top=top_k, filter=filter_expr)

    def get_relevant_documents(self, query: str) -> List[Document]:
        """LangChain-compatible retrieval returning Document objects."""
        raw_docs = self.search(query=query, top=5)
        return [
            Document(
                page_content=doc.get("content", ""),
                metadata={k: v for k, v in doc.items() if k != "content"},
            )
            for doc in raw_docs
        ]

    def __call__(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.search(query=query, **kwargs)
