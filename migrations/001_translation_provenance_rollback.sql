BEGIN;

ALTER TABLE public.bible_translations
    DROP COLUMN IF EXISTS coverage_type,
    DROP COLUMN IF EXISTS book_count,
    DROP COLUMN IF EXISTS verse_count;

COMMIT;
