#!/usr/bin/env python3
"""
Build biblical genealogy dataset and populate graph_people, graph_family_edges,
theographic, and theographic_relations tables.

Data: Manually curated from Genesis 5, 10, 11, 25, 36; Ruth 4; 1 Chronicles 1-9;
Matthew 1; Luke 3.

Usage:
  python3 scripts/build_genealogy.py

Sources: Holy Bible (public domain genealogical records)
"""

import asyncio
import json
import os

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# ---------------------------------------------------------------------------
# BIBLICAL GENEALOGY DATA — 113 major figures from Adam to the Apostles
# ---------------------------------------------------------------------------
# Format: (id, name, also_called, gender, birth_year_approx, death_year_approx, description)

PEOPLE = [
    # Genesis 5: Adam → Noah
    ("adam_1", "Adam", "First Man", "male", None, None, "First man, created by God. Father of Cain, Abel, Seth."),
    ("eve_1", "Eve", "First Woman", "female", None, None, "First woman, mother of all living."),
    ("seth_1", "Seth", None, "male", None, None, "Third son of Adam and Eve, ancestor of Noah and Jesus."),
    ("enosh_1", "Enosh", "Enos", "male", None, None, "Son of Seth. In his days men began to call on the name of the Lord."),
    ("kenan_1", "Kenan", "Cainan", "male", None, None, "Son of Enosh."),
    ("mahalalel_1", "Mahalalel", "Mahalaleel", "male", None, None, "Son of Kenan."),
    ("jared_1", "Jared", "Jered", "male", None, None, "Son of Mahalalel. Father of Enoch."),
    ("enoch_1", "Enoch", None, "male", None, None, "Walked with God and was taken. Father of Methuselah."),
    ("methuselah_1", "Methuselah", None, "male", None, None, "Oldest man in the Bible (969 years). Son of Enoch."),
    ("lamech_1", "Lamech", None, "male", None, None, "Son of Methuselah. Father of Noah."),
    ("noah_1", "Noah", "Noe", "male", None, None, "Built the ark. Saved from the flood with his family."),
    ("shem_1", "Shem", None, "male", None, None, "Son of Noah. Ancestor of Abraham and the Semitic peoples."),
    ("ham_1", "Ham", None, "male", None, None, "Son of Noah. Father of Canaan, Cush, Mizraim, Put."),
    ("japheth_1", "Japheth", None, "male", None, None, "Son of Noah. Ancestor of Indo-European peoples."),

    # Genesis 11: Shem → Abram
    ("arpachshad_1", "Arpachshad", "Arphaxad", "male", None, None, "Son of Shem."),
    ("shelah_1", "Shelah", "Sala", "male", None, None, "Son of Arpachshad."),
    ("eber_1", "Eber", "Heber", "male", None, None, "Son of Shelah. The name 'Hebrew' likely derives from Eber."),
    ("peleg_1", "Peleg", None, "male", None, None, "Son of Eber. In his days the earth was divided."),
    ("reu_1", "Reu", None, "male", None, None, "Son of Peleg."),
    ("serug_1", "Serug", None, "male", None, None, "Son of Reu."),
    ("nahor_1", "Nahor", None, "male", None, None, "Son of Serug. Grandfather of Abraham."),
    ("terah_1", "Terah", None, "male", None, None, "Son of Nahor. Father of Abraham, Nahor, and Haran."),

    # Patriarchs
    ("abraham_1", "Abraham", "Abram", "male", None, None, "Father of the faithful. Received God's covenant."),
    ("sarah_1", "Sarah", "Sarai", "female", None, None, "Wife of Abraham. Mother of Isaac."),
    ("hagar_1", "Hagar", None, "female", None, None, "Egyptian servant of Sarah. Mother of Ishmael."),
    ("keturah_1", "Keturah", None, "female", None, None, "Second wife of Abraham. Mother of six sons including Midian."),
    ("lot_1", "Lot", None, "male", None, None, "Nephew of Abraham. Father of Moab and Ammon."),
    ("ishmael_1", "Ishmael", None, "male", None, None, "Son of Abraham and Hagar. Ancestor of the Ishmaelites."),
    ("isaac_1", "Isaac", None, "male", None, None, "Son of promise. Son of Abraham and Sarah."),
    ("rebekah_1", "Rebekah", "Rebecca", "female", None, None, "Wife of Isaac. Mother of Jacob and Esau."),
    ("esau_1", "Esau", "Edom", "male", None, None, "Son of Isaac. Ancestor of the Edomites. Sold his birthright."),
    ("jacob_1", "Jacob", "Israel", "male", None, None, "Son of Isaac. Father of the twelve tribes of Israel."),
    ("leah_1", "Leah", None, "female", None, None, "First wife of Jacob. Mother of six sons and Dinah."),
    ("rachel_1", "Rachel", None, "female", None, None, "Beloved wife of Jacob. Mother of Joseph and Benjamin."),
    ("bilhah_1", "Bilhah", None, "female", None, None, "Rachel's servant. Mother of Dan and Naphtali."),
    ("zilpah_1", "Zilpah", None, "female", None, None, "Leah's servant. Mother of Gad and Asher."),

    # Twelve sons of Jacob / Tribes of Israel
    ("reuben_1", "Reuben", None, "male", None, None, "Firstborn of Jacob and Leah. Lost his birthright."),
    ("simeon_1", "Simeon", None, "male", None, None, "Second son of Jacob and Leah."),
    ("levi_1", "Levi", None, "male", None, None, "Third son of Jacob and Leah. Ancestor of the priestly tribe."),
    ("judah_1", "Judah", None, "male", None, None, "Fourth son of Jacob and Leah. Ancestor of David and Jesus."),
    ("dan_1", "Dan", None, "male", None, None, "Fifth son of Jacob, first of Bilhah."),
    ("naphtali_1", "Naphtali", None, "male", None, None, "Sixth son of Jacob, second of Bilhah."),
    ("gad_1", "Gad", None, "male", None, None, "Seventh son of Jacob, first of Zilpah."),
    ("asher_1", "Asher", None, "male", None, None, "Eighth son of Jacob, second of Zilpah."),
    ("issachar_1", "Issachar", None, "male", None, None, "Ninth son of Jacob, fifth of Leah."),
    ("zebulun_1", "Zebulun", None, "male", None, None, "Tenth son of Jacob, sixth of Leah."),
    ("joseph_1", "Joseph", None, "male", None, None, "Eleventh son of Jacob, first of Rachel. Rose to power in Egypt."),
    ("benjamin_1", "Benjamin", None, "male", None, None, "Twelfth son of Jacob, second of Rachel."),
    ("dinah_1", "Dinah", None, "female", None, None, "Daughter of Jacob and Leah."),

    # Judah's line → David
    ("perez_1", "Perez", "Phares", "male", None, None, "Son of Judah and Tamar. Ancestor of David."),
    ("hezron_1", "Hezron", "Esrom", "male", None, None, "Son of Perez."),
    ("ram_1", "Ram", "Aram", "male", None, None, "Son of Hezron."),
    ("amminadab_1", "Amminadab", None, "male", None, None, "Son of Ram. Father-in-law of Aaron."),
    ("nahshon_1", "Nahshon", "Naasson", "male", None, None, "Son of Amminadab. Leader of Judah in the wilderness."),
    ("salmon_1", "Salmon", None, "male", None, None, "Son of Nahshon. Husband of Rahab."),
    ("boaz_1", "Boaz", "Booz", "male", None, None, "Son of Salmon. Husband of Ruth. Kinsman-redeemer."),
    ("ruth_1", "Ruth", None, "female", None, None, "Moabite woman. Wife of Boaz. Great-grandmother of David."),
    ("obed_1", "Obed", None, "male", None, None, "Son of Boaz and Ruth. Father of Jesse."),
    ("jesse_1", "Jesse", None, "male", None, None, "Son of Obed. Father of King David."),

    # United Monarchy
    ("david_1", "David", None, "male", None, None, "Second king of Israel. Man after God's own heart. Psalmist."),
    ("bathsheba_1", "Bathsheba", "Bath-shua", "female", None, None, "Wife of David. Mother of Solomon."),
    ("solomon_1", "Solomon", "Jedidiah", "male", None, None, "Son of David and Bathsheba. Wisest king. Built the Temple."),
    ("rehoboam_1", "Rehoboam", None, "male", None, None, "Son of Solomon. First king of Judah after the division."),
    ("abijah_1", "Abijah", "Abijam", "male", None, None, "Son of Rehoboam. King of Judah."),
    ("asa_1", "Asa", None, "male", None, None, "Son of Abijah. Righteous king of Judah."),
    ("jehoshaphat_1", "Jehoshaphat", None, "male", None, None, "Son of Asa. Godly king of Judah."),
    ("jehoram_1", "Jehoram", "Joram", "male", None, None, "Son of Jehoshaphat. King of Judah."),
    ("uzziah_1", "Uzziah", "Azariah", "male", None, None, "Son of Jehoram (per Matthew's genealogy). King of Judah."),
    ("jotham_1", "Jotham", None, "male", None, None, "Son of Uzziah. King of Judah."),
    ("ahaz_1", "Ahaz", None, "male", None, None, "Son of Jotham. Wicked king of Judah."),
    ("hezekiah_1", "Hezekiah", None, "male", None, None, "Son of Ahaz. Righteous king who trusted God against Assyria."),
    ("manasseh_1", "Manasseh", None, "male", None, None, "Son of Hezekiah. Wicked king who later repented."),
    ("amon_1", "Amon", None, "male", None, None, "Son of Manasseh. King of Judah."),
    ("josiah_1", "Josiah", None, "male", None, None, "Son of Amon. Righteous king who rediscovered the Law."),
    ("jeconiah_1", "Jeconiah", "Jehoiachin, Coniah", "male", None, None, "Son of Josiah (per Matthew). Exiled to Babylon."),
    ("shealtiel_1", "Shealtiel", "Salathiel", "male", None, None, "Son of Jeconiah. Father of Zerubbabel."),
    ("zerubbabel_1", "Zerubbabel", "Zorobabel", "male", None, None, "Son of Shealtiel. Led return from exile. Rebuilt the Temple."),
    ("abihud_1", "Abihud", None, "male", None, None, "Son of Zerubbabel (per Matthew)."),
    ("eliakim_1", "Eliakim", None, "male", None, None, "Son of Abihud."),
    ("azor_1", "Azor", None, "male", None, None, "Son of Eliakim."),
    ("zadok_1", "Zadok", None, "male", None, None, "Son of Azor."),
    ("achim_1", "Achim", None, "male", None, None, "Son of Zadok."),
    ("elihud_1", "Elihud", None, "male", None, None, "Son of Achim."),
    ("eleazar_3", "Eleazar", None, "male", None, None, "Son of Elihud."),
    ("matthan_1", "Matthan", None, "male", None, None, "Son of Eleazar."),
    ("jacob_2", "Jacob", None, "male", None, None, "Son of Matthan. Father of Joseph (husband of Mary)."),

    # New Testament
    ("joseph_2", "Joseph", None, "male", None, None, "Husband of Mary. Legal father of Jesus. A righteous man."),
    ("mary_1", "Mary", "Miriam", "female", None, None, "Mother of Jesus. Virgin who conceived by the Holy Spirit."),
    ("jesus_1", "Jesus", "Jesus Christ, Messiah, Yeshua", "male", None, None, "Son of God. Savior of the world. The Word made flesh."),
    ("john_baptist_1", "John the Baptist", None, "male", None, None, "Son of Zechariah and Elizabeth. Forerunner of Christ."),

    # Key Levites/Priests
    ("aaron_1", "Aaron", None, "male", None, None, "Brother of Moses. First High Priest of Israel."),
    ("miriam_1", "Miriam", None, "female", None, None, "Sister of Moses and Aaron. Prophetess."),
    ("moses_1", "Moses", None, "male", None, None, "Lawgiver. Led Israel out of Egypt. Received the Torah."),
    ("joshua_1", "Joshua", "Jehoshua", "male", None, None, "Successor of Moses. Led Israel into the Promised Land."),
    ("phinehas_1", "Phinehas", None, "male", None, None, "Son of Eleazar. Zealous priest. Made an eternal covenant."),
    ("eli_1", "Eli", None, "male", None, None, "High priest and judge of Israel. Mentor of Samuel."),
    ("samuel_1", "Samuel", None, "male", None, None, "Last judge of Israel. Prophet who anointed Saul and David."),
    ("saul_1", "Saul", None, "male", None, None, "First king of Israel. Rejected by God for disobedience."),
    ("jonathan_1", "Jonathan", None, "male", None, None, "Son of Saul. Faithful friend of David."),
    ("zadok_2", "Zadok the Priest", None, "male", None, None, "Faithful priest under David and Solomon."),

    # Prophets
    ("elijah_1", "Elijah", None, "male", None, None, "Great prophet. Confronted Baal on Mount Carmel. Taken to heaven."),
    ("elisha_1", "Elisha", None, "male", None, None, "Successor of Elijah. Received a double portion of his spirit."),
    ("isaiah_1", "Isaiah", None, "male", None, None, "Major prophet. Prophesied the coming of the Messiah."),
    ("jeremiah_1", "Jeremiah", None, "male", None, None, "Weeping prophet. Prophesied the Babylonian exile."),
    ("ezekiel_1", "Ezekiel", None, "male", None, None, "Prophet in exile. Saw visions of God's glory."),
    ("daniel_1", "Daniel", None, "male", None, None, "Prophet in Babylon. Interpreted dreams. Survived the lion's den."),
    ("hosea_1", "Hosea", None, "male", None, None, "Prophet who married Gomer. Illustrated God's faithful love."),

    # NT Apostles
    ("peter_1", "Peter", "Simon Peter, Cephas", "male", None, None, "Chief apostle. Fisherman. Confessed Jesus as the Christ."),
    ("andrew_1", "Andrew", None, "male", None, None, "Brother of Peter. First called disciple."),
    ("james_1", "James", "James the Greater, son of Zebedee", "male", None, None, "Apostle. Brother of John. First martyred apostle."),
    ("john_1", "John", "John the Apostle, John the Beloved", "male", None, None, "Apostle. Brother of James. Author of Gospel, Epistles, Revelation."),
    ("paul_1", "Paul", "Saul of Tarsus", "male", None, None, "Apostle to the Gentiles. Author of most NT epistles."),
    ("timothy_1", "Timothy", None, "male", None, None, "Disciple of Paul. Pastor at Ephesus."),
]

# Father-child relationships
FATHER_CHILD = [
    ("adam_1", "seth_1"), ("seth_1", "enosh_1"), ("enosh_1", "kenan_1"),
    ("kenan_1", "mahalalel_1"), ("mahalalel_1", "jared_1"), ("jared_1", "enoch_1"),
    ("enoch_1", "methuselah_1"), ("methuselah_1", "lamech_1"), ("lamech_1", "noah_1"),
    ("noah_1", "shem_1"), ("noah_1", "ham_1"), ("noah_1", "japheth_1"),
    ("shem_1", "arpachshad_1"), ("arpachshad_1", "shelah_1"), ("shelah_1", "eber_1"),
    ("eber_1", "peleg_1"), ("peleg_1", "reu_1"), ("reu_1", "serug_1"),
    ("serug_1", "nahor_1"), ("nahor_1", "terah_1"), ("terah_1", "abraham_1"),
    ("abraham_1", "ishmael_1"), ("abraham_1", "isaac_1"),
    ("isaac_1", "esau_1"), ("isaac_1", "jacob_1"),
    ("jacob_1", "reuben_1"), ("jacob_1", "simeon_1"), ("jacob_1", "levi_1"),
    ("jacob_1", "judah_1"), ("jacob_1", "dan_1"), ("jacob_1", "naphtali_1"),
    ("jacob_1", "gad_1"), ("jacob_1", "asher_1"), ("jacob_1", "issachar_1"),
    ("jacob_1", "zebulun_1"), ("jacob_1", "joseph_1"), ("jacob_1", "benjamin_1"),
    ("jacob_1", "dinah_1"),
    ("judah_1", "perez_1"), ("perez_1", "hezron_1"), ("hezron_1", "ram_1"),
    ("ram_1", "amminadab_1"), ("amminadab_1", "nahshon_1"), ("nahshon_1", "salmon_1"),
    ("salmon_1", "boaz_1"), ("boaz_1", "obed_1"), ("obed_1", "jesse_1"),
    ("jesse_1", "david_1"),
    ("david_1", "solomon_1"), ("solomon_1", "rehoboam_1"), ("rehoboam_1", "abijah_1"),
    ("abijah_1", "asa_1"), ("asa_1", "jehoshaphat_1"), ("jehoshaphat_1", "jehoram_1"),
    ("jehoram_1", "uzziah_1"), ("uzziah_1", "jotham_1"), ("jotham_1", "ahaz_1"),
    ("ahaz_1", "hezekiah_1"), ("hezekiah_1", "manasseh_1"), ("manasseh_1", "amon_1"),
    ("amon_1", "josiah_1"), ("josiah_1", "jeconiah_1"), ("jeconiah_1", "shealtiel_1"),
    ("shealtiel_1", "zerubbabel_1"), ("zerubbabel_1", "abihud_1"),
    ("abihud_1", "eliakim_1"), ("eliakim_1", "azor_1"), ("azor_1", "zadok_1"),
    ("zadok_1", "achim_1"), ("achim_1", "elihud_1"), ("elihud_1", "eleazar_3"),
    ("eleazar_3", "matthan_1"), ("matthan_1", "jacob_2"), ("jacob_2", "joseph_2"),
    ("joseph_2", "jesus_1"), ("david_1", "jonathan_1"), ("saul_1", "jonathan_1"),
    ("jesse_1", "david_1"),
]

MOTHER_CHILD = [
    ("eve_1", "seth_1"), ("sarah_1", "isaac_1"), ("rebekah_1", "esau_1"),
    ("rebekah_1", "jacob_1"), ("leah_1", "reuben_1"), ("leah_1", "simeon_1"),
    ("leah_1", "levi_1"), ("leah_1", "judah_1"), ("leah_1", "issachar_1"),
    ("leah_1", "zebulun_1"), ("leah_1", "dinah_1"), ("rachel_1", "joseph_1"),
    ("rachel_1", "benjamin_1"), ("bilhah_1", "dan_1"), ("bilhah_1", "naphtali_1"),
    ("zilpah_1", "gad_1"), ("zilpah_1", "asher_1"), ("hagar_1", "ishmael_1"),
    ("ruth_1", "obed_1"), ("bathsheba_1", "solomon_1"), ("mary_1", "jesus_1"),
]

SPOUSES = [
    ("adam_1", "eve_1"), ("abraham_1", "sarah_1"), ("isaac_1", "rebekah_1"),
    ("jacob_1", "leah_1"), ("jacob_1", "rachel_1"), ("jacob_1", "bilhah_1"),
    ("jacob_1", "zilpah_1"), ("boaz_1", "ruth_1"), ("david_1", "bathsheba_1"),
    ("joseph_2", "mary_1"),
]


async def main():
    pg = await asyncpg.connect(DB_URL)

    # Clear existing data
    await pg.execute("TRUNCATE graph_people, graph_family_edges, theographic CASCADE")

    # ---- graph_people ----
    print("Populating graph_people...")
    for pid, name, also, gender, birth, death, desc in PEOPLE:
        await pg.execute(
            "INSERT INTO graph_people (id, name, also_called, gender, birth_year, death_year, description) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            pid, name, also, gender, birth, death, desc
        )
    pcount = await pg.fetchval("SELECT COUNT(*) FROM graph_people")
    print(f"  {pcount} people")

    # ---- graph_family_edges ----
    print("Populating graph_family_edges...")
    for father, child in FATHER_CHILD:
        await pg.execute(
            "INSERT INTO graph_family_edges (from_person_id, to_person_id, relationship_type) "
            "VALUES ($1, $2, 'father')", father, child
        )
    for mother, child in MOTHER_CHILD:
        await pg.execute(
            "INSERT INTO graph_family_edges (from_person_id, to_person_id, relationship_type) "
            "VALUES ($1, $2, 'mother')", mother, child
        )
    for a, b in SPOUSES:
        await pg.execute(
            "INSERT INTO graph_family_edges (from_person_id, to_person_id, relationship_type) "
            "VALUES ($1, $2, 'spouse')", a, b
        )
        await pg.execute(
            "INSERT INTO graph_family_edges (from_person_id, to_person_id, relationship_type) "
            "VALUES ($2, $1, 'spouse')", a, b
        )
    ecount = await pg.fetchval("SELECT COUNT(*) FROM graph_family_edges")
    print(f"  {ecount} relationships")

    # ---- theographic ----
    print("Populating theographic...")
    for pid, name, also, gender, birth, death, desc in PEOPLE:
        family = {"parents": [], "children": [], "spouses": [], "siblings": []}

        # Parents
        parents = await pg.fetch(
            "SELECT from_person_id FROM graph_family_edges "
            "WHERE to_person_id = $1 AND relationship_type IN ('father', 'mother')", pid
        )
        for p in parents:
            pname = await pg.fetchval("SELECT name FROM graph_people WHERE id = $1", p["from_person_id"])
            if pname:
                family["parents"].append(pname)

        # Children
        children = await pg.fetch(
            "SELECT to_person_id FROM graph_family_edges "
            "WHERE from_person_id = $1 AND relationship_type IN ('father', 'mother')", pid
        )
        for c in children:
            cname = await pg.fetchval("SELECT name FROM graph_people WHERE id = $1", c["to_person_id"])
            if cname:
                family["children"].append(cname)

        # Spouses
        sps = await pg.fetch(
            "SELECT to_person_id FROM graph_family_edges "
            "WHERE from_person_id = $1 AND relationship_type = 'spouse'", pid
        )
        for s in sps:
            sname = await pg.fetchval("SELECT name FROM graph_people WHERE id = $1", s["to_person_id"])
            if sname:
                family["spouses"].append(sname)

        alt_names = [also] if also else []
        await pg.execute(
            "INSERT INTO theographic (entity_id, entity_type, name, alternate_names, description, family_connections) "
            "VALUES ($1, 'person', $2, $3::jsonb, $4, $5::jsonb)",
            pid, name, json.dumps(alt_names), desc, json.dumps(family)
        )
    tcount = await pg.fetchval("SELECT COUNT(*) FROM theographic")
    print(f"  {tcount} entities")

    # ---- theographic_relations ----
    print("Creating theographic_relations...")
    await pg.execute("DROP TABLE IF EXISTS theographic_relations")
    await pg.execute("""
        CREATE TABLE theographic_relations (
            id SERIAL PRIMARY KEY,
            person_name TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            related_name TEXT NOT NULL,
            relationship TEXT
        )
    """)

    for pid, name, also, gender, birth, death, desc in PEOPLE:
        # Ancestors
        parents = await pg.fetch(
            "SELECT gp.name, gfe.relationship_type FROM graph_family_edges gfe "
            "JOIN graph_people gp ON gfe.from_person_id = gp.id "
            "WHERE gfe.to_person_id = $1 AND gfe.relationship_type IN ('father', 'mother')", pid
        )
        for p in parents:
            await pg.execute(
                "INSERT INTO theographic_relations (person_name, relation_type, related_name, relationship) "
                "VALUES ($1, 'ancestors', $2, $3)", name, p["name"], p["relationship_type"]
            )

        # Descendants
        children = await pg.fetch(
            "SELECT gp.name, gfe.relationship_type FROM graph_family_edges gfe "
            "JOIN graph_people gp ON gfe.to_person_id = gp.id "
            "WHERE gfe.from_person_id = $1 AND gfe.relationship_type IN ('father', 'mother')", pid
        )
        for c in children:
            await pg.execute(
                "INSERT INTO theographic_relations (person_name, relation_type, related_name, relationship) "
                "VALUES ($1, 'descendants', $2, $3)", name, c["name"], c["relationship_type"]
            )

        # Siblings
        for father, child in FATHER_CHILD:
            if child == pid:
                siblings = [c for f, c in FATHER_CHILD if f == father and c != pid]
                for sib in siblings:
                    sib_name = await pg.fetchval("SELECT name FROM graph_people WHERE id = $1", sib)
                    if sib_name:
                        await pg.execute(
                            "INSERT INTO theographic_relations (person_name, relation_type, related_name, relationship) "
                            "VALUES ($1, 'siblings', $2, 'brother')", name, sib_name
                        )

    rcount = await pg.fetchval("SELECT COUNT(*) FROM theographic_relations")
    print(f"  {rcount} relations")

    # Summary
    print(f"\n{'='*50}")
    print("Genealogy Import Complete")
    print(f"  People:            {pcount}")
    print(f"  Family edges:      {ecount}")
    print(f"  Theographic:       {tcount}")
    print(f"  Relations table:   {rcount}")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
