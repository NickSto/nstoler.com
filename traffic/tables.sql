
CREATE DATABASE traffic;
USE traffic;

CREATE TABLE visits (
visit_id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
visitor_id INT(10) UNSIGNED NULL,
unix_time INT(10) UNSIGNED NOT NULL,
date DATE NULL,
time TIME NULL,
page VARCHAR(1000) NULL,
referrer VARCHAR(1000) NULL,
PRIMARY KEY (visit_id) );

CREATE TABLE visitors (
visitor_id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
ip CHAR(15) NOT NULL,
user_agent VARCHAR(500) NULL,
visits INT(9) NULL,
is_me CHAR(0) NULL,
label VARCHAR(200) NULL,
screen_res CHAR(11) NULL,
os VARCHAR(50) NULL,
browser VARCHAR(35) NULL,
location VARCHAR(200) NULL,
isp VARCHAR(200) NULL,
PRIMARY KEY (visitor_id) );
ALTER TABLE visitors ADD cookie CHAR(16) NULL AFTER visitor_id;


CREATE USER 'tracker' IDENTIFIED BY '[PASSWORD]';
GRANT SELECT ON `traffic`.* TO 'tracker';
GRANT INSERT ON `traffic`.* TO 'tracker';
GRANT DELETE ON `traffic`.* TO 'tracker';
GRANT UPDATE ON `traffic`.* TO 'tracker';
GRANT LOCK TABLES ON `traffic`.* TO 'tracker';
