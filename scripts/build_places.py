#!/usr/bin/env python3
"""
Build biblical geography dataset and populate graph_places, 
graph_verse_mentions, and graph_event_place_edges tables.

Curated from biblical references: cities, regions, mountains, rivers,
seas, valleys, and other geographic features.

Usage:
  python3 scripts/build_places.py
"""

import asyncio
import os

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# Format: (id, name, lat, lon, feature_type, [(verse_ref), ...])
# Verse refs use OSIS format: "Gen 1:1"

PLACES = [
    # =========================================================================
    # Cities & Settlements
    # =========================================================================
    ("jerusalem_1", "Jerusalem", 31.7683, 35.2137, "city", [
        "Gen 14:18", "2Sa 5:5", "1Ki 8:1", "2Ki 25:9", "Ezr 1:2",
        "Neh 2:17", "Psa 122:3", "Isa 52:1", "Jer 3:17", "Ezk 5:5",
        "Zec 8:3", "Mat 21:10", "Luk 2:22", "Jhn 5:1", "Act 1:4",
        "Gal 4:25", "Rev 21:2"
    ]),
    ("bethlehem_1", "Bethlehem", 31.7041, 35.2058, "city", [
        "Gen 35:19", "Rut 1:1", "1Sa 16:1", "Mic 5:2",
        "Mat 2:1", "Luk 2:4", "Jhn 7:42"
    ]),
    ("nazareth_1", "Nazareth", 32.6996, 35.3035, "city", [
        "Mat 2:23", "Mar 1:9", "Luk 1:26", "Luk 4:16", "Jhn 1:46", "Act 10:38"
    ]),
    ("capernaum_1", "Capernaum", 32.8803, 35.5733, "city", [
        "Mat 4:13", "Mat 8:5", "Mar 1:21", "Luk 4:31", "Jhn 6:59"
    ]),
    ("jericho_1", "Jericho", 31.8572, 35.4444, "city", [
        "Jos 2:1", "Jos 6:1", "2Ki 2:4", "Mat 20:29", "Luk 10:30", "Luk 19:1", "Heb 11:30"
    ]),
    ("hebron_1", "Hebron", 31.5326, 35.0998, "city", [
        "Gen 13:18", "Gen 23:2", "Jos 14:13", "2Sa 2:1", "2Sa 5:3"
    ]),
    ("shechem_1", "Shechem", 32.2148, 35.2817, "city", [
        "Gen 12:6", "Gen 33:18", "Jos 24:1", "Jdg 9:1", "1Ki 12:1", "Jhn 4:5"
    ]),
    ("samaria_1", "Samaria", 32.2767, 35.1900, "city", [
        "1Ki 16:24", "2Ki 17:5", "Isa 7:9", "Hos 7:1", "Amo 3:9", "Act 8:5"
    ]),
    ("dan_1_city", "Dan (city)", 33.2484, 35.6527, "city", [
        "Jdg 18:29", "1Ki 12:29", "Jer 4:15"
    ]),
    ("beersheba_1", "Beersheba", 31.2518, 34.7913, "city", [
        "Gen 21:31", "Gen 26:33", "1Sa 8:2", "1Ki 19:3", "Amo 5:5"
    ]),
    ("bethel_1", "Bethel", 31.9417, 35.2365, "city", [
        "Gen 12:8", "Gen 28:19", "Jdg 20:18", "1Ki 12:29", "Amo 7:13"
    ]),
    ("shiloh_1", "Shiloh", 32.0556, 35.2894, "city", [
        "Jos 18:1", "1Sa 1:3", "1Sa 4:3", "Jer 7:12"
    ]),
    ("gibeah_1", "Gibeah", 31.8235, 35.2311, "city", [
        "Jdg 19:12", "1Sa 10:26", "1Sa 15:34", "Isa 10:29"
    ]),
    ("ai_1", "Ai", 31.9169, 35.2614, "city", [
        "Gen 12:8", "Jos 7:2", "Jos 8:1", "Ezr 2:28"
    ]),
    ("gibeon_1", "Gibeon", 31.8474, 35.1844, "city", [
        "Jos 9:3", "2Sa 2:12", "1Ki 3:4"
    ]),
    ("megiddo_1", "Megiddo", 32.5853, 35.1844, "city", [
        "Jos 12:21", "Jdg 5:19", "2Ki 23:29", "Rev 16:16"
    ]),
    ("hazor_1", "Hazor", 33.0172, 35.5683, "city", [
        "Jos 11:1", "Jdg 4:2", "1Ki 9:15"
    ]),
    ("gezer_1", "Gezer", 31.8756, 34.9200, "city", [
        "Jos 10:33", "1Ki 9:16"
    ]),
    ("lachish_1", "Lachish", 31.5647, 34.8499, "city", [
        "Jos 10:3", "2Ki 18:14", "Jer 34:7"
    ]),
    ("sodom_1", "Sodom", 31.2000, 35.5000, "city", [
        "Gen 13:10", "Gen 19:1", "Deu 29:23", "Isa 1:9", "Luk 17:29", "Jud 1:7"
    ]),
    ("gomorrah_1", "Gomorrah", 31.1800, 35.5200, "city", [
        "Gen 19:24", "Deu 29:23", "Mat 10:15", "2Pe 2:6"
    ]),
    ("tyre_1", "Tyre", 33.2700, 35.1950, "city", [
        "1Ki 5:1", "Isa 23:1", "Ezk 26:3", "Mat 11:21", "Act 21:3"
    ]),
    ("sidon_1", "Sidon", 33.5600, 35.3750, "city", [
        "Gen 10:15", "Jdg 10:6", "1Ki 16:31", "Mat 11:22", "Act 27:3"
    ]),
    ("damascus_1", "Damascus", 33.5138, 36.2765, "city", [
        "Gen 14:15", "2Ki 16:9", "Isa 7:8", "Act 9:2", "2Co 11:32"
    ]),
    ("babylon_1", "Babylon", 32.5361, 44.4208, "city", [
        "Gen 11:9", "2Ki 24:1", "Psa 137:1", "Isa 13:1", "Jer 50:1",
        "Dan 1:1", "1Pe 5:13", "Rev 14:8", "Rev 18:2"
    ]),
    ("nineveh_1", "Nineveh", 36.3594, 43.1528, "city", [
        "Gen 10:11", "2Ki 19:36", "Jon 1:2", "Nah 1:1", "Mat 12:41"
    ]),
    ("ur_1", "Ur of the Chaldeans", 30.9623, 46.1031, "city", [
        "Gen 11:28", "Gen 15:7", "Neh 9:7"
    ]),
    ("haran_1", "Haran", 36.8628, 39.0305, "city", [
        "Gen 11:31", "Gen 12:4", "2Ki 19:12", "Ezk 27:23"
    ]),
    ("susa_1", "Susa", 32.1892, 48.2579, "city", [
        "Neh 1:1", "Est 1:2", "Dan 8:2"
    ]),
    ("ephesus_1", "Ephesus", 37.9397, 27.3409, "city", [
        "Act 18:19", "Act 19:1", "1Co 15:32", "Eph 1:1", "1Ti 1:3", "Rev 2:1"
    ]),
    ("corinth_1", "Corinth", 37.9390, 22.9328, "city", [
        "Act 18:1", "1Co 1:2", "2Co 1:1"
    ]),
    ("athens_1", "Athens", 37.9838, 23.7275, "city", [
        "Act 17:15", "1Th 3:1"
    ]),
    ("rome_1", "Rome", 41.9028, 12.4964, "city", [
        "Act 2:10", "Act 19:21", "Act 28:14", "Rom 1:7", "2Ti 1:17"
    ]),
    ("antioch_1", "Antioch (Syria)", 36.2021, 36.1623, "city", [
        "Act 11:26", "Act 13:1", "Gal 2:11"
    ]),
    ("philippi_1", "Philippi", 41.0130, 24.2866, "city", [
        "Act 16:12", "Php 1:1", "1Th 2:2"
    ]),
    ("thessalonica_1", "Thessalonica", 40.6401, 22.9444, "city", [
        "Act 17:1", "1Th 1:1", "2Th 1:1"
    ]),
    ("colossae_1", "Colossae", 37.7862, 29.2600, "city", [
        "Col 1:2"
    ]),
    ("laodicea_1", "Laodicea", 37.8364, 29.1075, "city", [
        "Col 2:1", "Col 4:16", "Rev 3:14"
    ]),
    ("sardis_1", "Sardis", 38.4883, 28.0403, "city", [
        "Rev 3:1"
    ]),
    ("philadelphia_1_bib", "Philadelphia (Asia Minor)", 38.3497, 28.5183, "city", [
        "Rev 3:7"
    ]),
    ("pergamum_1", "Pergamum", 39.1325, 27.1842, "city", [
        "Rev 2:12"
    ]),
    ("thyatira_1", "Thyatira", 38.9206, 27.8361, "city", [
        "Act 16:14", "Rev 2:18"
    ]),
    ("smyrna_1", "Smyrna", 38.4192, 27.1387, "city", [
        "Rev 2:8"
    ]),
    ("tarsus_1", "Tarsus", 36.9167, 34.9000, "city", [
        "Act 9:11", "Act 21:39"
    ]),
    ("joppa_1", "Joppa", 32.0517, 34.7520, "city", [
        "Jos 19:46", "Jon 1:3", "Act 9:36", "Act 10:5"
    ]),
    ("caesarea_1", "Caesarea Maritima", 32.5017, 34.8917, "city", [
        "Act 8:40", "Act 10:1", "Act 23:23"
    ]),
    ("bethany_1", "Bethany", 31.7709, 35.2695, "city", [
        "Mat 21:17", "Mar 11:1", "Jhn 11:1", "Jhn 12:1"
    ]),
    ("emmaus_1", "Emmaus", 31.8300, 35.0600, "city", [
        "Luk 24:13"
    ]),
    ("gaza_1", "Gaza", 31.5000, 34.4667, "city", [
        "Gen 10:19", "Jdg 16:1", "Act 8:26"
    ]),
    ("ekron_1", "Ekron", 31.7767, 34.8500, "city", [
        "Jos 13:3", "1Sa 5:10", "2Ki 1:2"
    ]),
    ("ashdod_1", "Ashdod", 31.8044, 34.6553, "city", [
        "Jos 11:22", "1Sa 5:1", "Act 8:40"
    ]),
    ("ashkelon_1", "Ashkelon", 31.6689, 34.5744, "city", [
        "Jdg 1:18", "Jer 47:5", "Zep 2:4"
    ]),
    ("gath_1", "Gath", 31.7000, 34.8500, "city", [
        "Jos 11:22", "1Sa 5:8", "1Sa 17:4", "2Ki 12:17"
    ]),
    ("ramah_1", "Ramah", 31.8514, 35.2313, "city", [
        "Jdg 4:5", "1Sa 7:17", "Jer 31:15", "Mat 2:18"
    ]),
    ("mizpah_1", "Mizpah", 31.8286, 35.2200, "city", [
        "Gen 31:49", "Jdg 20:1", "1Sa 7:5", "Jer 40:6"
    ]),
    ("peniel_1", "Peniel", 32.1833, 35.7000, "city", [
        "Gen 32:30", "Jdg 8:8"
    ]),
    ("succoth_1", "Succoth", 32.3000, 35.5333, "city", [
        "Gen 33:17", "Jos 13:27", "Jdg 8:5"
    ]),
    ("kedesh_1", "Kedesh", 33.1136, 35.5333, "city", [
        "Jos 12:22", "Jos 20:7", "Jdg 4:6"
    ]),

    # =========================================================================
    # Regions & Territories
    # =========================================================================
    ("galilee_1", "Galilee", 32.7500, 35.4000, "region", [
        "Jos 20:7", "Isa 9:1", "Mat 4:15", "Mar 1:9", "Luk 2:39", "Jhn 7:1"
    ]),
    ("judea_1", "Judea", 31.5000, 35.1000, "region", [
        "Ezr 5:8", "Mat 2:1", "Luk 1:5", "Jhn 3:22", "Act 1:8"
    ]),
    ("samaria_region", "Samaria (region)", 32.2000, 35.2000, "region", [
        "1Ki 13:32", "2Ki 17:24", "Luk 17:11", "Jhn 4:4", "Act 8:1"
    ]),
    ("perea_1", "Perea", 31.8000, 35.7000, "region", [
        "Mat 19:1", "Mar 10:1", "Jhn 1:28", "Jhn 10:40"
    ]),
    ("decapolis_1", "Decapolis", 32.6000, 35.8000, "region", [
        "Mat 4:25", "Mar 5:20", "Mar 7:31"
    ]),
    ("bashan_1", "Bashan", 32.8000, 35.9000, "region", [
        "Num 21:33", "Deu 3:1", "Psa 22:12", "Ezk 39:18"
    ]),
    ("gilead_1", "Gilead", 32.2000, 35.8000, "region", [
        "Gen 31:21", "Num 32:1", "Jdg 10:8", "Jer 8:22"
    ]),
    ("moab_1", "Moab", 31.5000, 35.8000, "region", [
        "Gen 19:37", "Num 22:1", "Rut 1:1", "Isa 15:1", "Jer 48:1"
    ]),
    ("edom_1", "Edom", 30.0000, 35.0000, "region", [
        "Gen 25:30", "Num 20:14", "Oba 1:1", "Mal 1:4"
    ]),
    ("ammon_1", "Ammon", 31.9000, 35.9000, "region", [
        "Gen 19:38", "Deu 2:19", "Jer 49:1"
    ]),
    ("philistia_1", "Philistia", 31.5000, 34.5000, "region", [
        "Gen 21:32", "Exo 15:14", "Isa 14:29", "Joe 3:4"
    ]),
    ("canaan_1", "Canaan", 31.5000, 34.9000, "region", [
        "Gen 12:5", "Exo 6:4", "Jos 1:2", "Act 7:11"
    ]),
    ("mesopotamia_1", "Mesopotamia", 34.0000, 43.0000, "region", [
        "Gen 24:10", "Deu 23:4", "Jdg 3:8", "Act 2:9"
    ]),
    ("egypt_1", "Egypt", 26.0000, 30.0000, "region", [
        "Gen 12:10", "Exo 1:1", "Num 20:15", "Isa 19:1", "Mat 2:13", "Heb 11:27"
    ]),
    ("macedonia_1", "Macedonia", 41.0000, 22.0000, "region", [
        "Act 16:9", "Act 20:1", "2Co 8:1", "1Th 4:10"
    ]),
    ("achaia_1", "Achaia", 38.0000, 22.0000, "region", [
        "Act 18:12", "Rom 15:26", "1Co 16:15", "2Co 1:1"
    ]),
    ("asia_1_region", "Asia (Roman province)", 39.0000, 28.0000, "region", [
        "Act 2:9", "Act 16:6", "1Co 16:19", "Rev 1:4"
    ]),
    ("cyprus_1", "Cyprus", 35.0000, 33.0000, "region", [
        "Act 4:36", "Act 13:4", "Act 15:39"
    ]),
    ("crete_1", "Crete", 35.2000, 24.8000, "region", [
        "Act 27:7", "Tit 1:5"
    ]),

    # =========================================================================
    # Mountains & Hills
    # =========================================================================
    ("sinai_1", "Mount Sinai / Horeb", 28.5394, 33.9744, "mountain", [
        "Exo 3:1", "Exo 19:2", "Exo 24:16", "1Ki 19:8", "Gal 4:25"
    ]),
    ("zion_1", "Mount Zion", 31.7717, 35.2289, "mountain", [
        "2Sa 5:7", "Psa 48:2", "Isa 2:3", "Heb 12:22", "Rev 14:1"
    ]),
    ("olives_1", "Mount of Olives", 31.7784, 35.2439, "mountain", [
        "2Sa 15:30", "Zec 14:4", "Mat 21:1", "Mat 24:3", "Luk 22:39", "Act 1:12"
    ]),
    ("moriah_1", "Mount Moriah", 31.7781, 35.2354, "mountain", [
        "Gen 22:2", "2Ch 3:1"
    ]),
    ("carmel_1", "Mount Carmel", 32.7333, 35.0500, "mountain", [
        "1Ki 18:19", "2Ki 2:25", "Isa 35:2"
    ]),
    ("gerizim_1", "Mount Gerizim", 32.2000, 35.2733, "mountain", [
        "Deu 11:29", "Jos 8:33", "Jdg 9:7", "Jhn 4:20"
    ]),
    ("ebal_1", "Mount Ebal", 32.2350, 35.2800, "mountain", [
        "Deu 11:29", "Jos 8:30"
    ]),
    ("hermon_1", "Mount Hermon", 33.4167, 35.8500, "mountain", [
        "Deu 3:8", "Jos 13:11", "Psa 133:3"
    ]),
    ("tabor_1", "Mount Tabor", 32.6867, 35.3928, "mountain", [
        "Jdg 4:6", "Psa 89:12", "Jer 46:18"
    ]),
    ("nebo_1", "Mount Nebo", 31.7678, 35.7256, "mountain", [
        "Num 27:12", "Deu 32:49", "Deu 34:1"
    ]),
    ("ararat_1", "Mount Ararat", 39.7000, 44.3000, "mountain", [
        "Gen 8:4"
    ]),
    ("gilboa_1", "Mount Gilboa", 32.4833, 35.4167, "mountain", [
        "1Sa 28:4", "1Sa 31:1", "2Sa 1:6"
    ]),

    # =========================================================================
    # Rivers & Seas
    # =========================================================================
    ("jordan_1", "Jordan River", 31.8000, 35.5500, "river", [
        "Gen 13:10", "Jos 3:1", "2Ki 2:13", "Mat 3:6", "Mar 1:5", "Jhn 1:28"
    ]),
    ("euphrates_1", "Euphrates River", 33.0000, 44.0000, "river", [
        "Gen 2:14", "Gen 15:18", "Jos 1:4", "Jer 46:10", "Rev 9:14"
    ]),
    ("tigris_1", "Tigris River", 34.0000, 44.0000, "river", [
        "Gen 2:14", "Dan 10:4"
    ]),
    ("nile_1", "Nile River", 30.0000, 31.0000, "river", [
        "Gen 41:1", "Exo 1:22", "Isa 19:5", "Ezk 29:3"
    ]),
    ("dead_sea_1", "Dead Sea / Salt Sea", 31.5000, 35.5000, "sea", [
        "Gen 14:3", "Num 34:3", "Jos 3:16", "Ezk 47:8"
    ]),
    ("galilee_sea_1", "Sea of Galilee", 32.8000, 35.6000, "sea", [
        "Num 34:11", "Mat 4:18", "Mar 1:16", "Luk 5:1", "Jhn 6:1"
    ]),
    ("mediterranean_1", "Mediterranean Sea / Great Sea", 33.0000, 31.0000, "sea", [
        "Num 34:6", "Jos 1:4", "Jon 1:3", "Act 27:1"
    ]),
    ("red_sea_1", "Red Sea / Sea of Reeds", 24.0000, 35.0000, "sea", [
        "Exo 13:18", "Exo 14:21", "Jos 2:10", "Isa 51:10", "Heb 11:29"
    ]),
    ("kedron_1", "Kidron Brook", 31.7750, 35.2380, "river", [
        "2Sa 15:23", "1Ki 15:13", "Jhn 18:1"
    ]),
    ("jabbok_1", "Jabbok River", 32.3000, 35.7000, "river", [
        "Gen 32:22", "Num 21:24", "Jos 12:2"
    ]),

    # =========================================================================
    # Valleys & Plains
    # =========================================================================
    ("jezreel_1", "Valley of Jezreel", 32.5500, 35.3000, "valley", [
        "Jos 17:16", "Jdg 6:33", "Hos 1:5"
    ]),
    ("hinnom_1", "Valley of Hinnom / Gehenna", 31.7680, 35.2250, "valley", [
        "Jos 15:8", "Jer 7:31", "Mat 5:22", "Mar 9:43"
    ]),
    ("jehoshaphat_1", "Valley of Jehoshaphat", 31.7760, 35.2380, "valley", [
        "Joe 3:2", "Joe 3:12"
    ]),
    ("mamre_1", "Oaks of Mamre", 31.5560, 35.1030, "site", [
        "Gen 13:18", "Gen 18:1", "Gen 23:17"
    ]),
    ("machpelah_1", "Cave of Machpelah", 31.5247, 35.1106, "site", [
        "Gen 23:9", "Gen 25:9", "Gen 49:30"
    ]),
    ("golgotha_1", "Golgotha / Calvary", 31.7785, 35.2300, "site", [
        "Mat 27:33", "Mar 15:22", "Luk 23:33", "Jhn 19:17"
    ]),
    ("gethsemane_1", "Garden of Gethsemane", 31.7794, 35.2397, "site", [
        "Mat 26:36", "Mar 14:32", "Jhn 18:1"
    ]),
    ("silwan_1", "Pool of Siloam", 31.7700, 35.2350, "site", [
        "Jhn 9:7"
    ]),
    ("bethesda_1", "Pool of Bethesda", 31.7810, 35.2360, "site", [
        "Jhn 5:2"
    ]),
    ("salem_1", "Salem", 31.7683, 35.2137, "city", [
        "Gen 14:18", "Psa 76:2"
    ]),
    ("sharon_1", "Plain of Sharon", 32.3000, 34.9000, "valley", [
        "Isa 35:2", "Act 9:35"
    ]),
]


async def main():
    pg = await asyncpg.connect(DB_URL)

    # Clear existing
    await pg.execute("TRUNCATE graph_places, graph_verse_mentions RESTART IDENTITY")

    place_count = 0
    mention_count = 0

    for (pid, name, lat, lon, ftype, verses) in PLACES:
        await pg.execute(
            """INSERT INTO graph_places (id, name, latitude, longitude, feature_type)
               VALUES ($1, $2, $3, $4, $5)""",
            pid, name, lat, lon, ftype
        )
        place_count += 1

        for ref in verses:
            await pg.execute(
                """INSERT INTO graph_verse_mentions (verse_ref, entity_type, entity_id)
                   VALUES ($1, 'place', $2)""",
                ref, pid
            )
            mention_count += 1

    # Summary
    pcount = await pg.fetchval("SELECT COUNT(*) FROM graph_places")
    mcount = await pg.fetchval("SELECT COUNT(*) FROM graph_verse_mentions")

    # Feature type breakdown
    print(f"\n{'='*50}")
    print("Biblical Places Import Complete")
    print(f"  Places:    {pcount}")
    print(f"  Mentions:  {mcount}")
    print(f"\n  Feature types:")
    types = await pg.fetch(
        "SELECT feature_type, COUNT(*) as cnt FROM graph_places "
        "GROUP BY feature_type ORDER BY cnt DESC"
    )
    for row in types:
        print(f"    {row['feature_type']:15s} {row['cnt']}")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
