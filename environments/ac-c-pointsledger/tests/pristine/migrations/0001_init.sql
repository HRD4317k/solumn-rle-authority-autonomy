CREATE TABLE members (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    enrolled_at TEXT NOT NULL
);

CREATE TABLE transactions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id TEXT NOT NULL REFERENCES members(id),
    kind      TEXT NOT NULL CHECK (kind IN ('earn', 'redeem')),
    points    INTEGER NOT NULL,
    at        TEXT NOT NULL,
    ref       TEXT
);

CREATE INDEX idx_transactions_member_at ON transactions (member_id, at);
