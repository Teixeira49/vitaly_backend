-- Supabase Migration: Add photo_file_id to the user table
-- Stores the ImageKit file id of the current profile photo so the file can be
-- deleted from ImageKit when the photo is replaced or removed. Internal only:
-- it must never be exposed in API responses.

ALTER TABLE public."user" ADD COLUMN IF NOT EXISTS photo_file_id TEXT DEFAULT NULL;
