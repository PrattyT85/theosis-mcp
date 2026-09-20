BEGIN;

UPDATE public.bible_translations
SET source_url = 'https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/' || abbreviation || '.csv'
WHERE source_url IS NULL OR source_url = '';

COMMIT;
