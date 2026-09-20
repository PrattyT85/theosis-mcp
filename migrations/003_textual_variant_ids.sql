BEGIN;

CREATE SEQUENCE IF NOT EXISTS public.textual_variants_id_seq;
SELECT setval('public.textual_variants_id_seq', COALESCE((SELECT max(id) FROM public.textual_variants), 0) + 1, false);
UPDATE public.textual_variants SET id = nextval('public.textual_variants_id_seq') WHERE id IS NULL;
ALTER SEQUENCE public.textual_variants_id_seq OWNED BY public.textual_variants.id;
ALTER TABLE public.textual_variants ALTER COLUMN id SET DEFAULT nextval('public.textual_variants_id_seq'::regclass);
ALTER TABLE public.textual_variants ALTER COLUMN id SET NOT NULL;
ALTER TABLE public.textual_variants ADD CONSTRAINT textual_variants_pkey PRIMARY KEY (id);

CREATE SEQUENCE IF NOT EXISTS public.manuscript_witnesses_id_seq;
SELECT setval('public.manuscript_witnesses_id_seq', COALESCE((SELECT max(id) FROM public.manuscript_witnesses), 0) + 1, false);
UPDATE public.manuscript_witnesses SET id = nextval('public.manuscript_witnesses_id_seq') WHERE id IS NULL;
ALTER SEQUENCE public.manuscript_witnesses_id_seq OWNED BY public.manuscript_witnesses.id;
ALTER TABLE public.manuscript_witnesses ALTER COLUMN id SET DEFAULT nextval('public.manuscript_witnesses_id_seq'::regclass);
ALTER TABLE public.manuscript_witnesses ALTER COLUMN id SET NOT NULL;
ALTER TABLE public.manuscript_witnesses ADD CONSTRAINT manuscript_witnesses_pkey PRIMARY KEY (id);

COMMIT;
