# Waifu Tutor - Project Architecture

## System Overview
An interactive learning companion featuring an animated character that helps students study through document analysis, summarization, flashcards, and voice interactions.

---

## Architecture Layers

### 1. Frontend Layer (React)

#### Core Components

**Live2D Character System**
- Character renderer with emotional states (happy, encouraging, sad, neutral, excited)
- Animation triggers based on user interactions and quiz results
- Position management (sidebar/floating beside chatbox)
- Emotion state machine tied to app events

**Main Interface Modules**
- Chat interface with message history
- Document upload zone with drag-and-drop
- Flashcard study interface
- Summary display panel
- Reminder/schedule manager UI

**State Management**
- Redux/Zustand for global state (user progress, active document, character mood)
- Local state for UI interactions
- WebSocket connection state for real-time updates

**Audio System**
- Text-to-Speech integration (Web Speech API or ElevenLabs/similar)
- Voice playback controls
- Character voice personality configuration

#### Key Features Implementation

**Document Upload Flow**
```
User uploads → Preview → Processing indicator → Success notification with character reaction
```

**Summary Generation**
- Request summary from backend
- Display with voice playback option
- Character reads aloud with synchronized animations

**Flashcard System**
- Card flip animations
- Progress tracking
- Character reactions:
  - Correct: Celebration animation + encouraging voice line
  - Incorrect: Disappointed animation + supportive voice line
- Spaced repetition UI indicators

**Reminder System**
- Calendar/schedule view
- Notification permissions request
- Local notification triggers
- Integration with browser notification API

---

### 2. Backend Layer (Python/FastAPI)

#### API Structure

**Core Endpoints**

```
Authentication & User Management
POST   /api/auth/register
POST   /api/auth/login
GET    /api/user/profile

Document Management
POST   /api/documents/upload
GET    /api/documents/{doc_id}
DELETE /api/documents/{doc_id}
GET    /api/documents/list

AI Processing
POST   /api/ai/summarize
POST   /api/ai/generate-flashcards
POST   /api/ai/chat
POST   /api/ai/quiz-feedback

Study Tools
GET    /api/flashcards/{doc_id}
POST   /api/flashcards/{card_id}/review
GET    /api/study/progress

Reminders
POST   /api/reminders/create
GET    /api/reminders/list
PUT    /api/reminders/{reminder_id}
DELETE /api/reminders/{reminder_id}
```

#### Service Layer Architecture

**DocumentService**
- Parse uploaded documents (PDF, DOCX, TXT, MD)
- Extract and clean text content
- Chunk documents for vector storage
- Generate metadata (word count, topics, difficulty estimate)

**AIService**
- Gemini 2.5 Flash integration
- Prompt templates for different tasks:
  - Summarization (adjustable detail levels)
  - Flashcard generation (Q&A pairs with explanations)
  - Quiz evaluation with encouraging/constructive feedback
  - Chat responses in character personality
- Response streaming for chat
- Token usage tracking

**VectorService (Qdrant)**
- Document embedding generation
- Semantic search for relevant content
- Context retrieval for RAG-enhanced responses
- Collection management per user/course

**SearchService (BM25 + SQLite)**
- Keyword-based search implementation
- Hybrid search combining vector + keyword results
- Full-text search index maintenance

**ReminderService**
- Scheduled task management
- Notification queue
- Webhook/email integration for reminders

#### Data Processing Pipeline

```
Document Upload → Text Extraction → Chunking → 
  ↓
Parallel Processing:
  ├─ Embedding Generation → Qdrant Storage
  ├─ Keyword Indexing → SQLite FTS
  └─ AI Summary Generation → Cache in SQLite
```

---

### 3. Database Layer

#### Qdrant (Vector Database)

**Collections Structure**
```
Collection: user_{user_id}_documents
- Vectors: Document embeddings (1536 dimensions for text-embedding-004)
- Payload: {
    doc_id, chunk_text, chunk_index,
    metadata: {title, page, section, timestamp}
  }
```

**Operations**
- Semantic search with filtering
- Similarity threshold tuning
- Periodic re-indexing for updated documents

#### SQLite (Relational + FTS)

**Purpose & Responsibilities**
- User authentication and profile data
- Document metadata and file references
- Cached AI-generated summaries
- Flashcard content and review scheduling
- Reminder schedules and completion status
- Full-text search index (BM25) for keyword queries

**Key Design Considerations**
- Relational integrity between users, documents, and study materials
- Full-text search virtual tables for content indexing
- Spaced repetition algorithm data (ease factors, intervals, next review dates)
- Efficient indexing for common query patterns
- Migration path to PostgreSQL if needed for scale

---

### 4. Integration Layer

#### External Services

**Gemini 2.5 Flash API**
- API key management via environment variables
- Rate limiting and retry logic
- Prompt engineering templates stored in config
- Response caching for identical queries

**Text-to-Speech**
- Option 1: Browser Web Speech API (free, limited voices)
- Option 2: ElevenLabs/Google Cloud TTS (premium, character voice cloning)
- Audio file caching for repeated phrases

**File Storage**
- Local filesystem for development
- S3/Cloud Storage for production
- Signed URLs for secure document access

---

## Technical Implementation Details

### Frontend Stack
```
- React 18+ with TypeScript
- Live2D Cubism SDK for Web
- TailwindCSS for styling
- Axios for API calls
- React Query for server state
- Zustand for client state
- React Router for navigation
- Framer Motion for UI animations
```

### Backend Stack
```
- FastAPI (Python 3.11+)
- Pydantic for data validation
- SQLAlchemy for SQLite ORM
- Qdrant Client SDK
- Google Generative AI SDK (Gemini)
- python-docx, PyPDF2 for document parsing
- APScheduler for reminder scheduling
- JWT for authentication
- CORS middleware
```

### Deployment Architecture

**Development**
```
Frontend: Vite dev server (localhost:5173)
Backend: Uvicorn (localhost:8000)
Qdrant: Docker container (localhost:6333)
SQLite: Local file
```

**Production**
```
Frontend: Vercel/Netlify CDN
Backend: Railway/Fly.io/AWS EC2
Qdrant: Qdrant Cloud or self-hosted
SQLite: Attached volume or migrate to PostgreSQL
```

---

## Data Flow Examples

### Study Session Flow
```
1. User selects document
2. Frontend fetches flashcards from API
3. Character presents question with curious animation
4. User submits answer
5. Backend evaluates via Gemini + semantic similarity
6. Character reacts (happy/sad animation + voice)
7. Spaced repetition algorithm updates next review date
8. Progress saved to database
```

### Document Q&A Flow
```
1. User asks question in chat
2. Frontend sends to AI chat endpoint with context
3. Backend performs hybrid search:
   - BM25 keyword search in SQLite FTS
   - Semantic search in Qdrant
4. Top K results combined and ranked
5. Context + question sent to Gemini
6. Streaming response returned
7. Character animates while "thinking"
8. TTS reads response aloud if requested
```

---

## Security Considerations

- JWT-based authentication with refresh tokens
- Rate limiting on AI endpoints (per user/IP)
- File upload validation (size, type, malware scanning)
- SQL injection prevention via parameterized queries
- API key encryption in environment variables
- CORS configuration for frontend domain only
- User data isolation (documents, progress, reminders)

---

## Scalability Considerations

- Horizontal scaling: Stateless backend allows load balancing
- Caching layer: Redis for session storage and frequent queries
- Async task queue: Celery for document processing
- CDN for static assets and Live2D models
- Database migration path: SQLite → PostgreSQL for concurrent writes
- Vector database sharding by user cohorts

---

## Future Enhancements

- Multi-language support with i18n
- Multiple character personalities/models
- Collaborative study rooms
- Gamification (XP, achievements, leaderboards)
- Mobile app (React Native)
- Voice input for hands-free studying
- Integration with learning management systems (Canvas, Moodle)
- Advanced analytics dashboard for study patterns
