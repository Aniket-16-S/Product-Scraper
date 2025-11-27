import os
import json
import pickle
import numpy as np
import faiss
import nltk
import uuid
from nltk.stem import PorterStemmer
from sentence_transformers import SentenceTransformer
from rapidfuzz import fuzz

# Download NLTK data (only runs once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class IntelligentSearchEngine:
    def __init__(self, model_name='all-MiniLM-L6-v2', folder_path='search_engine_data'):
        self.folder_path = folder_path
        self.index_file = os.path.join(folder_path, "faiss_index.bin")
        self.metadata_file = os.path.join(folder_path, "metadata_v2.pkl") # Changed to v2 for new schema
        
        # 1. Load AI Model
        print("Loading AI Model...")
        self.model = SentenceTransformer(model_name)
        self.dimension = 384 # Dimension for MiniLM-L6-v2
        self.stemmer = PorterStemmer()

        # 2. Initialize FAISS and Metadata
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        self.index = None
        
        # New Data Structures for UUID Management
        # UUID -> Product Data (Original Text, etc.)
        self.products_map = {} 
        # UUID -> Normalized Text (for fuzzy check)
        self.normalized_map = {} 
        # List to map FAISS Integer Index -> UUID
        self.index_to_uuid = [] 
        
        self.load_data()

    def normalize(self, text):
        """
        Crucial Step: Lowercase + Stemming
        'Womens Kurties' -> 'women kurti'
        """
        text = str(text).lower().strip()
        # Remove punctuation for better matching
        text = "".join([c if c.isalnum() or c.isspace() else " " for c in text])
        words = text.split()
        stemmed = [self.stemmer.stem(word) for word in words]
        return " ".join(stemmed)

    def add_products(self, new_products):
        """
        Adds a list of product strings to the engine.
        Assigns a unique UUID to each product.
        """
        if not new_products:
            return

        print(f"Processing {len(new_products)} new products...")
        
        # 1. Normalize Text & Generate UUIDs
        new_entries = []
        norm_texts = []
        
        for p in new_products:
            norm = self.normalize(p)
            uid = str(uuid.uuid4())
            new_entries.append((uid, p, norm))
            norm_texts.append(norm)

        # 2. Create Embeddings
        embeddings = self.model.encode(norm_texts)
        faiss.normalize_L2(embeddings) # Essential for Cosine Similarity in FAISS

        # 3. Add to FAISS
        if self.index is None:
            # HNSW is fast and accurate
            self.index = faiss.IndexHNSWFlat(self.dimension, 32) 
            self.index.hnsw.efConstruction = 40
        
        self.index.add(np.array(embeddings).astype('float32'))

        # 4. Update Metadata Maps
        for uid, original, norm in new_entries:
            self.products_map[uid] = original
            self.normalized_map[uid] = norm
            self.index_to_uuid.append(uid)
        
        # 5. Auto-Save
        self.save_data()
        print(f"Index updated. Total products: {len(self.products_map)}")

    def check_negative_filter(self, query_text, result_text):
        """
        Hard Filter: Returns True if the result should be REJECTED.
        Logic: If 'men' in query and 'women' in result (and vice versa).
        """
        q = query_text.lower()
        r = result_text.lower()
        
        # Clean punctuation
        q = "".join([c if c.isalnum() or c.isspace() else " " for c in q])
        r = "".join([c if c.isalnum() or c.isspace() else " " for c in r])

        q_words = set(q.split())
        r_words = set(r.split())

        # Define Gender Terms
        men_terms = {'men', "man", "male", "boy", "gentleman", "mens"}
        women_terms = {'women', "woman", "female", "girl", "lady", "womens"}

        has_men_q = bool(q_words & men_terms)
        has_women_q = bool(q_words & women_terms)
        
        has_men_r = bool(r_words & men_terms)
        has_women_r = bool(r_words & women_terms)

        # Rule 1: Query is for MEN, Result is for WOMEN (and not Men)
        if has_men_q and not has_women_q:
            if has_women_r and not has_men_r:
                return True # REJECT

        # Rule 2: Query is for WOMEN, Result is for MEN (and not Women)
        if has_women_q and not has_men_q:
            if has_men_r and not has_women_r:
                return True # REJECT
                
        return False # ACCEPT

    def search(self, user_query, threshold=0.65):
        """
        Smart Search:
        1. Try Vector Search (FAISS)
        2. Apply Negative Filtering
        3. Double check with Fuzzy Match (RapidFuzz)
        """
        # 1. Normalize Query
        norm_query = self.normalize(user_query)
        
        # 2. Vector Search
        query_vec = self.model.encode([norm_query])
        faiss.normalize_L2(query_vec)
        
        # Search Top K candidates (Fetch more to allow for filtering)
        k = 5 
        if self.index is None or self.index.ntotal == 0:
            return user_query, False

        distances, indices = self.index.search(np.array(query_vec).astype('float32'), k)
        
        # Iterate through candidates to find the first valid one
        for i in range(k):
            idx = indices[0][i]
            score = distances[0][i]
            
            if idx == -1: continue
            
            # Retrieve Data using UUID
            try:
                uid = self.index_to_uuid[idx]
                found_product = self.products_map[uid]
                found_product_norm = self.normalized_map[uid]
            except IndexError:
                continue

            # --- NEGATIVE FILTERING ---
            if self.check_negative_filter(user_query, found_product):
                print(f"   [Filter] Rejected '{found_product}' for query '{user_query}' (Gender Mismatch)")
                continue # Skip this candidate
            
            # --- DECISION LOGIC ---
            
            # CASE A: Strong Vector Match
            if score > 0.8:
                return found_product, True

            # CASE B: Weak/Medium Vector Match -> Verify with Fuzzy Logic
            fuzzy_score = fuzz.ratio(norm_query, found_product_norm) / 100.0
            
            print(f"   [Debug] Query: '{norm_query}' | Match: '{found_product_norm}'")
            print(f"   [Debug] Vector Score: {score:.3f} | Fuzzy Score: {fuzzy_score:.3f}")

            if fuzzy_score > 0.85:
                return found_product, True
                
            if score > threshold:
                 return found_product, True
        
        return user_query, False

    def save_data(self):
        # Save FAISS Index
        faiss.write_index(self.index, self.index_file)
        # Save Metadata
        with open(self.metadata_file, 'wb') as f:
            pickle.dump({
                'products_map': self.products_map, 
                'normalized_map': self.normalized_map,
                'index_to_uuid': self.index_to_uuid
            }, f)

    def load_data(self):
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            print("Loading existing index from disk...")
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self.products_map = data.get('products_map', {})
                    self.normalized_map = data.get('normalized_map', {})
                    self.index_to_uuid = data.get('index_to_uuid', [])
            except Exception as e:
                print(f"Error loading data: {e}. Starting fresh.")
                self.index = None
                self.products_map = {}
                self.normalized_map = {}
                self.index_to_uuid = []
        else:
            print("No existing index found. Starting fresh.")

    def rebuild_index(self, all_products):
        """
        Rebuilds the entire index from a list of product names.
        Useful for syncing with the database after deletions.
        """
        print(f"Rebuilding index with {len(all_products)} products...")
        
        # Reset Data Structures
        self.index = None
        self.products_map = {}
        self.normalized_map = {}
        self.index_to_uuid = []
        
        # Add products (this will handle normalization, embedding, and saving)
        if all_products:
            self.add_products(all_products)
        else:
            # If empty, just save the empty state
            self.save_data()
            print("Index cleared.")

# --- EXECUTION ---

# Initialize Engine (Global Instance)
engine = IntelligentSearchEngine()

if __name__ == "__main__":
    # Add Data (Only needed once, it saves automatically)
    # engine.add_products([
    #     "Women Cotton Kurti", 
    #     "Men Blue Jeans", 
    #     "Samsung Galaxy S23",
    #     "Nike Running Shoes",
    #     "Men's Kurta"
    # ])

    # Test Cases
    queries = [
        "Womens Kurties",       # Test: Plural + Normalization
        "Pure Cooton Kurti",    # Test: Typo (Cooton)
        "Galaxy s23 phone",     # Test: Semantic (Phone keyword implied)
        "Red Lipstick",         # Test: Unknown item
        "Women's Kurti"         # Test: Negative Filter (Should NOT match Men's Kurta)
    ]
    
    print("-" * 30)
    for q in queries:
        result, found = engine.search(q)
        status = "FOUND" if found else "SCRAPE NEEDED"
        print(f"Query: '{q}' -> Result: '{result}' ({status})")
        print("-" * 30)
