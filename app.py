from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from transformers import AutoProcessor, AutoModel
import torch
import logging
import json

# configure logging
logging.basicConfig(level=logging.INFO) 
# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "iiif_photos"
MODEL_NAME = "google/siglip-so400m-patch14-384"

# Initialize Qdrant Client
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Initialize Model (Lazy loading might be better for startup time, but let's load on start)
print("Loading SigLIP2 model...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def get_text_embedding(text):
    """Computes embedding for text query."""
    inputs = processor(text=[text], return_tensors="pt", padding="max_length")
    # log the inputs for debugging
    #logging.info(f"Text: {text}")
    #logging.info(f"Inputs: {inputs}")
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    # log the text features for debugging
    #logging.info(f"Text features: {text_features}")
    # Normalize
    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
    # log the normalized text features for debugging
    #logging.info(f"Normalized text features: {text_features}")
    return text_features[0].tolist()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    manifest_id = request.args.get('manifest') # Optional filter by manifest
    # log the query for debugging
    logging.info(f"Search query: {query}")

    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    try:
        # Encode query
        vector = get_text_embedding(query)

        # Search Qdrant
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=10 # Default limit
        ).points

        # Format as IIIF AnnotationList
        resources = []
        hits = []
        for i, hit in enumerate(search_result):
            payload = hit.payload
            anno_id = f"{request.base_url}/anno/{i}"
            
            resource = {
                "@id": anno_id,
                "@type": "oa:Annotation",
                "motivation": "sc:painting",
                "resource": {
                    "@type": "cnt:ContentAsText",
                    "chars": payload.get('label', 'Match')
                },
                "on": f"{payload['canvas_id']}#xywh={payload['xywh']}"
            }
            if payload.get('thumbnail_url'):
                resource['thumbnail'] = payload.get('thumbnail_url')
                
            resources.append(resource)
            
            hits.append({
                "@type": "search:Hit",
                "annotations": [anno_id]
            })

        response = {
            "@context": [
                "http://iiif.io/api/presentation/2/context.json",
                "http://iiif.io/api/search/0/context.json"
            ],
            "@id": request.url,
            "@type": "sc:AnnotationList",
            "within": {
                "@type": "sc:Layer",
                "total": len(resources)
            },
            "resources": resources,
            "hits": hits
        }
        logging.info(f"Search response: {response}")

        return jsonify(response)

    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/search/autocomplete', methods=['GET'])
def autocomplete():
    # Placeholder for autocomplete
    return jsonify({
        "@context": "http://iiif.io/api/search/1/context.json",
        "@id": request.url,
        "@type": "search:TermList",
        "terms": []
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
