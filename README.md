# IIIF Content Search System

This project implements a IIIF Content Search API using **SigLIP2** for multimodal embeddings and **Qdrant** as a vector database. It allows users to search for images within a IIIF Manifest using natural language queries.

## Features

-   **IIIF manifest as input**: Extracts "photograph" annotations from a IIIF Manifest and encodes them using the SigLIP2 model.
-   **Vector Search**: Stores embeddings in Qdrant for fast semantic search.
-   **IIIF Search API**: Provides a IIIF Content Search 1.0 compliant endpoint.
-   **Debug Frontend**: A simple web interface to test search queries.

## Prerequisites

-   Python 3.10+
-   A Qdrant instance (Cloud or Local).

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project directory.

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

2.  Edit `.env` and provide your Qdrant credentials and app settings:
    ```ini
    QDRANT_URL=https://your-qdrant-url
    QDRANT_API_KEY=your-api-key
    FLASK_APP_URL=http://localhost:5001
    ```

## Usage

### 1. Indexing a Manifest

To make a manifest searchable, you need to index its images. The script will download images (or crops), compute embeddings, and store them in Qdrant.

```bash
python indexer.py path/to/manifest.json
```

This will:
-   Read the input manifest.
-   Index all annotations with "photograph" in their value.
-   Generate a new manifest file (default: `manifest_with_search.json`) containing the `service` definition for the search API.

### 2. Running the Search Service

Start the Flask application:

```bash
python app.py
```

The server will start on port **5001** (or as configured in `app.py`).

### 3. Using the Debug Frontend

Open your browser and navigate to:

[http://localhost:5001/](http://localhost:5001/)

Enter a text query (e.g., "people", "building") to see matching annotations from the indexed manifest.

### 4. API Usage

The search endpoint follows the IIIF Content Search API pattern:

```
GET /search?q=<query>
```

**Example**:
```bash
curl "http://localhost:5001/search?q=a%20group%20of%20people"
```

**Response**:
Returns a IIIF `AnnotationList` containing matching resources.

## Project Structure

-   `indexer.py`: Script to process manifests and populate Qdrant.
-   `app.py`: Flask application serving the API and frontend.
-   `templates/index.html`: Debug frontend template.
-   `requirements.txt`: Python dependencies.
