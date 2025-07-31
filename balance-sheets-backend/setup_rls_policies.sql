-- Row Level Security Policies for User Authentication
-- Run this in Supabase SQL Editor

-- Enable RLS on user-related tables
ALTER TABLE user_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any (for clean setup)
DROP POLICY IF EXISTS "Users can view own matches" ON user_matches;
DROP POLICY IF EXISTS "Users can create own matches" ON user_matches;
DROP POLICY IF EXISTS "Users can view own chat sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users can create own chat sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users can view own chat messages" ON chat_messages;
DROP POLICY IF EXISTS "Users can create own chat messages" ON chat_messages;

-- Policies for user_matches table
CREATE POLICY "Users can view own matches" ON user_matches
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own matches" ON user_matches
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for chat_sessions table
CREATE POLICY "Users can view own chat sessions" ON chat_sessions
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own chat sessions" ON chat_sessions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for chat_messages table
-- Users can view messages from their own chat sessions
CREATE POLICY "Users can view own chat messages" ON chat_messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions
            WHERE chat_sessions.id = chat_messages.session_id
            AND chat_sessions.user_id = auth.uid()
        )
    );

-- Users can create messages in their own chat sessions
CREATE POLICY "Users can create own chat messages" ON chat_messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions
            WHERE chat_sessions.id = chat_messages.session_id
            AND chat_sessions.user_id = auth.uid()
        )
    );

-- Note: These policies ensure that:
-- 1. Users can only see and create their own match records
-- 2. Users can only see and create their own chat sessions
-- 3. Users can only see and create messages within their own chat sessions
-- 4. All operations require authentication (auth.uid() must not be null)