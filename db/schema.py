# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

import duckdb

TABLE_NAMES = {
    "jobs",
    "results_cache",
    "file_chunks",
    "analysis_history",
    "repo_metadata",
    "commit_snapshots",
    "prompt_presets",
    "sidebar_profiles",
    "job_events",
}

_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS jobs (
        id           VARCHAR PRIMARY KEY,
        status       VARCHAR NOT NULL DEFAULT 'pending',
        source_type  VARCHAR NOT NULL,
        source_ref   VARCHAR NOT NULL,
        language     VARCHAR,
        features     VARCHAR[],
        custom_prompt TEXT,
        result_json  JSON,
        created_at   TIMESTAMP DEFAULT now(),
        completed_at TIMESTAMP
    )""",
    # Migration: add result_json to existing databases that predate this column
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS result_json JSON",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS template_category VARCHAR",
    """CREATE TABLE IF NOT EXISTS results_cache (
        id           VARCHAR PRIMARY KEY,
        job_id       VARCHAR NOT NULL,
        feature      VARCHAR NOT NULL,
        file_hash    VARCHAR NOT NULL,
        language     VARCHAR,
        result_json  JSON,
        created_at   TIMESTAMP DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS file_chunks (
        id           VARCHAR PRIMARY KEY,
        job_id       VARCHAR NOT NULL,
        file_path    VARCHAR NOT NULL,
        chunk_index  INTEGER NOT NULL,
        start_line   INTEGER,
        end_line     INTEGER,
        content      TEXT,
        token_count  INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS analysis_history (
        id           VARCHAR PRIMARY KEY,
        job_id       VARCHAR NOT NULL,
        feature      VARCHAR NOT NULL,
        source_ref   VARCHAR,
        language     VARCHAR,
        summary      TEXT,
        created_at   TIMESTAMP DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS repo_metadata (
        id           VARCHAR PRIMARY KEY,
        source_type  VARCHAR NOT NULL,
        repo_url     VARCHAR NOT NULL,
        branch       VARCHAR,
        last_synced  TIMESTAMP,
        commit_count INTEGER,
        file_tree    JSON
    )""",
    """CREATE TABLE IF NOT EXISTS commit_snapshots (
        id            VARCHAR PRIMARY KEY,
        repo_id       VARCHAR NOT NULL,
        commit_sha    VARCHAR NOT NULL,
        author        VARCHAR,
        message       TEXT,
        diff_summary  TEXT,
        files_changed VARCHAR[],
        created_at    TIMESTAMP DEFAULT now(),
        UNIQUE (repo_id, commit_sha)
    )""",
    """CREATE TABLE IF NOT EXISTS prompt_presets (
        id                 VARCHAR PRIMARY KEY,
        name               VARCHAR NOT NULL,
        feature            VARCHAR NOT NULL,
        system_prompt      TEXT,
        extra_instructions TEXT,
        created_at         TIMESTAMP DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS sidebar_profiles (
        id                 VARCHAR PRIMARY KEY,
        name               VARCHAR NOT NULL UNIQUE,
        source_type        VARCHAR,
        features           VARCHAR[],
        language           VARCHAR,
        custom_prompt      TEXT,
        extra_instructions TEXT,
        mermaid_type       VARCHAR DEFAULT 'flowchart',
        created_at         TIMESTAMP DEFAULT now(),
        updated_at         TIMESTAMP DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS job_events (
        id          VARCHAR PRIMARY KEY,
        job_id      VARCHAR NOT NULL,
        event_type  VARCHAR NOT NULL,
        agent       VARCHAR,
        file_path   VARCHAR,
        message     VARCHAR,
        created_at  TIMESTAMP DEFAULT now()
    )""",
]


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    for stmt in _STATEMENTS:
        conn.execute(stmt)
