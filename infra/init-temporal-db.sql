-- Create a separate database for Temporal so it doesn't share the app database
CREATE DATABASE temporal;
GRANT ALL PRIVILEGES ON DATABASE temporal TO thestudio;
