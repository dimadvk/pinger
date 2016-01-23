CREATE TABLE group_list
    (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     group_name TEXT,
     group_comment TEXT);
CREATE TABLE ip_list
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     ip TEXT,
     hostname TEXT,
     group_id INTEGER,
     FOREIGN KEY (group_id) REFERENCES group_list(id));
CREATE TABLE ping_results
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     date_time TEXT,
     ip TEXT,
     sent INTEGER,
     received INTEGER)

