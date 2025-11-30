import json
import os
import argparse
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from transformers import AutoProcessor, AutoModel
import torch

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
FLASK_APP_URL = os.getenv("FLASK_APP_URL", "http://localhost:5000")
COLLECTION_NAME = "iiif_photos"
MODEL_NAME = "google/siglip-so400m-patch14-384"

def setup_qdrant():
    """Initializes Qdrant client and creates collection if needed."""
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    if not client.collection_exists(COLLECTION_NAME):
        # delete collection if it exists
        if client.collection_exists(COLLECTION_NAME):
            client.delete_collection(COLLECTION_NAME)
        print(f"Creating collection {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1152, distance=Distance.COSINE), # SigLIP2 embedding size
        )
    return client

def load_model():
    """Loads SigLIP2 model and processor."""
    print("Loading SigLIP2 model...")
    # use mps if available
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.to(device)
    model.to(device)
    return processor, model, device

def get_image_embedding(image_url, processor, model, device):
    """Downloads image and computes embedding."""
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # Normalize
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features[0].tolist()
    except Exception as e:
        print(f"Error processing image {image_url}: {e}")
        return None

def process_manifest(manifest_path, output_path):
    """Reads manifest, indexes images, and adds search service."""
    client = setup_qdrant()
    processor, model, device = load_model()

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    points = []
    
    print("Indexing annotations...")
    for canvas in manifest.get('items', []):
        canvas_id = canvas['id']
        
        # Check annotations
        if 'annotations' in canvas:
            for annotation_page in canvas['annotations']:
                for annotation in annotation_page.get('items', []):
                    body = annotation.get('body', {})
                    # Filter for photographs based on value "photograph: ..."
                    if body.get('type') == 'TextualBody' and 'photograph' in body.get('value', '').lower():
                        target = annotation['target']
                        # Extract xywh
                        if '#xywh=' in target:
                            _, xywh = target.split('#xywh=')
                            x, y, w, h = xywh.split(',')
                            
                            # Construct Image API URL for the crop
                            # We need to find the base image service URL from the painting annotation
                            # For simplicity, let's look at the canvas items (painting)
                            painting_ann = canvas['items'][0]['items'][0]
                            image_service_id = painting_ann['body']['service'][0]['id']
                            
                            # Construct crop URL
                            crop_url = f"{image_service_id}/{x},{y},{w},{h}/max/0/default.jpg"
                            
                            print(f"Processing {annotation['id']} - {crop_url}")
                            embedding = get_image_embedding(crop_url, processor, model, device)
                            
                            if embedding:
                                points.append(PointStruct(
                                    id=annotation['id'].split('/')[-1], # Use UUID as ID (assuming it's a UUID) or hash it
                                    vector=embedding,
                                    payload={
                                        "canvas_id": canvas_id,
                                        "annotation_id": annotation['id'],
                                        "label": body.get('value'),
                                        "xywh": xywh,
                                        "thumbnail_url": crop_url
                                    }
                                ))

    if points:
        print(f"Upserting {len(points)} vectors to Qdrant...")
        # Qdrant requires integer or UUID ids. The annotation IDs are URLs ending in UUIDs.
        # Let's try to use the UUID part.
        # If UUID parsing fails, we might need to hash the ID.
        # For this specific dataset, IDs look like UUIDs.
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
        except Exception as e:
            print(f"Error upserting to Qdrant: {e}")
            # Fallback: generate UUIDs? Or just print error.
    
    # Add Search Service to Manifest
    service_block = {
        "@context": "http://iiif.io/api/search/0/context.json",
        "@id": f"{FLASK_APP_URL}/search",
        "profile": "http://iiif.io/api/search/0/search",
        "label": "Image Content Search",
        "service": {
            "@id": f"{FLASK_APP_URL}/search/autocomplete",
            "profile": "http://iiif.io/api/search/0/autocomplete",
            "label": "Autocomplete"
        }
    }
    
    manifest['service'] = [service_block]
    
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Indexed manifest saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index IIIF Manifest images to Qdrant")
    parser.add_argument("manifest", help="Path to input manifest.json")
    parser.add_argument("--output", default="manifest_with_search.json", help="Path to output manifest")
    args = parser.parse_args()

    process_manifest(args.manifest, args.output)
