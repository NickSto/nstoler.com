CREATE TABLE sequences (
identifier VARCHAR(60) NOT NULL,
db_name CHAR(5) NOT NULL,
db_id CHAR(15) NOT NULL,
description VARCHAR(1000) NULL,
length INT(7) NULL,
PRIMARY KEY (identifier),
KEY db_name_id (db_name, db_id) );

CREATE TABLE hits (
query_id VARCHAR(60) NOT NULL,
subject_id VARCHAR(60) NOT NULL,
identity DECIMAL(5,2) NULL,
align_length INT(6) NULL,
mismatches INT(5) NULL,
gap_openings INT(4) NULL,
query_start INT(6) NULL,
query_end INT(6) NULL,
subj_start INT(6) NULL,
subj_end INT(6) NULL,
e_value DOUBLE UNSIGNED NULL,
bit_score DECIMAL(5,1) NULL );