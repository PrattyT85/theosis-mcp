#!/usr/bin/env python3
"""
Build biblical name etymology dataset and populate the names table.

Curated from Hebrew and Greek name meanings — major biblical figures
with original language roots, meanings, and key verse references.

Usage:
  python3 scripts/build_names.py
"""

import asyncio
import os

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# Format: (name, name_original, type, description, refs, relationships)
NAMES = [
    # =========================================================================
    # Names of God
    # =========================================================================
    ("Yahweh / Jehovah", "יהוה (YHWH)", "divine_name",
     "The covenant name of God — 'I AM WHO I AM.' The tetragrammaton, considered too sacred to pronounce by Jews. Typically rendered 'LORD' in English translations.",
     "Exo 3:14; Exo 6:3; Psa 83:18", "Adonai; Elohim"),
    ("Elohim", "אלהים", "divine_name",
     "The generic Hebrew word for 'God' or 'gods.' Plural in form but used with singular verbs for the one true God. Also used of the divine council (Psalm 82).",
     "Gen 1:1; Psa 82:1; Deu 32:8", "Yahweh; Adonai"),
    ("Adonai", "אדני", "divine_name",
     "Hebrew for 'my Lord' — used as a substitute for YHWH in reading. Expresses God's sovereignty and authority.",
     "Psa 110:1; Isa 6:1", "Yahweh"),
    ("El Shaddai", "אל שדי", "divine_name",
     "God Almighty — the all-sufficient God. The name by which God revealed Himself to the patriarchs (Abraham, Isaac, Jacob).",
     "Gen 17:1; Gen 35:11; Exo 6:3", "Yahweh; Elohim"),
    ("El Elyon", "אל עליון", "divine_name",
     "God Most High — emphasizing God's supreme sovereignty over all nations and spiritual powers. Used by Melchizedek.",
     "Gen 14:18; Psa 78:35; Dan 4:34", "Yahweh"),
    ("Yahweh Yireh", "יהוה יראה", "divine_name",
     "The LORD Will Provide — Abraham's name for God at the binding of Isaac (Moriah).",
     "Gen 22:14", "Yahweh"),
    ("Yahweh Nissi", "יהוה נסי", "divine_name",
     "The LORD Is My Banner — Moses' name for God after the victory over Amalek.",
     "Exo 17:15", "Yahweh"),
    ("Yahweh Shalom", "יהוה שלום", "divine_name",
     "The LORD Is Peace — Gideon's name for God after the angelic visitation.",
     "Jdg 6:24", "Yahweh"),
    ("Theos", "Θεός", "divine_name",
     "Greek for 'God' — the standard NT designation for the one true God. Used of the Father most frequently, but also of Christ (John 1:1, 20:28).",
     "Jhn 1:1; Jhn 20:28; Rom 9:5", "Kyrios"),
    ("Kyrios", "Κύριος", "divine_name",
     "Greek for 'Lord' — the NT equivalent of Adonai and the Septuagint rendering of YHWH. Applied to Jesus as the confession of His deity.",
     "Php 2:11; Rom 10:9; 1Co 12:3", "Theos; Iesous"),

    # =========================================================================
    # Personal Names (Hebrew — Genesis/NT)
    # =========================================================================
    ("Adam", "אָדָם (adam)", "personal_name",
     "Man, humanity. From adamah (ground/earth), since man was formed from the dust of the ground. Also related to adom (red).",
     "Gen 2:7; Gen 5:2", "Eve; Seth"),
    ("Eve", "חַוָּה (Chavvah)", "personal_name",
     "Life-giver, living. The mother of all living (Gen 3:20). From chayah (to live).",
     "Gen 3:20", "Adam"),
    ("Abraham", "אַבְרָהָם (Avraham)", "personal_name",
     "Father of a multitude. Originally Abram ('exalted father'), God changed his name to signify the covenant promise of many descendants.",
     "Gen 17:5", "Sarah; Isaac; Ishmael"),
    ("Sarah", "שָׂרָה (Sarah)", "personal_name",
     "Princess. Originally Sarai ('my princess'), changed to Sarah ('princess' to all nations) as part of the covenant.",
     "Gen 17:15", "Abraham; Isaac"),
    ("Isaac", "יִצְחָק (Yitzchak)", "personal_name",
     "He laughs. Named for both Abraham's and Sarah's laughter at the promise of a son in old age, and the joy of his birth.",
     "Gen 21:6", "Abraham; Sarah; Jacob; Esau"),
    ("Jacob", "יַעֲקֹב (Ya'akov)", "personal_name",
     "Heel-grabber, supplanter. Born grasping Esau's heel. Later renamed Israel ('one who strives with God') after wrestling at Peniel.",
     "Gen 25:26; Gen 32:28", "Isaac; Rebekah; Israel"),
    ("Israel", "יִשְׂרָאֵל (Yisrael)", "personal_name",
     "One who strives/prevails with God. Jacob's new name after wrestling with the angel. Also the name of the nation descended from him.",
     "Gen 32:28; Gen 35:10", "Jacob"),
    ("Joseph", "יוֹסֵף (Yosef)", "personal_name",
     "May He (YHWH) add. Rachel's cry at his birth. Fitting for the son who was 'added' back to his family after being presumed dead.",
     "Gen 30:24", "Jacob; Rachel; Benjamin"),
    ("Moses", "מֹשֶׁה (Moshe)", "personal_name",
     "Drawn out. Named by Pharaoh's daughter because she drew him from the water. Hebrew pun: mosheh sounds like mashah (to draw out).",
     "Exo 2:10", "Aaron; Miriam; Joshua"),
    ("Aaron", "אַהֲרֹן (Aharon)", "personal_name",
     "Uncertain etymology — possibly 'mountain' or 'enlightened.' First High Priest of Israel, brother of Moses.",
     "Exo 4:14; Exo 28:1", "Moses; Miriam"),
    ("Joshua", "יְהוֹשֻׁעַ (Yehoshua)", "personal_name",
     "YHWH is salvation. The Hebrew form of 'Jesus.' Moses' successor who led Israel into the Promised Land.",
     "Num 13:16; Jos 1:1", "Moses; Jesus"),
    ("Samuel", "שְׁמוּאֵל (Shemuel)", "personal_name",
     "Heard by God, or name of God. Hannah's prayer was heard, and Samuel became God's prophet. Also a wordplay on shaul (asked).",
     "1Sa 1:20", "Hannah; Eli"),
    ("David", "דָּוִד (David)", "personal_name",
     "Beloved. The shepherd-king, man after God's own heart. His name became synonymous with the Messianic hope.",
     "1Sa 16:13; 2Sa 7:8", "Jesse; Solomon; Jesus"),
    ("Solomon", "שְׁלֹמֹה (Shelomoh)", "personal_name",
     "Peaceful, his peace. From shalom. Named Jedidiah ('beloved of YHWH') by Nathan but called Solomon. Builder of the Temple.",
     "2Sa 12:24; 1Ki 3:1", "David; Bathsheba"),
    ("Elijah", "אֵלִיָּהוּ (Eliyahu)", "personal_name",
     "My God is YHWH. The great prophet whose very name was his message — a declaration against Baal worship at Carmel.",
     "1Ki 17:1; 1Ki 18:21", "Elisha"),
    ("Isaiah", "יְשַׁעְיָהוּ (Yeshayahu)", "personal_name",
     "YHWH is salvation. The messianic prophet whose name encapsulates his message of redemption.",
     "Isa 1:1; Isa 6:1", "Hezekiah"),
    ("Jeremiah", "יִרְמְיָהוּ (Yirmeyahu)", "personal_name",
     "YHWH exalts, or YHWH throws. The weeping prophet whose life embodied his message of judgment and hope.",
     "Jer 1:1", "Baruch"),
    ("Ezekiel", "יְחֶזְקֵאל (Yechezkel)", "personal_name",
     "God strengthens. The prophet in exile whose visions sustained Israel in Babylon.",
     "Ezk 1:1", "Daniel"),
    ("Daniel", "דָּנִיֵּאל (Daniyyel)", "personal_name",
     "God is my judge. The prophet who remained faithful in Babylon. His name declared his trust in God's justice over Babylon's courts.",
     "Dan 1:7", "Hananiah; Mishael; Azariah"),
    ("Hosea", "הוֹשֵׁעַ (Hoshea)", "personal_name",
     "Salvation, deliverance. The prophet whose marriage to Gomer became a living parable of God's faithful love for unfaithful Israel.",
     "Hos 1:1", "Gomer"),
    ("Jonah", "יוֹנָה (Yonah)", "personal_name",
     "Dove. The reluctant prophet. The dove symbolized peace and the Spirit — ironic for the prophet who fled from God's call.",
     "Jon 1:1", ""),
    ("Job", "אִיּוֹב (Iyyov)", "personal_name",
     "Persecuted, or where is my father? The righteous sufferer whose name may reflect his cry for God in affliction.",
     "Job 1:1", ""),
    ("Nehemiah", "נְחֶמְיָה (Nechemyah)", "personal_name",
     "YHWH comforts. The cupbearer who rebuilt Jerusalem's walls. His name reflected his mission — bringing comfort to a broken city.",
     "Neh 1:1", "Ezra"),
    ("Ezra", "עֶזְרָא (Ezra)", "personal_name",
     "Help. The priest-scribe who led spiritual renewal after the exile. His name summarized his ministry.",
     "Ezr 7:1", "Nehemiah"),
    ("Esther", "אֶסְתֵּר (Ester)", "personal_name",
     "Star (Persian). Her Hebrew name was Hadassah ('myrtle'). Like a star, she shone in the darkness of Persian exile to save her people.",
     "Est 2:7", "Mordecai; Hadassah"),
    ("Ruth", "רוּת (Rut)", "personal_name",
     "Friend, companion. The Moabite woman whose loyal friendship to Naomi became the channel of messianic blessing.",
     "Rut 1:16", "Naomi; Boaz; David"),

    # =========================================================================
    # NT Personal Names (Greek)
    # =========================================================================
    ("Jesus", "Ἰησοῦς (Iesous)", "personal_name",
     "YHWH is salvation. Greek form of the Hebrew Yehoshua/Joshua. Named by angelic command: 'you shall call His name Jesus, for He will save His people from their sins.'",
     "Mat 1:21; Php 2:10", "Christ; Joshua"),
    ("Christ", "Χριστός (Christos)", "title",
     "Anointed One. Greek translation of Hebrew Mashiach (Messiah). Not a surname but a title — Jesus the Christ, the Anointed King.",
     "Mat 16:16; Jhn 1:41; Act 2:36", "Jesus; Messiah"),
    ("Messiah", "מָשִׁיחַ (Mashiach)", "title",
     "Anointed One. The long-awaited deliverer of Israel, prophesied throughout the OT. Applied to kings, priests, and ultimately the eschatological Savior.",
     "Psa 2:2; Dan 9:25; Jhn 4:25", "Christ; Jesus"),
    ("Immanuel", "עִמָּנוּאֵל (Immanu-El)", "title",
     "God with us. The name prophesied by Isaiah and fulfilled in Jesus. Not used as a personal name but as a declaration of His identity.",
     "Isa 7:14; Mat 1:23", "Jesus"),
    ("Peter", "Πέτρος (Petros)", "personal_name",
     "Rock. Originally Simon (Shimon, 'hearing'), Jesus renamed him Cephas (Aramaic) / Peter (Greek) — 'on this rock I will build my church.'",
     "Mat 16:18; Jhn 1:42", "Cephas; Simon"),
    ("Andrew", "Ἀνδρέας (Andreas)", "personal_name",
     "Manly, courageous. From Greek aner (man). The first disciple called, who immediately brought his brother Peter to Jesus.",
     "Jhn 1:40", "Peter"),
    ("John", "Ἰωάννης (Ioannes)", "personal_name",
     "YHWH is gracious. Hebrew Yochanan. The beloved disciple, author of the Gospel, epistles, and Revelation.",
     "Mat 4:21; Jhn 13:23", "James; Jesus"),
    ("Paul", "Παῦλος (Paulos)", "personal_name",
     "Small, humble. Originally Saul (Sha'ul — 'asked for'), the Pharisee-persecutor. His name change may reflect his new identity or simply his Roman name for Gentile ministry.",
     "Act 13:9", "Saul; Timothy"),
    ("Timothy", "Τιμόθεος (Timotheos)", "personal_name",
     "Honoring God. From time (honor) + theos (God). Paul's beloved son in the faith, pastor at Ephesus.",
     "Act 16:1; 1Ti 1:2", "Paul"),
    ("Stephen", "Στέφανος (Stephanos)", "personal_name",
     "Crown. The first Christian martyr. His name proved prophetic — he received the martyr's crown.",
     "Act 6:5; Act 7:59", ""),
    ("Barnabas", "Βαρνάβας (Barnabas)", "personal_name",
     "Son of encouragement. Originally Joseph, the apostles gave him this name because of his generous and encouraging character.",
     "Act 4:36", "Paul; Mark"),
    ("Mary", "Μαριάμ (Mariam)", "personal_name",
     "Bitter, or beloved. Hebrew Miryam. Moses' sister bore the same name. The mother of Jesus — 'blessed among women.'",
     "Luk 1:28; Mat 1:16", "Jesus; Joseph"),
    ("Thomas", "Θωμᾶς (Thomas)", "personal_name",
     "Twin. Aramaic T'oma. Called Didymus (Greek for twin). Known as doubting Thomas, but also the one who declared 'My Lord and my God!'",
     "Jhn 20:28", ""),
    ("Matthew", "Μαθθαῖος (Matthaios)", "personal_name",
     "Gift of YHWH. Hebrew Mattityahu. Also called Levi. The tax collector who became an apostle and gospel writer.",
     "Mat 9:9", "Levi"),
    ("Elizabeth", "Ἐλισάβετ (Elisabet)", "personal_name",
     "God is my oath. Hebrew Elisheva. Mother of John the Baptist, cousin of Mary. Her name spoke of God's faithfulness to His covenant.",
     "Luk 1:5", "Zechariah; John the Baptist; Mary"),
    ("Lazarus", "Λάζαρος (Lazaros)", "personal_name",
     "God has helped. Shortened form of Hebrew Eleazar. Raised from the dead by Jesus after four days in the tomb.",
     "Jhn 11:1", "Mary; Martha"),
    ("Nicodemus", "Νικόδημος (Nikodemos)", "personal_name",
     "Victory of the people. From nike (victory) + demos (people). The Pharisee who came to Jesus by night and later helped bury Him.",
     "Jhn 3:1; Jhn 19:39", ""),
    ("Magdalene", "Μαγδαληνή (Magdalene)", "personal_name",
     "Of Magdala. Mary from the town of Magdala (Migdal, 'tower'). The first witness of the resurrection.",
     "Luk 8:2; Jhn 20:1", "Jesus"),

    # =========================================================================
    # Tribes & Group Names
    # =========================================================================
    ("Judah", "יְהוּדָה (Yehudah)", "tribe_name",
     "Praise. Leah's fourth son: 'This time I will praise the LORD.' The royal tribe from which David and Jesus descended.",
     "Gen 29:35; Gen 49:10; Rev 5:5", "David; Jesus"),
    ("Levi", "לֵוִי (Levi)", "tribe_name",
     "Joined, attached. Leah's third son: 'Now my husband will be joined to me.' The priestly tribe, set apart for Tabernacle/Temple service.",
     "Gen 29:34; Num 3:12", "Aaron; Moses"),
    ("Ephraim", "אֶפְרַיִם (Ephrayim)", "tribe_name",
     "Fruitful. Joseph's younger son, blessed above his brother Manasseh by Jacob. Became the dominant northern tribe.",
     "Gen 41:52; Gen 48:19", "Joseph; Manasseh"),
    ("Benjamin", "בִּנְיָמִין (Binyamin)", "tribe_name",
     "Son of my right hand. Originally Ben-Oni ('son of my sorrow') by Rachel's death, renamed by Jacob. The smallest tribe that produced King Saul and the apostle Paul.",
     "Gen 35:18; 1Sa 9:1", "Rachel; Jacob; Saul; Paul"),
    ("Israel (nation)", "יִשְׂרָאֵל", "tribe_name",
     "The covenant people of God, descended from the twelve sons of Jacob/Israel. Chosen to be a light to the nations and the channel of Messiah.",
     "Gen 32:28; Exo 19:6; Rom 9:4", "Jacob"),
    ("Pharisees", "פְּרוּשִׁים (Perushim)", "group_name",
     "Separated ones. A Jewish sect devoted to meticulous observance of the Torah and oral traditions. Included Nicodemus, Gamaliel, and Paul before conversion.",
     "Mat 3:7; Act 23:6", "Sadducees; Essenes"),
    ("Sadducees", "צְדוּקִים (Tzedukim)", "group_name",
     "Followers of Zadok the priest. The aristocratic priestly party who denied resurrection, angels, and spirits. Controlled the Temple.",
     "Mat 22:23; Act 23:8", "Pharisees"),
    ("Gentiles", "ἔθνη (ethne)", "group_name",
     "Nations. Hebrew goyim. All non-Jewish peoples. In NT theology, the inclusion of Gentiles in God's covenant people was the 'mystery' revealed to Paul.",
     "Gen 12:3; Act 10:45; Eph 3:6", "Israel"),
]


async def main():
    pg = await asyncpg.connect(DB_URL)

    # Fix id column if needed
    await pg.execute("""
        CREATE SEQUENCE IF NOT EXISTS names_id_seq;
        ALTER TABLE names ALTER COLUMN id SET DEFAULT nextval('names_id_seq');
    """)

    # Clear existing
    await pg.execute("TRUNCATE names RESTART IDENTITY")

    count = 0
    for (name, original, ntype, desc, refs, relationships) in NAMES:
        await pg.execute(
            """INSERT INTO names (name, name_original, type, description, refs, relationships)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            name, original, ntype, desc, refs, relationships
        )
        count += 1

    print(f"\n{'='*50}")
    print("Names Import Complete")
    print(f"  Names: {count}")

    # Breakdown
    types = await pg.fetch(
        "SELECT type, COUNT(*) as cnt FROM names GROUP BY type ORDER BY cnt DESC"
    )
    for row in types:
        print(f"  {row['type']:20s} {row['cnt']}")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
