"""
This file contains the collection service.
"""
from typing import List
from sentence_transformers import SentenceTransformer
from src.database import Session, LinkData, Collection

# The user needs to install hdbscan manually
# uv pip install hdbscan
try:
    import hdbscan
except ImportError:
    print("hdbscan not found. Please install it with 'uv pip install hdbscan'")
    hdbscan = None

class CollectionService:
    """Service for creating and managing collections."""

    def __init__(self, session):
        self.session = session
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embeddings(self):
        """Generate embeddings for all links that don't have one."""
        links = self.session.query(LinkData).filter(LinkData.embedding == None).all()
        for link in links:
            if link.content:
                embedding = self.embedding_model.encode(link.content)
                link.embedding = embedding.tolist()
        self.session.commit()

    def cluster_links(self):
        """Cluster links based on their embeddings."""
        if hdbscan is None:
            raise ImportError("hdbscan is not installed. Please install it with 'uv pip install hdbscan'")

        self.generate_embeddings()
        links = self.session.query(LinkData).filter(LinkData.embedding != None).all()
        embeddings = [link.embedding for link in links]

        clusterer = hdbscan.HDBSCAN(min_cluster_size=2)
        cluster_labels = clusterer.fit_predict(embeddings)

        # Clear existing collections
        self.session.query(Collection).delete()
        self.session.commit()

        for i, link in enumerate(links):
            label = cluster_labels[i]
            if label != -1:
                collection = self.session.query(Collection).filter_by(id=int(label)).first()
                if collection is None:
                    collection = Collection(id=int(label), name=f"Collection {label}")
                    self.session.add(collection)
                collection.links.append(link)
        self.session.commit()
