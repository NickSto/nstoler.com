
-- CREATE USER 'tracker' IDENTIFIED BY '[PUT ACTUAL PASSWORD HERE]';
GRANT SELECT ON `traffic`.* TO 'tracker';
GRANT INSERT ON `traffic`.* TO 'tracker';
GRANT DELETE ON `traffic`.* TO 'tracker';
GRANT UPDATE ON `traffic`.* TO 'tracker';
GRANT LOCK TABLES ON `traffic`.* TO 'tracker';
