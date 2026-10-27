-- Run as a MySQL administrator in phpMyAdmin > SQL or the MySQL CLI.
-- Replace CHANGE_ME with a strong local password BEFORE running this script.
-- Use the same password in backend/.env. Do not commit that .env file.
CREATE DATABASE IF NOT EXISTS sentinel_security CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sentinel_user'@'127.0.0.1' IDENTIFIED BY 'CHANGE_ME';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES ON sentinel_security.* TO 'sentinel_user'@'127.0.0.1';
-- Tables are created automatically by FastAPI at startup.
-- If the user already exists, CREATE USER will not change its password.
