# Doclingflow

A document processing application that uses Docling and LLMs to process unstructured documents from petrochemical storage terminals, creating a vector database for RAG while simultaneously classifying documents.

## Architecture

### Services (Docker-based)
- **Backend API** (FastAPI) - REST API for document processing and retrieval
- **Celery Worker** - Background processing of documents
- **Qdrant** - Vector database for embeddings
- **PostgreSQL** - Metadata and document information storage
- **Redis** - Task queue and caching
- **Frontend** (Next.js) - Web UI for management and analytics

### Features
- 📁 Automatic folder watching for new documents
- 🤖 LLM-based document classification (Safety, Technical, Business, etc.)
- 🔍 Entity extraction (equipment IDs, chemicals, dates, locations)
- 📊 Analytics dashboard with processing statistics
- 🎯 Vector search for RAG applications
- ⚙️ Configurable settings via UI and YAML
- 🐳 Fully containerized with Docker Compose

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI or Anthropic API key (for LLM processing)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd Doclingflow
```

2. **Create environment file**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here
```

3. **Create .gitkeep files for data directories**
```bash
touch data/inbox/.gitkeep data/processed/.gitkeep data/failed/.gitkeep data/archive/.gitkeep
```

4. **Start the application**
```bash
docker-compose up -d
```

This will start all services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard

### Usage

**Option 1: Drop files into the inbox folder**
```bash
cp your-document.pdf data/inbox/
```
The file watcher will automatically detect and process the document.

**Option 2: Upload via Web UI**
- Navigate to http://localhost:3000
- Use the upload interface to select files or folders
- Monitor processing status in real-time

## Configuration

### Settings File
Edit `config/settings.yaml` to configure:
- Watch folders
- Document classification categories
- LLM provider and models
- Chunk size and overlap
- Entity extraction rules
- Storage paths and retention policies

### Supported Document Types
- PDF (`.pdf`)
- Word Documents (`.docx`)
- Excel Spreadsheets (`.xlsx`)
- PowerPoint (`.pptx`)
- Text files (`.txt`)
- HTML (`.html`)

## Development

### Project Structure
```
doclingflow/
├── backend/               # Python FastAPI backend
│   ├── api/              # API routes
│   ├── core/             # Core configuration
│   ├── services/         # Business logic
│   ├── tasks/            # Celery tasks
│   └── schemas/          # Data models
├── frontend/             # Next.js frontend
│   └── src/
├── config/               # Configuration files
├── data/                 # Document storage
│   ├── inbox/           # Drop new files here
│   ├── processed/       # Successfully processed
│   ├── failed/          # Failed processing
│   └── archive/         # Archived documents
└── docker-compose.yml    # Container orchestration
```

### Running Individual Services

**Backend only:**
```bash
docker-compose up backend
```

**Worker only:**
```bash
docker-compose up celery-worker
```

**View logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Rebuilding After Code Changes
```bash
docker-compose up -d --build
```

## Document Processing Pipeline

1. **File Detection** - Watchdog monitors inbox folder
2. **Ingestion** - Document queued for processing
3. **Docling Extraction** - Text, tables, and structure extracted
4. **Classification** - LLM classifies document category
5. **Entity Extraction** - LLM extracts domain-specific entities
6. **Chunking** - Document split into semantic chunks
7. **Embedding** - Chunks converted to vectors
8. **Storage** - Vectors stored in Qdrant, metadata in PostgreSQL
9. **Completion** - File moved to processed folder

## Monitoring

### Check Service Status
```bash
docker-compose ps
```

### Check Processing Queue
- Navigate to http://localhost:3000/dashboard
- View queue status, processing statistics, and recent documents

### Database Access

**PostgreSQL:**
```bash
docker-compose exec postgres psql -U doclingflow -d doclingflow
```

**Qdrant:**
- Dashboard: http://localhost:6333/dashboard
- API: http://localhost:6333

**Redis:**
```bash
docker-compose exec redis redis-cli
```

## Troubleshooting

### Documents not processing
1. Check celery worker logs: `docker-compose logs celery-worker`
2. Verify API keys in `.env`
3. Check file permissions in `data/inbox/`

### Frontend not connecting to backend
1. Verify `NEXT_PUBLIC_API_URL` in `.env`
2. Check backend is running: `docker-compose ps backend`
3. Check network connectivity: `docker-compose exec frontend ping backend`

### Qdrant connection issues
1. Verify Qdrant is running: `docker-compose ps qdrant`
2. Check `QDRANT_HOST` and `QDRANT_PORT` in `.env`

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes all data)
docker-compose down -v
```

## Next Steps

- [ ] Implement backend core modules (config, database)
- [ ] Create API routes (documents, search, analytics, settings)
- [ ] Build document processing services (Docling, LLM, embeddings)
- [ ] Implement Celery tasks for async processing
- [ ] Create frontend components (Dashboard, Upload, Search, Settings)
- [ ] Add authentication and user management
- [ ] Implement advanced search and filtering
- [ ] Add document preview functionality

## License

MIT
