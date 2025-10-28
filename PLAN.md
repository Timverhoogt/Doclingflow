# Doclingflow Development Plan

## Project Preferences

### Technology Stack
- **Vector Database**: Qdrant (self-hosted, familiar)
- **Deployment**: Docker containers (all services containerized)
- **LLM Provider**: OpenRouter API (using Claude models - claude-3.5-sonnet preferred)
- **Embeddings**: OpenRouter API (using OpenAI text-embedding-3-small)
- **Backend**: Python 3.11, FastAPI
- **Frontend**: Next.js with TypeScript
- **Task Queue**: Celery + Redis
- **Metadata DB**: PostgreSQL

### Domain Context
- **Industry**: Petrochemical storage terminals
- **Document Types**:
  - Business documents (invoices, contracts, reports)
  - Technical documents (specifications, datasheets)
  - Safety documents (SDS, MSDS, hazard sheets)
  - Equipment manuals (maintenance, operations)
  - Regulatory compliance (permits, certificates)
  - Operational procedures (SOPs)

---

## Phase 1: Core Backend Infrastructure ✅

### 1.1 Configuration & Database Setup
- [x] Create `backend/core/config.py` - Settings loader (YAML + env vars)
- [x] Create `backend/core/database.py` - PostgreSQL connection and session management
- [x] Create `backend/schemas/models.py` - SQLAlchemy models for documents, processing jobs
- [x] Create database migration setup with Alembic
- [x] Create `backend/core/qdrant_client.py` - Qdrant connection wrapper

### 1.2 Document Models & Schemas
- [x] Create `backend/schemas/document.py` - Pydantic models for API
- [x] Create `backend/schemas/classification.py` - Classification schemas
- [x] Create `backend/schemas/processing.py` - Processing job schemas

### 1.3 Basic API Structure
- [x] Create `backend/api/main.py` - FastAPI app initialization
- [x] Create `backend/api/routes/health.py` - Health check endpoints
- [x] Create `backend/api/routes/documents.py` - Document CRUD endpoints
- [x] Create `backend/api/dependencies.py` - Dependency injection (DB sessions, etc.)

---

## Phase 2: Document Processing Pipeline ✅

### 2.1 File Watching & Ingestion
- [x] Create `backend/services/file_watcher.py` - Monitor inbox folder with watchdog
- [x] Create `backend/services/file_handler.py` - File validation and metadata extraction
- [x] Create `backend/tasks/__init__.py` - Celery app initialization
- [x] Create `backend/tasks/ingestion.py` - Document ingestion tasks

### 2.2 Docling Integration
- [x] Create `backend/services/docling_processor.py` - Document parsing with Docling
- [x] Add support for PDF extraction
- [x] Add support for DOCX extraction
- [x] Add support for XLSX extraction
- [x] Add support for PPTX extraction
- [x] Create error handling for unsupported formats

### 2.3 LLM Classification Service
- [x] Create `backend/services/llm_client.py` - LLM provider abstraction (OpenAI/Anthropic)
- [x] Create `backend/services/classifier.py` - Document classification logic
- [x] Create prompts for petrochemical document classification
- [x] Implement category mapping (Safety, Technical, Business, Equipment, etc.)
- [x] Add confidence scoring

### 2.4 Entity Extraction
- [x] Create `backend/services/entity_extractor.py` - LLM-based entity extraction
- [x] Create prompts for extracting:
  - Equipment IDs
  - Chemical names
  - Dates and timestamps
  - Locations and facilities
  - Personnel names
  - Measurements and values
- [x] Store extracted entities in document metadata

### 2.5 Chunking & Embeddings
- [x] Create `backend/services/chunker.py` - Semantic chunking logic
- [x] Implement chunk size/overlap from settings
- [x] Create `backend/services/embedder.py` - Embedding generation
- [x] Support OpenAI embeddings (text-embedding-3-small)
- [x] Add fallback to sentence-transformers for local embeddings

### 2.6 Vector Storage
- [x] Create `backend/services/vector_store.py` - Qdrant operations
- [x] Implement collection creation
- [x] Implement vector upsert with metadata
- [x] Implement vector search functionality
- [x] Add filtering by document classification

### 2.7 Complete Processing Pipeline
- [x] Create `backend/tasks/processing.py` - Main document processing Celery task
- [x] Orchestrate: Docling → Classify → Extract → Chunk → Embed → Store
- [x] Add progress tracking
- [x] Implement retry logic for failures
- [x] Move processed files to appropriate folders

---

## Phase 3: API Endpoints ✅

### 3.1 Document Management
- [x] `POST /api/documents/upload` - Manual file upload
- [x] `GET /api/documents` - List documents with filters
- [x] `GET /api/documents/{id}` - Get document details
- [x] `DELETE /api/documents/{id}` - Delete document
- [x] `GET /api/documents/{id}/chunks` - Get document chunks

### 3.2 Search & Retrieval
- [x] Create `backend/api/routes/search.py`
- [x] `POST /api/search/semantic` - Vector similarity search
- [x] `POST /api/search/hybrid` - Combine vector + keyword search
- [x] `GET /api/search/filters` - Get available filters (categories, dates, etc.)

### 3.3 Analytics & Statistics
- [x] Create `backend/api/routes/analytics.py`
- [x] `GET /api/analytics/overview` - Processing stats (total docs, by category, etc.)
- [x] `GET /api/analytics/timeline` - Documents processed over time
- [x] `GET /api/analytics/categories` - Distribution by classification
- [x] `GET /api/analytics/processing-queue` - Current queue status

### 3.4 Settings Management
- [x] Create `backend/api/routes/settings.py`
- [x] `GET /api/settings` - Get current settings
- [x] `PATCH /api/settings` - Update settings
- [x] `GET /api/settings/watch-folders` - List watch folders
- [x] `POST /api/settings/watch-folders` - Add watch folder
- [x] `DELETE /api/settings/watch-folders/{path}` - Remove watch folder

### 3.5 Processing Jobs
- [x] Create `backend/api/routes/jobs.py`
- [x] `GET /api/jobs` - List processing jobs
- [x] `GET /api/jobs/{id}` - Get job status
- [x] `POST /api/jobs/{id}/retry` - Retry failed job
- [x] `DELETE /api/jobs/{id}` - Cancel job

---

## Phase 4: Frontend Development ✅

### 4.1 Project Setup
- [x] Create Next.js config (`next.config.js`)
- [x] Create TailwindCSS config (`tailwind.config.js`)
- [x] Create `frontend/src/app/layout.tsx` - Root layout
- [x] Create `frontend/src/app/page.tsx` - Home/Dashboard page
- [x] Set up React Query provider

### 4.2 API Client
- [x] Create `frontend/src/services/api.ts` - Axios instance
- [x] Create `frontend/src/services/documents.ts` - Document API calls
- [x] Create `frontend/src/services/search.ts` - Search API calls
- [x] Create `frontend/src/services/analytics.ts` - Analytics API calls
- [x] Create `frontend/src/services/settings.ts` - Settings API calls

### 4.3 Shared Components
- [x] Create `frontend/src/components/ui/Button.tsx`
- [x] Create `frontend/src/components/ui/Card.tsx`
- [x] Create `frontend/src/components/ui/Input.tsx`
- [x] Create `frontend/src/components/ui/Select.tsx`
- [x] Create `frontend/src/components/ui/Badge.tsx`
- [x] Create `frontend/src/components/ui/Table.tsx`
- [x] Create `frontend/src/components/ui/Modal.tsx`
- [x] Create `frontend/src/components/Layout/Sidebar.tsx`
- [x] Create `frontend/src/components/Layout/Header.tsx`

### 4.4 Dashboard Page
- [x] Create `frontend/src/components/Dashboard/StatsOverview.tsx` - Key metrics cards
- [x] Create `frontend/src/components/Dashboard/ProcessingChart.tsx` - Timeline chart (Recharts)
- [x] Create `frontend/src/components/Dashboard/CategoryDistribution.tsx` - Pie/bar chart
- [x] Create `frontend/src/components/Dashboard/RecentDocuments.tsx` - Recent docs table
- [x] Create `frontend/src/components/Dashboard/QueueStatus.tsx` - Processing queue widget

### 4.5 Document Management
- [x] Create `frontend/src/app/documents/page.tsx` - Documents list page
- [x] Create `frontend/src/components/Documents/UploadModal.tsx` - Drag & drop upload
- [x] Document listing with filters and search
- [x] Document actions (view, download, delete)
- [x] Real-time status updates

### 4.6 Search Interface
- [x] Create `frontend/src/app/search/page.tsx` - Search page
- [x] Semantic and hybrid search capabilities
- [x] Advanced filtering by category, date range
- [x] Search results with similarity scores
- [x] Document context and metadata display

### 4.7 Settings Page
- [x] Create `frontend/src/app/settings/page.tsx` - Settings page
- [x] General settings (file size, batch size, formats)
- [x] LLM configuration (provider, model, API key)
- [x] Processing settings (chunk size, overlap, categories)
- [x] Watch folder management with add/remove functionality

### 4.8 Analytics Page
- [x] Create `frontend/src/app/analytics/page.tsx` - Analytics page
- [x] Detailed charts for document trends
- [x] Classification breakdown visualizations
- [x] Processing performance metrics
- [x] System health indicators

---

## Phase 5: Testing & Quality ⏳

### 5.1 Backend Testing
- [ ] Create `tests/conftest.py` - Test fixtures
- [ ] Create `tests/test_api/test_documents.py` - API tests
- [ ] Create `tests/test_services/test_classifier.py` - Classification tests
- [ ] Create `tests/test_services/test_embedder.py` - Embedding tests
- [ ] Create integration test for full pipeline

### 5.2 Frontend Testing
- [ ] Set up Jest and React Testing Library
- [ ] Test critical components
- [ ] Test API integration

### 5.3 Documentation
- [ ] Add API documentation (FastAPI auto-docs already available)
- [ ] Create user guide
- [ ] Document deployment process
- [ ] Add architecture diagrams

---

## Phase 6: Production Readiness ⏳

### 6.1 Security
- [ ] Add authentication (JWT tokens)
- [ ] Add user management
- [ ] Implement role-based access control
- [ ] Add API rate limiting
- [ ] Secure sensitive settings

### 6.2 Performance Optimization
- [ ] Add database indexes
- [ ] Implement caching (Redis)
- [ ] Optimize vector search queries
- [ ] Add pagination for large result sets
- [ ] Implement batch processing

### 6.3 Monitoring & Logging
- [ ] Set up structured logging
- [ ] Add Prometheus metrics
- [ ] Create health check dashboard
- [ ] Implement error tracking (Sentry or similar)

### 6.4 Deployment
- [ ] Create production Docker Compose
- [ ] Add environment-specific configs
- [ ] Set up backup strategies for databases
- [ ] Create deployment documentation
- [ ] Add CI/CD pipeline (GitHub Actions)

---

## Phase 7: Advanced Features ⏳

### 7.1 Enhanced RAG
- [ ] Implement conversation history for RAG queries
- [ ] Add citation/source tracking
- [ ] Implement re-ranking for better results
- [ ] Add query expansion

### 7.2 Document Preview
- [ ] Add PDF preview in frontend
- [ ] Highlight relevant chunks in context
- [ ] Show extracted tables and images

### 7.3 Batch Operations
- [ ] Bulk document upload
- [ ] Batch re-processing
- [ ] Bulk classification updates

### 7.4 Advanced Analytics
- [ ] Document similarity analysis
- [ ] Duplicate detection
- [ ] Trend analysis over time
- [ ] Export analytics reports

---

## Current Progress

**Completed:**
- ✅ Project structure and Docker setup
- ✅ Git repository initialized
- ✅ Configuration files created
- ✅ Development plan documented
- ✅ **Phase 1: Core Backend Infrastructure** - Complete database setup, models, schemas, and basic API structure
- ✅ **Phase 2: Document Processing Pipeline** - Complete end-to-end document processing with Docling, LLM classification, entity extraction, chunking, embeddings, and vector storage
- ✅ **Phase 3: API Endpoints** - Complete REST API with document management, search, analytics, settings, and job management
- ✅ **Phase 4: Frontend Development** - Complete Next.js frontend with dashboard, document management, search interface, settings, and analytics

**Next Up:**
- Phase 5: Testing & Quality - Backend and frontend testing, documentation, and quality assurance

---

## Notes

- Prioritize getting a minimal working pipeline first (end-to-end document processing)
- Focus on petrochemical-specific features (equipment IDs, chemical names, safety classifications)
- Keep Docker-first approach for all development
- Test with real petrochemical documents early to validate classification accuracy
