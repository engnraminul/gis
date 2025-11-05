-- PostgreSQL database dump for admin-only backup

-- Users table
INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES 
(1, 'pbkdf2_sha256$600000$test$hash', NULL, true, 'admin', '', '', 'admin@test.com', true, true, '2025-01-01 00:00:00+00');

-- Profiles table  
INSERT INTO "Login_profile" (id, user_id, full_name, phone, email, address, profile_picture, user_status) VALUES 
(1, 1, 'Administrator', '123-456-7890', 'admin@test.com', 'Admin Address', '', 'administrator');

-- Backup record
INSERT INTO "Login_backup" (id, name, backup_type, status, file_path, file_size, created_by_id, created_at, completed_at, error_message, description) VALUES 
(1, 'Test_Admin_Only_Backup', 'full', 'completed', 'C:\Users\aminu\Downloads\Compressed\GIS 1 june\myprojectdir\test_backup_admin_only.zip', 1024, 1, '2025-01-01 00:00:00+00', '2025-01-01 00:01:00+00', NULL, 'Test backup containing only admin user');