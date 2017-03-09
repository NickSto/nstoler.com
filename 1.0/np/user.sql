
-- CREATE USER 'customizer' IDENTIFIED BY '[PUT AN ACTUAL PASSWORD HERE]';
GRANT SELECT ON `content`.* TO 'customizer';
GRANT INSERT ON `content`.* TO 'customizer';
GRANT DELETE ON `content`.* TO 'customizer';
GRANT UPDATE ON `content`.* TO 'customizer';
GRANT LOCK TABLES ON `content`.* TO 'customizer';
