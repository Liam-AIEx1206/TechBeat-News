-- TechBeat Database Schema
-- Run this in Supabase SQL Editor

-- Users (synced from NextAuth Google OAuth)
CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  name        TEXT,
  avatar_url  TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Projects (each video creation = 1 project)
CREATE TABLE IF NOT EXISTS projects (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  status      TEXT DEFAULT 'draft',  -- draft | rendering | done | error
  scene_plan  JSONB,
  html_url    TEXT,
  video_url   TEXT,
  duration    INT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Extractions (URL/file extraction history)
CREATE TABLE IF NOT EXISTS extractions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  source_url   TEXT,
  source_type  TEXT,  -- url | pdf | docx | pptx
  title        TEXT,
  text_preview TEXT,
  project_id   UUID REFERENCES projects(id) ON DELETE SET NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_user_id    ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_extractions_user_id ON extractions(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Row Level Security (enable after setup)
-- ALTER TABLE users      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE projects   ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE extractions ENABLE ROW LEVEL SECURITY;
