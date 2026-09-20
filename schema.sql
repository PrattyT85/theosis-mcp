--
-- PostgreSQL database dump
--

\restrict IPGmSoL2crlthvGR1pipgt0N5qbnoLEuQ3cEhJxJFjYF4XWLhDKKCwWeCBUQ6B9

-- Dumped from database version 16.14 (Ubuntu 16.14-1.pgdg24.04+1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-1.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: kvj_import; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA kvj_import;


--
-- Name: dblink; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS dblink WITH SCHEMA public;


--
-- Name: EXTENSION dblink; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION dblink IS 'connect to other PostgreSQL databases from within a database';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: KJV_books; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."KJV_books" (
    id integer NOT NULL,
    name character varying(255)
);


--
-- Name: KJV_books_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public."KJV_books_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: KJV_books_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public."KJV_books_id_seq" OWNED BY public."KJV_books".id;


--
-- Name: KJV_verses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."KJV_verses" (
    id integer NOT NULL,
    book_id integer,
    chapter integer,
    verse integer,
    text text
);


--
-- Name: KJV_verses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public."KJV_verses_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: KJV_verses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public."KJV_verses_id_seq" OWNED BY public."KJV_verses".id;


--
-- Name: acai_entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acai_entities (
    id text,
    entity_type text NOT NULL,
    name text NOT NULL,
    gender text,
    description text,
    roles text,
    father_id text,
    mother_id text,
    partners text,
    offspring text,
    siblings text,
    referred_to_as text,
    key_references text,
    reference_count integer,
    speeches_count integer
);


--
-- Name: ane_book_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ane_book_mappings (
    entry_id text NOT NULL,
    book text NOT NULL,
    chapter_start integer,
    chapter_end integer
);


--
-- Name: ane_context; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ane_context (
    id integer NOT NULL,
    period character varying(100),
    dimension character varying(100),
    topic character varying(300),
    content text NOT NULL,
    embedding public.vector(768)
);


--
-- Name: ane_context_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ane_context_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ane_context_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ane_context_id_seq OWNED BY public.ane_context.id;


--
-- Name: ane_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ane_entries (
    id text,
    dimension text NOT NULL,
    dimension_label text NOT NULL,
    title text NOT NULL,
    summary text NOT NULL,
    detail text,
    ane_parallels text,
    interpretive_significance text,
    period text,
    period_label text,
    key_references text,
    scholarly_sources text
);


--
-- Name: aquifer_content; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aquifer_content (
    id integer NOT NULL,
    content_id text NOT NULL,
    resource_type text NOT NULL,
    title text NOT NULL,
    book text,
    book_num integer,
    start_ref text,
    end_ref text,
    chapter_start integer,
    verse_start integer,
    chapter_end integer,
    verse_end integer,
    content text NOT NULL,
    content_plain text NOT NULL,
    is_range integer DEFAULT 0
);


--
-- Name: aquifer_content_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.aquifer_content_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aquifer_content_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.aquifer_content_id_seq OWNED BY public.aquifer_content.id;


--
-- Name: bible_books; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bible_books (
    id integer NOT NULL,
    translation_id integer,
    name text,
    testament text,
    book_number integer,
    osis_ref text
);


--
-- Name: bible_books_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bible_books_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bible_books_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bible_books_id_seq OWNED BY public.bible_books.id;


--
-- Name: bible_cross_references; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bible_cross_references (
    id integer NOT NULL,
    from_book_id integer,
    from_chapter integer,
    from_verse integer,
    to_book_id integer,
    to_chapter integer,
    to_verse integer,
    source text,
    votes integer
);


--
-- Name: bible_cross_references_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bible_cross_references_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bible_cross_references_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bible_cross_references_id_seq OWNED BY public.bible_cross_references.id;


--
-- Name: bible_extra_biblical; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bible_extra_biblical (
    id integer NOT NULL,
    category text,
    title text,
    author text,
    section text,
    subsection text,
    text text
);


--
-- Name: bible_extra_biblical_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bible_extra_biblical_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bible_extra_biblical_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bible_extra_biblical_id_seq OWNED BY public.bible_extra_biblical.id;


--
-- Name: bible_translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bible_translations (
    id integer NOT NULL,
    abbreviation text,
    name text,
    language text,
    year integer,
    license text,
    description text,
    source_url text
);


--
-- Name: bible_translations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bible_translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bible_translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bible_translations_id_seq OWNED BY public.bible_translations.id;


--
-- Name: bible_verses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bible_verses (
    id integer NOT NULL,
    book_id integer,
    chapter integer,
    verse integer,
    text text
);


--
-- Name: bible_verses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bible_verses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bible_verses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bible_verses_id_seq OWNED BY public.bible_verses.id;


--
-- Name: books; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.books (
    id integer NOT NULL,
    translation_id integer,
    name character varying(100) NOT NULL,
    testament character varying(20),
    book_number integer,
    osis_ref character varying(20),
    chapters integer,
    CONSTRAINT books_testament_check CHECK (((testament)::text = ANY ((ARRAY['OT'::character varying, 'NT'::character varying, 'APO'::character varying])::text[])))
);


--
-- Name: books_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.books_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: books_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.books_id_seq OWNED BY public.books.id;


--
-- Name: commentaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.commentaries (
    id integer NOT NULL,
    book_osis character varying(10) NOT NULL,
    chapter integer NOT NULL,
    verse_start integer NOT NULL,
    verse_end integer,
    author character varying(300) NOT NULL,
    author_year integer,
    author_category text,
    source_title text,
    source_url text,
    quote text NOT NULL,
    language text DEFAULT 'en'::text
);


--
-- Name: commentaries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.commentaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: commentaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.commentaries_id_seq OWNED BY public.commentaries.id;


--
-- Name: extra_biblical_texts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extra_biblical_texts (
    id integer NOT NULL,
    category character varying(100),
    title character varying(300) NOT NULL,
    author character varying(200),
    section character varying(200),
    subsection character varying(200),
    text text NOT NULL,
    embedding public.vector(768),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT extra_biblical_texts_category_check CHECK (((category)::text = ANY ((ARRAY['deuterocanonical'::character varying, 'apocrypha'::character varying, 'pseudepigrapha'::character varying, 'church_fathers'::character varying, 'ante_nicene'::character varying, 'nicene1'::character varying, 'nicene2'::character varying])::text[])))
);


--
-- Name: extra_biblical_texts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extra_biblical_texts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extra_biblical_texts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extra_biblical_texts_id_seq OWNED BY public.extra_biblical_texts.id;


--
-- Name: graph_event_place_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_event_place_edges (
    event_id text NOT NULL,
    place_id text NOT NULL
);


--
-- Name: graph_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_events (
    id text,
    title text NOT NULL,
    start_year integer,
    duration text,
    sort_key real
);


--
-- Name: graph_family_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_family_edges (
    from_person_id text NOT NULL,
    to_person_id text NOT NULL,
    relationship_type text NOT NULL
);


--
-- Name: graph_people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_people (
    id text,
    name text NOT NULL,
    also_called text,
    gender text,
    birth_year integer,
    death_year integer,
    birth_place_id text,
    death_place_id text,
    description text
);


--
-- Name: graph_people_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_people_groups (
    name text,
    members text
);


--
-- Name: graph_person_event_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_person_event_edges (
    person_id text NOT NULL,
    event_id text NOT NULL
);


--
-- Name: graph_person_group_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_person_group_edges (
    person_id text NOT NULL,
    group_name text NOT NULL
);


--
-- Name: graph_places; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_places (
    id text,
    name text NOT NULL,
    latitude real,
    longitude real,
    feature_type text
);


--
-- Name: graph_verse_mentions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_verse_mentions (
    verse_ref text NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL
);


--
-- Name: hlt_annotations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hlt_annotations (
    id integer,
    reference text NOT NULL,
    annotation_type text NOT NULL,
    annotation_text text NOT NULL,
    word_position integer,
    explanation text NOT NULL,
    heiser_content_id integer
);


--
-- Name: hlt_study_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hlt_study_notes (
    id integer,
    reference text NOT NULL,
    book text NOT NULL,
    chapter integer,
    verse integer,
    note_type text NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    heiser_content_ids text,
    related_verses text,
    priority integer DEFAULT 5
);


--
-- Name: lexicon; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lexicon (
    id integer,
    strongs text NOT NULL,
    language text NOT NULL,
    word text,
    transliteration text,
    pronunciation text,
    short_definition text,
    full_definition text,
    etymology text,
    usage_count integer DEFAULT 0,
    semantic_domain text,
    related_words text,
    abbott_smith_def text,
    nt_occurrences integer,
    lxx_hebrew text,
    synonyms text,
    sense_hierarchy text
);


--
-- Name: manuscript_witnesses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.manuscript_witnesses (
    id integer,
    variant_id integer NOT NULL,
    manuscript text NOT NULL,
    manuscript_date text,
    reading_support text
);


--
-- Name: morphology; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.morphology (
    id integer,
    code text NOT NULL,
    language text NOT NULL,
    parsing text,
    part_of_speech text,
    person text,
    number text,
    tense text,
    voice text,
    mood text,
    case_value text,
    gender text
);


--
-- Name: names_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.names_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: names; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.names (
    id integer DEFAULT nextval('public.names_id_seq'::regclass),
    name text NOT NULL,
    name_original text,
    type text,
    description text,
    refs text,
    relationships text
);


--
-- Name: nt_ot_lxx_quote_hints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nt_ot_lxx_quote_hints (
    id integer,
    nt_reference text NOT NULL,
    nt_display text NOT NULL,
    nt_book text NOT NULL,
    ot_reference text NOT NULL,
    ot_display text NOT NULL,
    ot_book text NOT NULL,
    follows_lxx integer DEFAULT 1 NOT NULL,
    divergence_type text,
    divergence_note text,
    textual_variant_id integer
);


--
-- Name: passages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passages (
    id integer,
    reference_start text NOT NULL,
    reference_end text NOT NULL,
    book text NOT NULL,
    start_verse_id integer NOT NULL,
    end_verse_id integer NOT NULL,
    text_combined text NOT NULL,
    verse_count integer NOT NULL,
    section_type text
);


--
-- Name: strongs_lexicon; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.strongs_lexicon (
    id integer NOT NULL,
    strongs_id character varying(50) NOT NULL,
    language character varying(10),
    lemma character varying(200),
    transliteration character varying(200),
    gloss text,
    full_definition text,
    morphology_code character varying(50),
    CONSTRAINT strongs_lexicon_language_check CHECK (((language)::text = ANY ((ARRAY['greek'::character varying, 'hebrew'::character varying])::text[])))
);


--
-- Name: strongs_lexicon_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.strongs_lexicon_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: strongs_lexicon_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.strongs_lexicon_id_seq OWNED BY public.strongs_lexicon.id;


--
-- Name: strongs_verse_map; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.strongs_verse_map (
    id integer NOT NULL,
    verse_id integer,
    strongs_id character varying(50),
    "position" integer,
    morphological_tag character varying(100)
);


--
-- Name: strongs_verse_map_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.strongs_verse_map_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: strongs_verse_map_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.strongs_verse_map_id_seq OWNED BY public.strongs_verse_map.id;


--
-- Name: textual_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.textual_variants (
    id integer,
    reference text NOT NULL,
    book text NOT NULL,
    chapter integer,
    verse integer,
    mt_reading text NOT NULL,
    mt_hebrew text,
    variant_source text NOT NULL,
    variant_reading text NOT NULL,
    variant_original text,
    variant_significance text,
    heiser_analysis text,
    heiser_content_id integer,
    scholarly_consensus text,
    preferred_for_hlt text,
    hlt_rationale text
);


--
-- Name: thematic_references; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.thematic_references (
    id integer,
    theme text NOT NULL,
    reference text NOT NULL,
    note text
);


--
-- Name: theographic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theographic (
    id integer NOT NULL,
    entity_id character varying(100),
    entity_type character varying(20),
    name character varying(200) NOT NULL,
    alternate_names jsonb DEFAULT '[]'::jsonb,
    description text,
    family_connections jsonb DEFAULT '{}'::jsonb,
    embedding public.vector(768),
    CONSTRAINT theographic_entity_type_check CHECK (((entity_type)::text = ANY ((ARRAY['person'::character varying, 'place'::character varying, 'event'::character varying])::text[])))
);


--
-- Name: theographic_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.theographic_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: theographic_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.theographic_id_seq OWNED BY public.theographic.id;


--
-- Name: theographic_relations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theographic_relations (
    id integer NOT NULL,
    person_name text NOT NULL,
    relation_type text NOT NULL,
    related_name text NOT NULL,
    relationship text
);


--
-- Name: theographic_relations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.theographic_relations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: theographic_relations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.theographic_relations_id_seq OWNED BY public.theographic_relations.id;


--
-- Name: theological_themes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theological_themes (
    id integer NOT NULL,
    theme_slug character varying(100),
    theme_name character varying(300),
    description text,
    related_verses jsonb DEFAULT '[]'::jsonb,
    reference character varying(50)
);


--
-- Name: theological_themes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.theological_themes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: theological_themes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.theological_themes_id_seq OWNED BY public.theological_themes.id;


--
-- Name: theological_works; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theological_works (
    id integer NOT NULL,
    work_title text NOT NULL,
    author text,
    volume text,
    part text,
    chapter text,
    section text,
    text text NOT NULL,
    source_url text
);


--
-- Name: theological_works_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.theological_works_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: theological_works_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.theological_works_id_seq OWNED BY public.theological_works.id;


--
-- Name: theology_content; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theology_content (
    id integer,
    source_work text NOT NULL,
    source_author text NOT NULL,
    source_type text NOT NULL,
    chapter_or_episode text,
    title text,
    content_summary text NOT NULL,
    content_detail text,
    page_range text,
    url text
);


--
-- Name: theology_theme_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theology_theme_index (
    id integer,
    theme_key text NOT NULL,
    content_id integer,
    reference text
);


--
-- Name: theology_themes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theology_themes (
    id integer,
    theme_key text NOT NULL,
    theme_label text NOT NULL,
    description text NOT NULL,
    parent_theme text,
    key_works text
);


--
-- Name: torah_weave_cells; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.torah_weave_cells (
    id integer,
    unit_id integer NOT NULL,
    cell_label text NOT NULL,
    row_num integer NOT NULL,
    column_letter text NOT NULL,
    subdivision text,
    book text NOT NULL,
    verse_range text NOT NULL,
    chapter_start integer NOT NULL,
    verse_start integer NOT NULL,
    chapter_end integer NOT NULL,
    verse_end integer NOT NULL,
    sort_start integer NOT NULL,
    sort_end integer NOT NULL
);


--
-- Name: torah_weave_cells_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.torah_weave_cells_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: torah_weave_cells_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.torah_weave_cells_id_seq OWNED BY public.torah_weave_cells.id;


--
-- Name: torah_weave_units; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.torah_weave_units (
    id integer,
    book text NOT NULL,
    book_full text NOT NULL,
    unit_number integer NOT NULL,
    title text NOT NULL,
    verses text NOT NULL,
    verse_range text NOT NULL,
    format text NOT NULL,
    irregular integer NOT NULL,
    is_unique integer NOT NULL,
    cell_count integer NOT NULL,
    type text,
    cell_count_with_subdivisions integer
);


--
-- Name: torah_weave_units_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.torah_weave_units_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: torah_weave_units_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.torah_weave_units_id_seq OWNED BY public.torah_weave_units.id;


--
-- Name: translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.translations (
    id integer NOT NULL,
    abbreviation character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    language character varying(50) DEFAULT 'english'::character varying,
    year integer,
    license character varying(100),
    description text,
    source_url text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: translations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.translations_id_seq OWNED BY public.translations.id;


--
-- Name: verse_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verse_embeddings (
    id integer NOT NULL,
    book text NOT NULL,
    chapter integer NOT NULL,
    verse integer NOT NULL,
    verse_id integer,
    embedding public.vector(384)
);


--
-- Name: verse_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.verse_embeddings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: verse_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.verse_embeddings_id_seq OWNED BY public.verse_embeddings.id;


--
-- Name: verses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verses (
    id integer NOT NULL,
    reference text NOT NULL,
    book text,
    chapter integer,
    verse integer,
    text_english text,
    text_original text,
    word_data text,
    section_end text,
    kjv_text text
);


--
-- Name: KJV_books id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."KJV_books" ALTER COLUMN id SET DEFAULT nextval('public."KJV_books_id_seq"'::regclass);


--
-- Name: KJV_verses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."KJV_verses" ALTER COLUMN id SET DEFAULT nextval('public."KJV_verses_id_seq"'::regclass);


--
-- Name: ane_context id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ane_context ALTER COLUMN id SET DEFAULT nextval('public.ane_context_id_seq'::regclass);


--
-- Name: aquifer_content id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aquifer_content ALTER COLUMN id SET DEFAULT nextval('public.aquifer_content_id_seq'::regclass);


--
-- Name: bible_books id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_books ALTER COLUMN id SET DEFAULT nextval('public.bible_books_id_seq'::regclass);


--
-- Name: bible_cross_references id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_cross_references ALTER COLUMN id SET DEFAULT nextval('public.bible_cross_references_id_seq'::regclass);


--
-- Name: bible_extra_biblical id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_extra_biblical ALTER COLUMN id SET DEFAULT nextval('public.bible_extra_biblical_id_seq'::regclass);


--
-- Name: bible_translations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_translations ALTER COLUMN id SET DEFAULT nextval('public.bible_translations_id_seq'::regclass);


--
-- Name: bible_verses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_verses ALTER COLUMN id SET DEFAULT nextval('public.bible_verses_id_seq'::regclass);


--
-- Name: books id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.books ALTER COLUMN id SET DEFAULT nextval('public.books_id_seq'::regclass);


--
-- Name: commentaries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commentaries ALTER COLUMN id SET DEFAULT nextval('public.commentaries_id_seq'::regclass);


--
-- Name: extra_biblical_texts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_biblical_texts ALTER COLUMN id SET DEFAULT nextval('public.extra_biblical_texts_id_seq'::regclass);


--
-- Name: strongs_lexicon id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_lexicon ALTER COLUMN id SET DEFAULT nextval('public.strongs_lexicon_id_seq'::regclass);


--
-- Name: strongs_verse_map id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_verse_map ALTER COLUMN id SET DEFAULT nextval('public.strongs_verse_map_id_seq'::regclass);


--
-- Name: theographic id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theographic ALTER COLUMN id SET DEFAULT nextval('public.theographic_id_seq'::regclass);


--
-- Name: theographic_relations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theographic_relations ALTER COLUMN id SET DEFAULT nextval('public.theographic_relations_id_seq'::regclass);


--
-- Name: theological_themes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theological_themes ALTER COLUMN id SET DEFAULT nextval('public.theological_themes_id_seq'::regclass);


--
-- Name: theological_works id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theological_works ALTER COLUMN id SET DEFAULT nextval('public.theological_works_id_seq'::regclass);


--
-- Name: torah_weave_cells id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.torah_weave_cells ALTER COLUMN id SET DEFAULT nextval('public.torah_weave_cells_id_seq'::regclass);


--
-- Name: torah_weave_units id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.torah_weave_units ALTER COLUMN id SET DEFAULT nextval('public.torah_weave_units_id_seq'::regclass);


--
-- Name: translations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.translations ALTER COLUMN id SET DEFAULT nextval('public.translations_id_seq'::regclass);


--
-- Name: verse_embeddings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verse_embeddings ALTER COLUMN id SET DEFAULT nextval('public.verse_embeddings_id_seq'::regclass);


--
-- Name: KJV_books KJV_books_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."KJV_books"
    ADD CONSTRAINT "KJV_books_pkey" PRIMARY KEY (id);


--
-- Name: KJV_verses KJV_verses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."KJV_verses"
    ADD CONSTRAINT "KJV_verses_pkey" PRIMARY KEY (id);


--
-- Name: ane_context ane_context_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ane_context
    ADD CONSTRAINT ane_context_pkey PRIMARY KEY (id);


--
-- Name: aquifer_content aquifer_content_content_id_resource_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aquifer_content
    ADD CONSTRAINT aquifer_content_content_id_resource_type_key UNIQUE (content_id, resource_type);


--
-- Name: aquifer_content aquifer_content_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aquifer_content
    ADD CONSTRAINT aquifer_content_pkey PRIMARY KEY (id);


--
-- Name: bible_books bible_books_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_books
    ADD CONSTRAINT bible_books_pkey PRIMARY KEY (id);


--
-- Name: bible_cross_references bible_cross_references_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_cross_references
    ADD CONSTRAINT bible_cross_references_pkey PRIMARY KEY (id);


--
-- Name: bible_extra_biblical bible_extra_biblical_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_extra_biblical
    ADD CONSTRAINT bible_extra_biblical_pkey PRIMARY KEY (id);


--
-- Name: bible_translations bible_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_translations
    ADD CONSTRAINT bible_translations_pkey PRIMARY KEY (id);


--
-- Name: bible_verses bible_verses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_verses
    ADD CONSTRAINT bible_verses_pkey PRIMARY KEY (id);


--
-- Name: books books_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_pkey PRIMARY KEY (id);


--
-- Name: books books_translation_id_osis_ref_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_translation_id_osis_ref_key UNIQUE (translation_id, osis_ref);


--
-- Name: commentaries commentaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commentaries
    ADD CONSTRAINT commentaries_pkey PRIMARY KEY (id);


--
-- Name: extra_biblical_texts extra_biblical_texts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_biblical_texts
    ADD CONSTRAINT extra_biblical_texts_pkey PRIMARY KEY (id);


--
-- Name: strongs_lexicon strongs_lexicon_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_lexicon
    ADD CONSTRAINT strongs_lexicon_pkey PRIMARY KEY (id);


--
-- Name: strongs_lexicon strongs_lexicon_strongs_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_lexicon
    ADD CONSTRAINT strongs_lexicon_strongs_id_key UNIQUE (strongs_id);


--
-- Name: strongs_verse_map strongs_verse_map_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_verse_map
    ADD CONSTRAINT strongs_verse_map_pkey PRIMARY KEY (id);


--
-- Name: strongs_verse_map strongs_verse_map_verse_id_strongs_id_position_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_verse_map
    ADD CONSTRAINT strongs_verse_map_verse_id_strongs_id_position_key UNIQUE (verse_id, strongs_id, "position");


--
-- Name: theographic theographic_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theographic
    ADD CONSTRAINT theographic_entity_id_key UNIQUE (entity_id);


--
-- Name: theographic theographic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theographic
    ADD CONSTRAINT theographic_pkey PRIMARY KEY (id);


--
-- Name: theographic_relations theographic_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theographic_relations
    ADD CONSTRAINT theographic_relations_pkey PRIMARY KEY (id);


--
-- Name: theological_themes theological_themes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theological_themes
    ADD CONSTRAINT theological_themes_pkey PRIMARY KEY (id);


--
-- Name: theological_works theological_works_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theological_works
    ADD CONSTRAINT theological_works_pkey PRIMARY KEY (id);


--
-- Name: translations translations_abbreviation_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.translations
    ADD CONSTRAINT translations_abbreviation_key UNIQUE (abbreviation);


--
-- Name: translations translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.translations
    ADD CONSTRAINT translations_pkey PRIMARY KEY (id);


--
-- Name: verse_embeddings verse_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verse_embeddings
    ADD CONSTRAINT verse_embeddings_pkey PRIMARY KEY (id);


--
-- Name: verses verses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verses
    ADD CONSTRAINT verses_pkey PRIMARY KEY (id);


--
-- Name: idx_commentaries_author; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_commentaries_author ON public.commentaries USING btree (author);


--
-- Name: idx_commentaries_fulltext; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_commentaries_fulltext ON public.commentaries USING gin (to_tsvector('english'::regconfig, quote));


--
-- Name: idx_commentaries_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_commentaries_ref ON public.commentaries USING btree (book_osis, chapter, verse_start);


--
-- Name: idx_extra_biblical_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extra_biblical_embedding ON public.extra_biblical_texts USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_extra_biblical_text_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extra_biblical_text_fts ON public.extra_biblical_texts USING gin (to_tsvector('english'::regconfig, text));


--
-- Name: idx_theol_works_author; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_theol_works_author ON public.theological_works USING btree (author);


--
-- Name: idx_theol_works_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_theol_works_title ON public.theological_works USING btree (work_title);


--
-- Name: idx_verse_embeddings_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verse_embeddings_ref ON public.verse_embeddings USING btree (book, chapter, verse);


--
-- Name: idx_verse_embeddings_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verse_embeddings_vector ON public.verse_embeddings USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: KJV_verses KJV_verses_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."KJV_verses"
    ADD CONSTRAINT "KJV_verses_book_id_fkey" FOREIGN KEY (book_id) REFERENCES public."KJV_books"(id);


--
-- Name: bible_books bible_books_translation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_books
    ADD CONSTRAINT bible_books_translation_id_fkey FOREIGN KEY (translation_id) REFERENCES public.bible_translations(id);


--
-- Name: bible_verses bible_verses_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bible_verses
    ADD CONSTRAINT bible_verses_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.bible_books(id);


--
-- Name: books books_translation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_translation_id_fkey FOREIGN KEY (translation_id) REFERENCES public.translations(id) ON DELETE CASCADE;


--
-- Name: strongs_verse_map strongs_verse_map_strongs_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.strongs_verse_map
    ADD CONSTRAINT strongs_verse_map_strongs_id_fkey FOREIGN KEY (strongs_id) REFERENCES public.strongs_lexicon(strongs_id) ON DELETE CASCADE;


--
-- Name: verse_embeddings verse_embeddings_verse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verse_embeddings
    ADD CONSTRAINT verse_embeddings_verse_id_fkey FOREIGN KEY (verse_id) REFERENCES public.verses(id);

-- Search and lookup indexes used by the MCP server.
CREATE INDEX idx_bible_books_translation_osis ON public.bible_books (translation_id, osis_ref);
CREATE INDEX idx_bible_verses_book_chapter_verse ON public.bible_verses (book_id, chapter, verse);
CREATE INDEX idx_bible_verses_fts ON public.bible_verses USING gin (to_tsvector('english', text));
CREATE INDEX idx_theological_works_fts ON public.theological_works USING gin (to_tsvector('english', text));

-- Fresh installs restore the schema as postgres; grant the runtime/import role access.
GRANT USAGE ON SCHEMA public TO theosis;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO theosis;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO theosis;

--
-- PostgreSQL database dump complete
--

\unrestrict IPGmSoL2crlthvGR1pipgt0N5qbnoLEuQ3cEhJxJFjYF4XWLhDKKCwWeCBUQ6B9

