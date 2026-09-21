BEGIN;

-- Literary structure corpus: pericope lists and structural analysis
-- Source: Hajime Murai, Literary Structure of the Bible (CC BY 4.0)
-- http://www.bible.literarystructure.info/bible/bible_e.html

-- Source registry: one row per imported workbook/worksheet provenance
CREATE TABLE IF NOT EXISTS public.literary_structure_sources (
    id              serial PRIMARY KEY,
    source_id       text NOT NULL,           -- stable identifier (e.g. murai_pericope_ot)
    source_type     text NOT NULL,           -- pericope_list | structure
    licence         text NOT NULL DEFAULT 'CC-BY-4.0',
    url             text,
    attribution     text,
    workbook_name   text,                    -- original filename
    workbook_hash   text,                    -- SHA-256 of the .xlsx file
    worksheet_name  text,                    -- sheet tab within the workbook
    version_hint    text,                    -- page update date if known
    imported_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, worksheet_name)
);

-- Structural analysis units: one row per labelled unit in a structure sheet
CREATE TABLE IF NOT EXISTS public.literary_structures (
    id              serial PRIMARY KEY,
    source_id       text NOT NULL,           -- FK to literary_structure_sources.source_id
    book            text NOT NULL,           -- OSIS book code (Gen, Mat, etc.)
    structure_label text,                    -- raw label: [1], A(1:3-5), B1(...), A'
    is_header       boolean NOT NULL DEFAULT false,  -- true for [N] pericope header rows
    parent_label    text,                    -- parent structure label if nested
    unit_sequence   integer,                 -- ordinal within the parent
    depth           integer NOT NULL DEFAULT 0,       -- nesting depth
    raw_reference   text,                    -- unparsed reference string
    start_chapter   integer,                 -- normalised start chapter
    start_verse     integer,                 -- normalised start verse
    start_suffix    text,                    -- partial verse suffix (a/b)
    end_chapter     integer,                 -- normalised end chapter
    end_verse       integer,                 -- normalised end verse
    end_suffix      text,                    -- partial verse suffix (a/b)
    description_ja  text,                    -- Japanese description (col B)
    description_en  text,                    -- English summary / description (col C, may contain <br>)
    transliteration text,                    -- Hebrew/Greek transliteration (col D)
    cross_references text,                   -- raw cross-ref text from NT sheets
    workbook_name   text,
    worksheet_name  text,
    excel_row       integer,                 -- 1-indexed row in source sheet
    UNIQUE (source_id, book, structure_label, excel_row)
);

-- Pericope list entries: one row per pericope in a list sheet
CREATE TABLE IF NOT EXISTS public.literary_pericopes (
    id              serial PRIMARY KEY,
    source_id       text NOT NULL,           -- FK to literary_structure_sources.source_id
    book            text NOT NULL,           -- OSIS book code
    sequence        integer NOT NULL,        -- ordinal from source
    raw_reference   text,                    -- unparsed reference string
    start_chapter   integer,
    start_verse     integer,
    start_suffix    text,
    end_chapter     integer,
    end_verse       integer,
    end_suffix      text,
    title           text,                    -- pericope title / heading
    workbook_name   text,
    worksheet_name  text,
    excel_row       integer,
    UNIQUE (source_id, book, sequence)
);

-- Cross-reference links between literary structures and other passages
CREATE TABLE IF NOT EXISTS public.literary_structure_links (
    id              serial PRIMARY KEY,
    source_id       text NOT NULL,
    structure_id    integer NOT NULL REFERENCES public.literary_structures(id) ON DELETE CASCADE,
    target_passage  text NOT NULL,           -- raw target passage reference
    link_type       text NOT NULL DEFAULT 'cross_reference',
    UNIQUE (source_id, structure_id, target_passage)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lit_struct_sources_source_id
    ON public.literary_structure_sources (source_id);
CREATE INDEX IF NOT EXISTS idx_lit_struct_book_ref
    ON public.literary_structures (book, raw_reference);
CREATE INDEX IF NOT EXISTS idx_lit_struct_source_book
    ON public.literary_structures (source_id, book);
CREATE INDEX IF NOT EXISTS idx_lit_pericope_book_seq
    ON public.literary_pericopes (book, sequence);
CREATE INDEX IF NOT EXISTS idx_lit_pericope_source
    ON public.literary_pericopes (source_id);
CREATE INDEX IF NOT EXISTS idx_lit_struct_links_structure
    ON public.literary_structure_links (structure_id);
CREATE INDEX IF NOT EXISTS idx_lit_struct_links_target
    ON public.literary_structure_links (target_passage);

-- Grants for the runtime role
GRANT USAGE, SELECT, UPDATE ON SEQUENCE
    public.literary_structure_sources_id_seq,
    public.literary_structures_id_seq,
    public.literary_pericopes_id_seq,
    public.literary_structure_links_id_seq TO theosis;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    public.literary_structure_sources,
    public.literary_structures,
    public.literary_pericopes,
    public.literary_structure_links TO theosis;

COMMIT;
