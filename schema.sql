CREATE TABLE group_list
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     group_name text,
     group_comment text);
CREATE TABLE ip_list
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     ip text,
     hostname text,
     group_id integer,
     FOREIGN KEY (group_id) REFERENCES group_list(id));
CREATE TABLE ping_results
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     date_time text,
     ip text,
     sent text,
     received text)

