CREATE TABLE IF NOT EXISTS users (
    PRIMARY KEY (user_id),
    user_id    BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS words (
    PRIMARY KEY (word_id),
    UNIQUE(owner_id, english),
    word_id    SERIAL,
    english    VARCHAR(50) NOT NULL,
    russian    VARCHAR(50) NOT NULL,
    owner_id   BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_active_words (
    PRIMARY KEY (user_id, word_id),
    user_id  BIGINT,
             FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    word_id  INT,
             FOREIGN KEY (word_id) REFERENCES words(word_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
