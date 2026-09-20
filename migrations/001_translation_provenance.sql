BEGIN;

ALTER TABLE public.bible_translations
    ADD COLUMN IF NOT EXISTS coverage_type text NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS book_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS verse_count integer NOT NULL DEFAULT 0;

UPDATE public.bible_translations bt
SET book_count = counts.book_count,
    verse_count = counts.verse_count,
    coverage_type = CASE
        WHEN counts.book_count > 66 THEN 'extended'
        WHEN counts.book_count = 66 THEN 'full'
        ELSE 'partial'
    END
FROM (
    SELECT bb.translation_id,
           count(DISTINCT bb.id)::integer AS book_count,
           count(bv.id)::integer AS verse_count
    FROM public.bible_books bb
    LEFT JOIN public.bible_verses bv ON bv.book_id = bb.id
    GROUP BY bb.translation_id
) counts
WHERE bt.id = counts.translation_id;

COMMIT;
