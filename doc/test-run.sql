-- 既存のテーブルがあれば削除（テスト環境のリセット用）
DROP TABLE IF EXISTS Users;

-- Users テーブルの作成
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 単発参照を高速化するためのインデックス作成
-- (emailやroleでの検索を想定)
CREATE INDEX IF NOT EXISTS idx_users_email ON Users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON Users(role);

-- テスト用の初期データ挿入
INSERT INTO Users (name, email, role) VALUES
('Alice', 'alice@example.com', 'admin'),
('Bob', 'bob@example.com', 'user'),
('Charlie', 'charlie@example.com', 'user');
