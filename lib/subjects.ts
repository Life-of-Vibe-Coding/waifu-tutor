import { getDb } from "./db";
import { DEMO_USER_ID } from "./constants";

export interface Subject {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
}

export function listSubjects(userId: string = DEMO_USER_ID): Subject[] {
  const db = getDb();
  return db.prepare(
    "SELECT id, user_id, name, created_at FROM subjects WHERE user_id = ? ORDER BY name ASC"
  ).all(userId) as Subject[];
}

export function getSubjectById(id: string): Subject | null {
  const db = getDb();
  const row = db.prepare("SELECT id, user_id, name, created_at FROM subjects WHERE id = ?").get(id);
  return (row as Subject) ?? null;
}

export function getSubjectByName(userId: string, name: string): Subject | null {
  const db = getDb();
  const row = db.prepare(
    "SELECT id, user_id, name, created_at FROM subjects WHERE user_id = ? AND name = ?"
  ).get(userId, name.trim());
  return (row as Subject) ?? null;
}

export function createSubject(userId: string, name: string): Subject {
  const db = getDb();
  const { randomUUID } = require("crypto");
  const id = randomUUID();
  const now = new Date().toISOString();
  db.prepare(
    "INSERT INTO subjects (id, user_id, name, created_at) VALUES (?, ?, ?, ?)"
  ).run(id, userId, name.trim(), now);
  return { id, user_id: userId, name: name.trim(), created_at: now };
}

export function createSubjectIfNotExists(userId: string, name: string): Subject {
  const existing = getSubjectByName(userId, name);
  if (existing) return existing;
  return createSubject(userId, name);
}
