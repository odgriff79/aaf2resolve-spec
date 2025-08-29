-- Drop tables if they exist (for migration/reset)
DROP TABLE IF EXISTS effect_keyframe;
DROP TABLE IF EXISTS effect_param;
DROP TABLE IF EXISTS effect;
DROP TABLE IF EXISTS event;
DROP TABLE IF EXISTS external_ref;
DROP TABLE IF EXISTS source;
DROP TABLE IF EXISTS timeline;
DROP TABLE IF EXISTS project;

-- Project root table
CREATE TABLE project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rate_num INTEGER NOT NULL,
    rate_den INTEGER NOT NULL
);

-- Timeline per project
CREATE TABLE timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    tc_start INTEGER,
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

-- Source media definitions
CREATE TABLE source (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    name TEXT,
    path TEXT,
    rate_num INTEGER,
    rate_den INTEGER,
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

-- Events (clips/effects) in a timeline
CREATE TABLE event (
    id TEXT PRIMARY KEY,
    timeline_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    start INTEGER,
    duration INTEGER,
    track INTEGER,
    source_id TEXT,
    operation TEXT,
    FOREIGN KEY (timeline_id) REFERENCES timeline(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES source(id)
);

-- Effects attached to events
CREATE TABLE effect (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    type TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES event(id) ON DELETE CASCADE
);

-- Effect parameters (simple key-value)
CREATE TABLE effect_param (
    effect_id TEXT NOT NULL,
    name TEXT,
    value TEXT,
    PRIMARY KEY (effect_id, name),
    FOREIGN KEY (effect_id) REFERENCES effect(id) ON DELETE CASCADE
);

-- Keyframes for effect params (optional)
CREATE TABLE effect_keyframe (
    effect_id TEXT NOT NULL,
    param_name TEXT,
    frame INTEGER,
    value TEXT,
    PRIMARY KEY (effect_id, param_name, frame),
    FOREIGN KEY (effect_id) REFERENCES effect(id) ON DELETE CASCADE
);

-- External references (e.g. linked assets, temp files, or FCPXML refs)
CREATE TABLE external_ref (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    ref_type TEXT,
    ref_value TEXT,
    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
);

-- Indices for lookup
CREATE INDEX idx_project_name ON project(name);
CREATE INDEX idx_timeline_project ON timeline(project_id);
CREATE INDEX idx_event_timeline ON event(timeline_id);
CREATE INDEX idx_event_source ON event(source_id);
CREATE INDEX idx_effect_event ON effect(event_id);
CREATE INDEX idx_extref_project ON external_ref(project_id);
