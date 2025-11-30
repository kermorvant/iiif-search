import csv
import json
import argparse
import ast
from collections import defaultdict

def parse_polygon(polygon_str):
    """Parses the polygon string into a list of points."""
    try:
        return ast.literal_eval(polygon_str)
    except (ValueError, SyntaxError):
        return []

def get_bbox(polygon):
    """Calculates the bounding box (x, y, w, h) from a polygon."""
    if not polygon:
        return 0, 0, 0, 0
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return min_x, min_y, max_x - min_x, max_y - min_y

def create_manifest(csv_file_path, output_file_path):
    """Reads CSV and generates a IIIF Manifest."""
    
    # Group rows by image_id
    images = defaultdict(list)
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            images[row['image_id']].append(row)

    manifest = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": "https://storage.teklia.com/public/test/manifest.json",
        "type": "Manifest",
        "label": { "en": [ "Generated Manifest from CSV" ] },
        "items": []
    }

    for image_id, rows in images.items():
        # Find the 'page' row to define the Canvas
        page_row = next((r for r in rows if r['type'] == 'page'), None)
        
        # If no page row, try to infer from the first row or skip? 
        # Let's use the first row if no page row, but we need dimensions.
        if not page_row:
            # Fallback: use the first row and try to infer dimensions from union of all polygons?
            # For now, let's just warn and skip or use a default if strictly required.
            # But the prompt implies 'page' exists for the image.
            # Let's assume there is at least one row.
            if not rows: continue
            main_row = rows[0]
            # Calculate union bbox of all annotations to guess canvas size
            all_polys = [parse_polygon(r['polygon']) for r in rows]
            all_points = [p for poly in all_polys for p in poly]
            if all_points:
                _, _, width, height = get_bbox(all_points)
            else:
                width, height = 1000, 1000 # Fallback
        else:
            main_row = page_row
            polygon = parse_polygon(page_row['polygon'])
            _, _, width, height = get_bbox(polygon)

        canvas_id = f"https://storage.teklia.com/public/test/canvas/{image_id}"
        
        canvas = {
            "id": canvas_id,
            "type": "Canvas",
            "width": width,
            "height": height,
            "label": { "none": [ main_row['name'] ] },
            "items": [
                {
                    "id": f"{canvas_id}/annotation/page",
                    "type": "AnnotationPage",
                    "items": [
                        {
                            "id": f"{canvas_id}/annotation/image",
                            "type": "Annotation",
                            "motivation": "painting",
                            "body": {
                                "id": f"{main_row['image_url']}/full/max/0/default.jpg",
                                "type": "Image",
                                "format": "image/jpeg",
                                "service": [
                                    {
                                        "id": main_row['image_url'],
                                        "type": "ImageService2",
                                        "profile": "level1"
                                    }
                                ],
                                "width": width,
                                "height": height
                            },
                            "target": canvas_id
                        }
                    ]
                }
            ],
            "annotations": []
        }

        # Add other annotations
        annotation_page_id = f"{canvas_id}/annotations"
        annotation_page = {
            "id": annotation_page_id,
            "type": "AnnotationPage",
            "items": []
        }

        for row in rows:
            if row['type'] == 'page':
                continue # Already handled as the painting annotation

            poly = parse_polygon(row['polygon'])
            x, y, w, h = get_bbox(poly)
            
            ann_id = f"{canvas_id}/annotation/{row['id']}"
            annotation = {
                "id": ann_id,
                "type": "Annotation",
                "motivation": "commenting",
                "body": {
                    "type": "TextualBody",
                    "value": f"{row['type']}: {row['name']}",
                    "format": "text/plain"
                },
                "target": f"{canvas_id}#xywh={x},{y},{w},{h}"
            }
            annotation_page['items'].append(annotation)

        if annotation_page['items']:
            canvas['annotations'].append(annotation_page)
        
        manifest['items'].append(canvas)

    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest created at {output_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CSV to IIIF Manifest")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("--output", default="manifest.json", help="Path to the output JSON file")
    args = parser.parse_args()

    create_manifest(args.csv_file, args.output)
