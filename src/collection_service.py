"""
This file contains the collection service.
"""
from typing import List
import json
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist
from sentence_transformers import SentenceTransformer
from .database import db

class CollectionService:
    """Service for creating and managing collections."""

    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embeddings(self):
        """Generate embeddings for all links that don't have one."""
        links_with_embeddings = []
        all_links = db.get_all_links()
        
        for link in all_links:
            if link.content and not self._has_embedding(link.id):
                embedding = self.embedding_model.encode(link.content)
                self._save_embedding(link.id, embedding.tolist())
                links_with_embeddings.append(link.id)
        
        print(f"Generated embeddings for {len(links_with_embeddings)} links")

    def _has_embedding(self, link_id: str) -> bool:
        """Check if a link has an embedding stored."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding FROM link_data WHERE id = ?", (link_id,))
            row = cursor.fetchone()
            return row and row['embedding'] is not None

    def _save_embedding(self, link_id: str, embedding: List[float]):
        """Save embedding for a link."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE link_data SET embedding = ? WHERE id = ?
            """, (json.dumps(embedding), link_id))

    def _get_embedding(self, link_id: str) -> List[float]:
        """Get embedding for a link."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding FROM link_data WHERE id = ?", (link_id,))
            row = cursor.fetchone()
            if row and row['embedding']:
                return json.loads(row['embedding'])
            return None

    def cluster_links(self, max_clusters=10, min_cluster_size=2):
        """Cluster links based on their embeddings using scipy hierarchical clustering."""
        self.generate_embeddings()
        all_links = db.get_all_links()
        
        # Get links that have embeddings
        links_with_embeddings = []
        embeddings = []
        
        for link in all_links:
            embedding = self._get_embedding(link.id)
            if embedding:
                links_with_embeddings.append(link)
                embeddings.append(embedding)
        
        if len(links_with_embeddings) < min_cluster_size:
            print(f"Not enough links ({len(links_with_embeddings)}) for clustering (minimum: {min_cluster_size})")
            return
        
        embeddings = np.array(embeddings)

        # Calculate pairwise distances and perform hierarchical clustering
        distances = pdist(embeddings, metric='cosine')
        linkage_matrix = linkage(distances, method='ward')
        
        # Determine optimal number of clusters (limited by max_clusters)
        n_clusters = min(max_clusters, len(links_with_embeddings) // min_cluster_size)
        if n_clusters < 2:
            n_clusters = 2
            
        cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')

        # Create collections for each cluster
        cluster_counts = {}
        for i, link in enumerate(links_with_embeddings):
            label = cluster_labels[i]
            if label not in cluster_counts:
                cluster_counts[label] = 0
            cluster_counts[label] += 1
        
        # Only create collections for clusters with minimum size
        created_collections = 0
        for i, link in enumerate(links_with_embeddings):
            label = cluster_labels[i]
            if cluster_counts[label] >= min_cluster_size:
                # Create collection if it doesn't exist
                collection_id = self._get_or_create_collection(f"Cluster {label}", f"Auto-generated cluster {label}")
                db.add_link_to_collection(link.id, collection_id)
                created_collections += 1
        
        print(f"Created collections from {len(links_with_embeddings)} links using hierarchical clustering")

    def _get_or_create_collection(self, name: str, description: str = "") -> int:
        """Get existing collection by name or create a new one."""
        collections = db.get_all_collections()
        for collection_id, collection_name, _ in collections:
            if collection_name == name:
                return collection_id
        return db.create_collection(name, description)
