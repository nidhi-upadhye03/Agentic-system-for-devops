#!/usr/bin/env python3
"""
Qdrant Vector Store Initialization Script

This script initializes collections and indexes in Qdrant for the LLM application.
It creates collections for different document types and configures appropriate
vector dimensions and distance metrics.
"""

import os
import sys
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    CollectionInfo,
    OptimizersConfigDiff,
    HnswConfigDiff,
    PayloadSchemaType,
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QdrantInitializer:
    """Initialize Qdrant collections and indexes"""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize Qdrant client

        Args:
            url: Qdrant server URL (default: from env or localhost)
            api_key: API key for authentication (default: from env)
            timeout: Request timeout in seconds
        """
        self.url = url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.api_key = api_key or os.getenv('QDRANT_API_KEY')

        logger.info(f"Connecting to Qdrant at {self.url}")

        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=timeout
        )

        # Test connection
        try:
            collections = self.client.get_collections()
            logger.info(f"Successfully connected. Found {len(collections.collections)} existing collections")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        on_disk: bool = False,
        recreate: bool = False
    ) -> bool:
        """
        Create a collection with specified configuration

        Args:
            name: Collection name
            vector_size: Dimension of vectors
            distance: Distance metric (COSINE, EUCLID, DOT)
            on_disk: Store vectors on disk (for large collections)
            recreate: Recreate if exists

        Returns:
            True if created/updated, False if already exists
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(col.name == name for col in collections)

            if exists:
                if recreate:
                    logger.info(f"Deleting existing collection: {name}")
                    self.client.delete_collection(name)
                else:
                    logger.info(f"Collection already exists: {name}")
                    return False

            logger.info(f"Creating collection: {name} (vector_size={vector_size}, distance={distance.value})")

            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=on_disk
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000,
                    memmap_threshold=50000
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                    full_scan_threshold=10000
                )
            )

            logger.info(f"Successfully created collection: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise

    def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: PayloadSchemaType
    ):
        """
        Create an index on a payload field for faster filtering

        Args:
            collection_name: Name of the collection
            field_name: Field to index
            field_schema: Type of the field (KEYWORD, INTEGER, FLOAT, etc.)
        """
        try:
            logger.info(f"Creating payload index on {collection_name}.{field_name}")

            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema
            )

            logger.info(f"Successfully created index on {field_name}")

        except Exception as e:
            logger.error(f"Failed to create index on {field_name}: {e}")
            raise

    def initialize_standard_collections(self, recreate: bool = False):
        """
        Initialize standard collections for the application

        Args:
            recreate: Recreate collections if they exist
        """
        logger.info("Initializing standard collections...")

        collections_config = [
            {
                'name': 'documents',
                'vector_size': 1536,  # OpenAI text-embedding-ada-002 / text-embedding-3-small
                'distance': Distance.COSINE,
                'description': 'General document embeddings',
                'indexes': [
                    ('document_type', PayloadSchemaType.KEYWORD),
                    ('user_id', PayloadSchemaType.KEYWORD),
                    ('timestamp', PayloadSchemaType.INTEGER),
                ]
            },
            {
                'name': 'code_snippets',
                'vector_size': 1536,
                'distance': Distance.COSINE,
                'description': 'Code and technical documentation embeddings',
                'indexes': [
                    ('language', PayloadSchemaType.KEYWORD),
                    ('framework', PayloadSchemaType.KEYWORD),
                    ('user_id', PayloadSchemaType.KEYWORD),
                ]
            },
            {
                'name': 'conversations',
                'vector_size': 1536,
                'distance': Distance.COSINE,
                'description': 'Chat conversation history embeddings',
                'indexes': [
                    ('session_id', PayloadSchemaType.KEYWORD),
                    ('user_id', PayloadSchemaType.KEYWORD),
                    ('timestamp', PayloadSchemaType.INTEGER),
                ]
            },
            {
                'name': 'knowledge_base',
                'vector_size': 3072,  # text-embedding-3-large
                'distance': Distance.COSINE,
                'description': 'High-quality knowledge base embeddings',
                'indexes': [
                    ('category', PayloadSchemaType.KEYWORD),
                    ('source', PayloadSchemaType.KEYWORD),
                    ('priority', PayloadSchemaType.INTEGER),
                ]
            },
            {
                'name': 'user_profiles',
                'vector_size': 1536,
                'distance': Distance.COSINE,
                'description': 'User preference and behavior embeddings',
                'indexes': [
                    ('user_id', PayloadSchemaType.KEYWORD),
                    ('profile_type', PayloadSchemaType.KEYWORD),
                ]
            }
        ]

        # Create collections
        for config in collections_config:
            logger.info(f"\n--- {config['description']} ---")

            self.create_collection(
                name=config['name'],
                vector_size=config['vector_size'],
                distance=config['distance'],
                on_disk=config['vector_size'] > 2000,  # Large embeddings on disk
                recreate=recreate
            )

            # Create payload indexes
            for field_name, field_schema in config.get('indexes', []):
                self.create_payload_index(
                    collection_name=config['name'],
                    field_name=field_name,
                    field_schema=field_schema
                )

        logger.info("\n=== Collection initialization complete ===")

    def get_collection_info(self, name: str) -> Optional[CollectionInfo]:
        """Get information about a collection"""
        try:
            return self.client.get_collection(name)
        except Exception as e:
            logger.error(f"Failed to get collection info for {name}: {e}")
            return None

    def list_collections(self):
        """List all collections with their details"""
        try:
            collections = self.client.get_collections().collections

            logger.info("\n=== Existing Collections ===")
            for col in collections:
                info = self.get_collection_info(col.name)
                if info:
                    logger.info(f"\nCollection: {col.name}")
                    logger.info(f"  Vectors: {info.vectors_count}")
                    logger.info(f"  Points: {info.points_count}")
                    logger.info(f"  Status: {info.status}")

            return collections

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def health_check(self) -> bool:
        """Check if Qdrant is healthy and responsive"""
        try:
            collections = self.client.get_collections()
            logger.info(f"Health check passed. Server has {len(collections.collections)} collections")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Initialize Qdrant collections')
    parser.add_argument(
        '--url',
        default=os.getenv('QDRANT_URL', 'http://localhost:6333'),
        help='Qdrant server URL'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('QDRANT_API_KEY'),
        help='Qdrant API key'
    )
    parser.add_argument(
        '--recreate',
        action='store_true',
        help='Recreate collections if they exist'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List existing collections'
    )
    parser.add_argument(
        '--health',
        action='store_true',
        help='Perform health check only'
    )

    args = parser.parse_args()

    try:
        # Initialize client
        initializer = QdrantInitializer(url=args.url, api_key=args.api_key)

        # Health check
        if args.health:
            if initializer.health_check():
                logger.info("Health check: OK")
                sys.exit(0)
            else:
                logger.error("Health check: FAILED")
                sys.exit(1)

        # List collections
        if args.list:
            initializer.list_collections()
            sys.exit(0)

        # Initialize collections
        initializer.initialize_standard_collections(recreate=args.recreate)

        # Show final status
        initializer.list_collections()

        logger.info("\nInitialization completed successfully!")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
