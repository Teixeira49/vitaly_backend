-- Supabase Migration: Agregar photo_url a la tabla user
-- Permite almacenar la URL de la foto de perfil del usuario (alojada en ImageKit)

ALTER TABLE public."user" ADD COLUMN IF NOT EXISTS photo_url TEXT DEFAULT NULL;
