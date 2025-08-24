/**
 * Web Worker for search operations
 * Handles MiniSearch operations in a separate thread to keep UI responsive
 */

// Import MiniSearch in Web Worker
importScripts('https://cdn.jsdelivr.net/npm/minisearch@6.3.0/dist/umd/index.min.js');

class SearchWorker {
    constructor() {
        this.searchIndex = null;
        this.searchData = null;
    }
    
    initialize(data) {
        try {
            this.searchData = data;
            
            // Initialize MiniSearch index
            this.searchIndex = new MiniSearch({
                fields: ['title', 'summary', 'tags', 'category', 'subcategory'],
                storeFields: [
                    'id', 'url', 'title', 'summary', 'tags', 
                    'category', 'subcategory', 'content_type', 
                    'difficulty', 'quality_score'
                ],
                searchOptions: {
                    boost: { 
                        title: 2, 
                        category: 1.5,
                        tags: 1.3
                    },
                    fuzzy: 0.2,
                    prefix: true,
                    combineWith: 'AND'
                }
            });
            
            // Add all documents to the index
            this.searchIndex.addAll(this.searchData.docs);
            
            // Send initialization confirmation
            self.postMessage({
                type: 'initialized',
                docCount: this.searchData.docs.length
            });
            
        } catch (error) {
            self.postMessage({
                type: 'error',
                message: error.message
            });
        }
    }
    
    search(query, filters = {}) {
        try {
            if (!this.searchIndex) {
                throw new Error('Search index not initialized');
            }
            
            let results = [];
            
            if (query && query.trim()) {
                // Perform text search
                results = this.searchIndex.search(query.trim(), {
                    limit: 100,
                    fuzzy: 0.2,
                    prefix: true
                });
            } else {
                // No query - return all documents with basic scoring
                results = this.searchData.docs.map(doc => ({
                    id: doc.id,
                    score: 1,
                    ...doc
                }));
            }
            
            // Apply filters
            results = this.applyFilters(results, filters);
            
            // Sort by score (descending) and limit results
            results.sort((a, b) => (b.score || 0) - (a.score || 0));
            results = results.slice(0, 50);
            
            // Send results back to main thread
            self.postMessage({
                type: 'search_results',
                results: results,
                query: query,
                totalFound: results.length
            });
            
        } catch (error) {
            self.postMessage({
                type: 'error',
                message: error.message
            });
        }
    }
    
    applyFilters(results, filters) {
        if (!filters) return results;
        
        return results.filter(result => {
            // Category filter
            if (filters.category && filters.category !== '') {
                if (result.category !== filters.category) {
                    return false;
                }
            }
            
            // Content type filter
            if (filters.content_type && filters.content_type !== '') {
                if (result.content_type !== filters.content_type) {
                    return false;
                }
            }
            
            // Difficulty filter
            if (filters.difficulty && filters.difficulty !== '') {
                if (result.difficulty !== filters.difficulty) {
                    return false;
                }
            }
            
            // Quality score filter (optional)
            if (filters.min_quality && typeof filters.min_quality === 'number') {
                if ((result.quality_score || 0) < filters.min_quality) {
                    return false;
                }
            }
            
            return true;
        });
    }
    
    getStats() {
        if (!this.searchData) {
            return null;
        }
        
        const docs = this.searchData.docs;
        const categories = new Set();
        const contentTypes = new Set();
        const difficulties = new Set();
        
        docs.forEach(doc => {
            if (doc.category) categories.add(doc.category);
            if (doc.content_type) contentTypes.add(doc.content_type);
            if (doc.difficulty) difficulties.add(doc.difficulty);
        });
        
        return {
            totalDocs: docs.length,
            categories: Array.from(categories).sort(),
            contentTypes: Array.from(contentTypes).sort(),
            difficulties: Array.from(difficulties).sort()
        };
    }
}

// Initialize worker
const searchWorker = new SearchWorker();

// Handle messages from main thread
self.addEventListener('message', (event) => {
    const { type, data, query, filters } = event.data;
    
    switch (type) {
        case 'initialize':
            searchWorker.initialize(data);
            break;
            
        case 'search':
            searchWorker.search(query, filters);
            break;
            
        case 'stats':
            const stats = searchWorker.getStats();
            self.postMessage({
                type: 'stats_response',
                stats: stats
            });
            break;
            
        default:
            self.postMessage({
                type: 'error',
                message: `Unknown message type: ${type}`
            });
    }
});

// Handle worker errors
self.addEventListener('error', (error) => {
    self.postMessage({
        type: 'error',
        message: error.message || 'Unknown worker error'
    });
});

// Send ready signal
self.postMessage({
    type: 'worker_ready'
});