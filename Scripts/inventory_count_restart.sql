PRAGMA foreign_keys = OFF;
DELETE FROM inventory_count;
DELETE FROM sqlite_sequence WHERE name='inventory_count';
PRAGMA foreign_keys = ON;
VACUUM;