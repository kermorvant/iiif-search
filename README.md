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

### 1. Export the corpus from Arkindex

Use arkindex to detect photographs in the corpus and export the corpus in csv, with both the pages and the photographs. An example of the csv file is provided in `examples/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a.csv'

### 2. Convert the csv to a manifest

Use the `csv_to_iiif.py` script to convert the csv to a manifest. The script will generate a new manifest file (default: `manifest.json`) containing the `service` definition for the search API.

```bash
python csv_to_iiif.py examples/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a.csv --output examples/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a.json
```

### 3. Indexing a Manifest

To make a manifest searchable, you need to index its images. The script will download images (or crops), compute embeddings, and store them in Qdrant.

```bash
python indexer.py examples/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a.json --output examples/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a_searchable.json
```

This will:
-   Read the input manifest.
-   Index all annotations with "photograph" in their value.
-   Generate a new manifest file (default: `manifest_with_search.json`) containing the `service` definition for the search API.

### 4. Upload the manifest to an accessible URL

For example, you can upload the manifest to a GitHub Pages website. For example:

https://kermorvant.github.io/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a_searchable.json

### 5. Running the Search Service

Start the Flask application:

```bash
python app.py
```

The server will start on port **5001** (or as configured in `app.py`).

### 6. Using the Debug Frontend

Open your browser and navigate to:

[http://localhost:5001/](http://localhost:5001/)

Enter a text query (e.g., "people", "building") to see matching annotations from the indexed manifest.

### 7. Use in Mirdator or Universal Viewer

Load the manifest in Mirdator or Universal Viewer. The search service will be available at the URL configured in the `app.py` file.

You can test with https://kermorvant.github.io/0c10a0ae-4ee8-4527-abc9-9112e4cd2a9a_searchable.json

