
CREATE DATABASE content;
USE content;

CREATE TABLE links (
link_id INT(6) NOT NULL AUTO_INCREMENT,
link VARCHAR(1000) NOT NULL,
linktext VARCHAR(200) NULL,
comment TEXT NULL,
PRIMARY KEY (link_id) );

CREATE TABLE notes (
note_id INT(6) NOT NULL AUTO_INCREMENT,
content TEXT NOT NULL,
PRIMARY KEY (note_id) );

CREATE TABLE notepad (
page VARCHAR(50) NOT NULL,
note_id INT(9) NOT NULL AUTO_INCREMENT,
content TEXT NOT NULL,
PRIMARY KEY (note_id) );


CREATE USER 'customizer' IDENTIFIED BY '[PASSWORD]';
GRANT SELECT ON `content`.* TO 'customizer';
GRANT INSERT ON `content`.* TO 'customizer';
GRANT DELETE ON `content`.* TO 'customizer';
GRANT UPDATE ON `content`.* TO 'customizer';
GRANT LOCK TABLES ON `content`.* TO 'customizer';
