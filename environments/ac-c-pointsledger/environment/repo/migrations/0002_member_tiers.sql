ALTER TABLE members ADD COLUMN tier TEXT NOT NULL DEFAULT 'bronze';

CREATE TABLE tier_history (
    member_id  TEXT NOT NULL REFERENCES members(id),
    tier       TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
