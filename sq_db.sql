CREATE TABLE IF NOT EXISTS object_type(
type VARCHAR(20) PRIMARY KEY CHECK(type != '') NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS object (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name VARCHAR(50) NOT NULL UNIQUE CHECK(name != ''),
type VARCHAR(20) NOT NULL,
parent INTEGER NULL,
time_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

CONSTRAINT not_self_ref
CHECK (parent != id),

CONSTRAINT object_parent_fk
FOREIGN KEY (parent)
REFERENCES object(id)
ON DELETE CASCADE,

CONSTRAINT object_type_type_fk
FOREIGN KEY (type)
REFERENCES object_type(type)
ON DELETE CASCADE
);

INSERT INTO object_type
VALUES
('folder'), ('type1'), ('type2');

INSERT INTO object(name, type, parent)
VALUES
('Folder_1', 'folder', NULL),
('Type1_1', 'type1', 1),
('Type2_1', 'type2', NULL),
('Type1_2', 'type1', 5),
('Folder_2', 'folder', 1),
('Type2_2', 'type2', 5);