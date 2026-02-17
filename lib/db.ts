import Database from "better-sqlite3";
import path from "path";
import { DEMO_DISPLAY_NAME, DEMO_EMAIL, DEMO_USER_ID } from "./constants";

const dbPath = process.env.DATABASE_URL?.replace("sqlite:", "")?.replace("file:", "") ||
  path.join(process.cwd(), "data", "waifu_tutor.db");

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    const dir = path.dirname(dbPath);
    const fs = require("fs");
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    db = new Database(dbPath);
    db.pragma("journal_mode = WAL");
    runMigrations(db);
  }
  return db;
}

function runMigrations(database: Database.Database) {
  database.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT,
      display_name TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS subjects (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      name TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(user_id, name)
    );

    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      subject_id TEXT REFERENCES subjects(id),
      title TEXT NOT NULL,
      filename TEXT NOT NULL,
      mime_type TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      status TEXT DEFAULT 'processing',
      word_count INTEGER DEFAULT 0,
      topic_hint TEXT,
      difficulty_estimate TEXT,
      storage_path TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS document_chunks (
      id TEXT PRIMARY KEY,
      doc_id TEXT NOT NULL REFERENCES documents(id),
      chunk_index INTEGER NOT NULL,
      chunk_text TEXT NOT NULL,
      page INTEGER,
      section TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
      chunk_text,
      doc_id UNINDEXED,
      chunk_index UNINDEXED,
      content='document_chunks',
      content_rowid='rowid'
    );

    CREATE TABLE IF NOT EXISTS chunk_embeddings (
      chunk_id TEXT PRIMARY KEY REFERENCES document_chunks(id),
      doc_id TEXT NOT NULL,
      embedding BLOB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS summaries (
      id TEXT PRIMARY KEY,
      doc_id TEXT NOT NULL REFERENCES documents(id),
      detail_level TEXT NOT NULL,
      summary_text TEXT NOT NULL,
      generated_at TEXT DEFAULT (datetime('now')),
      token_usage INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS flashcards (
      id TEXT PRIMARY KEY,
      doc_id TEXT NOT NULL REFERENCES documents(id),
      question TEXT NOT NULL,
      answer TEXT NOT NULL,
      explanation TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      repetitions INTEGER DEFAULT 0,
      interval_days INTEGER DEFAULT 1,
      ease_factor REAL DEFAULT 2.5,
      last_reviewed_at TEXT,
      next_review_at TEXT
    );

    CREATE TABLE IF NOT EXISTS flashcard_reviews (
      id TEXT PRIMARY KEY,
      card_id TEXT NOT NULL REFERENCES flashcards(id),
      quality INTEGER NOT NULL,
      repetitions INTEGER NOT NULL,
      interval_days INTEGER NOT NULL,
      ease_factor REAL NOT NULL,
      user_answer TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS study_progress (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      cards_reviewed_today INTEGER DEFAULT 0,
      total_reviews INTEGER DEFAULT 0,
      average_score REAL DEFAULT 0,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS reminders (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      title TEXT NOT NULL,
      note TEXT,
      scheduled_for TEXT NOT NULL,
      completed INTEGER DEFAULT 0,
      last_notified_at TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ai_usage_logs (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      endpoint TEXT NOT NULL,
      model TEXT NOT NULL,
      prompt_tokens INTEGER DEFAULT 0,
      completion_tokens INTEGER DEFAULT 0,
      latency_ms INTEGER DEFAULT 0,
      raw_response BLOB,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS note_folders (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      name TEXT NOT NULL,
      parent_id TEXT REFERENCES note_folders(id),
      sort_order INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS study_notes (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id),
      folder_id TEXT REFERENCES note_folders(id),
      subject_id TEXT REFERENCES subjects(id),
      doc_id TEXT REFERENCES documents(id),
      title TEXT NOT NULL,
      content TEXT NOT NULL DEFAULT '',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );
  `);

  const triggers = [
    `CREATE TRIGGER IF NOT EXISTS document_chunks_ai AFTER INSERT ON document_chunks BEGIN
      INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
      VALUES (new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
    END`,
    `CREATE TRIGGER IF NOT EXISTS document_chunks_ad AFTER DELETE ON document_chunks BEGIN
      INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
      VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
    END`,
    `CREATE TRIGGER IF NOT EXISTS document_chunks_au AFTER UPDATE ON document_chunks BEGIN
      INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
      VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
      INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
      VALUES(new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
    END`,
  ];
  triggers.forEach((sql) => database.exec(sql));

  // Migration: add subjects table and documents.subject_id if missing
  try {
    database.exec("SELECT 1 FROM subjects LIMIT 1");
  } catch {
    database.exec(`
      CREATE TABLE IF NOT EXISTS subjects (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, name)
      );
    `);
  }
  const docsInfo = database.prepare("PRAGMA table_info(documents)").all() as { name: string }[];
  if (!docsInfo.some((c) => c.name === "subject_id")) {
    database.exec("ALTER TABLE documents ADD COLUMN subject_id TEXT REFERENCES subjects(id)");
  }

  const existingUser = database.prepare("SELECT 1 FROM users WHERE id = ?").get(DEMO_USER_ID);
  if (!existingUser) {
    const uuid = () => require("crypto").randomUUID();
    database.prepare(
      "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)"
    ).run(DEMO_USER_ID, DEMO_EMAIL, DEMO_DISPLAY_NAME);
    database.prepare(
      "INSERT INTO study_progress (id, user_id, cards_reviewed_today, total_reviews, average_score) VALUES (?, ?, 0, 0, 0)"
    ).run(uuid(), DEMO_USER_ID);
  }
}

export { getDb };
