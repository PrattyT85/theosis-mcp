#!/usr/bin/env python3
"""
Build biblical events dataset and populate graph_events,
graph_person_event_edges, and graph_event_place_edges.

Curated from Genesis through Revelation — major events with approximate
dates, participating people, and locations.

Usage:
  python3 scripts/build_events.py
"""

import asyncio
import os

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# Format: (id, title, year, duration, sort_key, [person_ids], [place_ids])
# Years are approximate BCE (negative) or CE (positive)
# Person IDs match graph_people (from build_genealogy.py)
# Place IDs match graph_places (from build_places.py)

EVENTS = [
    # =========================================================================
    # Primeval History
    # =========================================================================
    ("creation_1", "Creation", -4000, "6 days", -4000.0,
     ["adam_1", "eve_1"], []),
    ("fall_1", "The Fall of Man", -4000, "1 day", -3999.9,
     ["adam_1", "eve_1"], []),
    ("cain_abel_1", "Cain Murders Abel", -3900, "1 day", -3900.0,
     [], []),
    ("flood_1", "The Great Flood", -2350, "1 year", -2350.0,
     ["noah_1"], []),
    ("babel_1", "Tower of Babel", -2250, "unknown", -2250.0,
     [], []),

    # =========================================================================
    # Patriarchs
    # =========================================================================
    ("call_abraham_1", "Call of Abraham", -1920, "1 day", -1920.0,
     ["abraham_1", "sarah_1", "lot_1"], ["haran_1"]),
    ("covenant_abraham_1", "Abrahamic Covenant", -1910, "1 day", -1910.0,
     ["abraham_1"], []),
    ("sodom_1_event", "Destruction of Sodom and Gomorrah", -1898, "1 day", -1898.0,
     ["abraham_1", "lot_1"], ["sodom_1", "gomorrah_1"]),
    ("isaac_birth_1", "Birth of Isaac", -1892, "1 day", -1892.0,
     ["abraham_1", "sarah_1", "isaac_1"], []),
    ("binding_isaac_1", "Binding of Isaac (Akedah)", -1870, "1 day", -1870.0,
     ["abraham_1", "isaac_1"], ["moriah_1"]),
    ("jacob_ladder_1", "Jacob's Ladder at Bethel", -1760, "1 night", -1760.0,
     ["jacob_1"], ["bethel_1"]),
    ("jacob_wrestling_1", "Jacob Wrestles with God", -1740, "1 night", -1740.0,
     ["jacob_1"], ["peniel_1"]),
    ("joseph_sold_1", "Joseph Sold into Slavery", -1715, "1 day", -1715.0,
     ["joseph_1", "jacob_1"], []),
    ("joseph_egypt_1", "Joseph Rises to Power in Egypt", -1705, "years", -1705.0,
     ["joseph_1"], ["egypt_1"]),

    # =========================================================================
    # Exodus & Wilderness
    # =========================================================================
    ("exodus_birth_1", "Birth of Moses", -1393, "1 day", -1393.0,
     ["moses_1"], ["egypt_1"]),
    ("burning_bush_1", "The Burning Bush", -1313, "1 day", -1313.0,
     ["moses_1"], ["sinai_1"]),
    ("passover_1", "The First Passover", -1313, "1 night", -1312.9,
     ["moses_1", "aaron_1"], ["egypt_1"]),
    ("exodus_1", "The Exodus from Egypt", -1313, "1 day", -1312.8,
     ["moses_1", "aaron_1", "miriam_1"], ["red_sea_1", "egypt_1"]),
    ("sinai_covenant_1", "Giving of the Law at Sinai", -1312, "40 days", -1312.0,
     ["moses_1", "aaron_1"], ["sinai_1"]),
    ("golden_calf_1", "The Golden Calf", -1312, "1 day", -1311.9,
     ["moses_1", "aaron_1"], ["sinai_1"]),
    ("tabernacle_1", "Construction of the Tabernacle", -1312, "~6 months", -1311.0,
     ["moses_1", "aaron_1"], ["sinai_1"]),
    ("spies_1", "The Twelve Spies", -1310, "40 days", -1310.0,
     ["moses_1", "joshua_1"], ["canaan_1"]),
    ("serpent_1", "The Bronze Serpent", -1270, "1 day", -1270.0,
     ["moses_1"], []),

    # =========================================================================
    # Conquest & Judges
    # =========================================================================
    ("jordan_crossing_1", "Crossing the Jordan", -1273, "1 day", -1273.0,
     ["joshua_1"], ["jordan_1"]),
    ("jericho_1_event", "Fall of Jericho", -1273, "7 days", -1272.9,
     ["joshua_1"], ["jericho_1"]),
    ("sun_stands_still_1", "The Sun Stands Still", -1270, "1 day", -1270.0,
     ["joshua_1"], ["gibeon_1"]),
    ("deborah_1", "Deborah and Barak Defeat Sisera", -1150, "1 day", -1150.0,
     [], ["megiddo_1"]),
    ("gideon_1", "Gideon's 300 Defeat Midian", -1100, "1 night", -1100.0,
     [], ["jezreel_1"]),
    ("samson_1", "Samson Destroys the Philistine Temple", -1050, "1 day", -1050.0,
     [], ["gaza_1"]),
    ("ruth_1_event", "Ruth and Boaz", -1120, "months", -1120.0,
     ["boaz_1", "ruth_1"], ["bethlehem_1"]),

    # =========================================================================
    # United Monarchy
    # =========================================================================
    ("samuel_call_1", "God Calls Samuel", -1060, "1 night", -1060.0,
     ["samuel_1", "eli_1"], ["shiloh_1"]),
    ("saul_anointed_1", "Saul Anointed King", -1020, "1 day", -1020.0,
     ["samuel_1", "saul_1"], []),
    ("david_goliath_1", "David and Goliath", -1015, "1 day", -1015.0,
     ["david_1", "saul_1"], ["gath_1"]),
    ("david_king_1", "David Anointed King over Israel", -1000, "1 day", -1000.0,
     ["david_1", "samuel_1"], ["hebron_1"]),
    ("jerusalem_captured_1", "David Captures Jerusalem", -995, "1 day", -995.0,
     ["david_1"], ["jerusalem_1", "zion_1"]),
    ("ark_returned_1", "The Ark Brought to Jerusalem", -994, "1 day", -994.0,
     ["david_1"], ["jerusalem_1"]),
    ("david_bathsheba_1", "David and Bathsheba", -980, "months", -980.0,
     ["david_1", "bathsheba_1"], ["jerusalem_1"]),
    ("solomon_temple_1", "Solomon Builds the Temple", -960, "7 years", -960.0,
     ["solomon_1"], ["jerusalem_1", "moriah_1"]),

    # =========================================================================
    # Divided Kingdom & Exile
    # =========================================================================
    ("kingdom_divided_1", "The Kingdom Divides", -931, "1 day", -931.0,
     ["rehoboam_1"], ["shechem_1", "jerusalem_1"]),
    ("elijah_carmel_1", "Elijah on Mount Carmel", -860, "1 day", -860.0,
     ["elijah_1"], ["carmel_1"]),
    ("elijah_chariot_1", "Elijah Taken to Heaven", -850, "1 day", -850.0,
     ["elijah_1", "elisha_1"], ["jordan_1"]),
    ("isaiah_vision_1", "Isaiah's Temple Vision", -740, "1 day", -740.0,
     ["isaiah_1"], ["jerusalem_1"]),
    ("hezekiah_1_event", "Hezekiah's Prayer and Deliverance", -701, "1 night", -701.0,
     ["hezekiah_1", "isaiah_1"], ["jerusalem_1"]),
    ("josiah_reform_1", "Josiah's Reformation", -622, "months", -622.0,
     ["josiah_1"], ["jerusalem_1"]),
    ("jeremiah_call_1", "Call of Jeremiah", -627, "1 day", -627.0,
     ["jeremiah_1"], []),
    ("temple_destroyed_1", "Destruction of the First Temple", -586, "1 day", -586.0,
     ["jeremiah_1"], ["jerusalem_1", "babylon_1"]),
    ("ezekiel_valley_1", "Ezekiel's Vision of Dry Bones", -575, "1 day", -575.0,
     ["ezekiel_1"], ["babylon_1"]),
    ("daniel_lion_1", "Daniel in the Lion's Den", -535, "1 night", -535.0,
     ["daniel_1"], ["babylon_1"]),
    ("return_exile_1", "Return from Exile", -538, "months", -538.0,
     ["zerubbabel_1"], ["jerusalem_1", "babylon_1"]),
    ("temple_rebuilt_1", "Second Temple Completed", -516, "years", -516.0,
     ["zerubbabel_1"], ["jerusalem_1"]),
    ("esther_1_event", "Esther Saves the Jews", -475, "days", -475.0,
     [], ["susa_1"]),
    ("nehemiah_wall_1", "Nehemiah Rebuilds the Wall", -445, "52 days", -445.0,
     [], ["jerusalem_1"]),

    # =========================================================================
    # Life of Christ
    # =========================================================================
    ("annunciation_1", "The Annunciation to Mary", -1, "1 day", -1.0,
     ["mary_1"], ["nazareth_1"]),
    ("jesus_birth_1", "Birth of Jesus", -4, "1 day", -4.0,
     ["jesus_1", "mary_1", "joseph_2"], ["bethlehem_1"]),
    ("temple_presentation_1", "Presentation at the Temple", -4, "1 day", -3.9,
     ["jesus_1", "mary_1", "joseph_2"], ["jerusalem_1"]),
    ("baptism_jesus_1", "Baptism of Jesus", 26, "1 day", 26.0,
     ["jesus_1", "john_baptist_1"], ["jordan_1"]),
    ("temptation_1", "Temptation of Jesus", 26, "40 days", 26.1,
     ["jesus_1"], []),
    ("sermon_mount_1", "Sermon on the Mount", 28, "1 day", 28.0,
     ["jesus_1"], ["galilee_1"]),
    ("transfiguration_1", "The Transfiguration", 29, "1 day", 29.0,
     ["jesus_1", "peter_1", "james_1", "john_1"], ["tabor_1"]),
    ("triumphal_entry_1", "Triumphal Entry", 30, "1 day", 30.0,
     ["jesus_1"], ["jerusalem_1", "olives_1"]),
    ("last_supper_1", "The Last Supper", 30, "1 evening", 30.1,
     ["jesus_1", "peter_1", "john_1"], ["jerusalem_1"]),
    ("gethsemane_1", "Agony in Gethsemane", 30, "1 night", 30.2,
     ["jesus_1", "peter_1", "james_1", "john_1"], ["gethsemane_1"]),
    ("crucifixion_1", "The Crucifixion", 30, "1 day", 30.3,
     ["jesus_1", "mary_1", "john_1"], ["golgotha_1", "jerusalem_1"]),
    ("resurrection_1", "The Resurrection", 30, "1 morning", 30.4,
     ["jesus_1", "mary_1", "peter_1", "john_1"], ["jerusalem_1"]),
    ("ascension_1", "The Ascension", 30, "1 day", 30.5,
     ["jesus_1"], ["olives_1"]),

    # =========================================================================
    # Early Church
    # =========================================================================
    ("pentecost_1", "Pentecost — Coming of the Holy Spirit", 30, "1 day", 30.6,
     ["peter_1", "john_1"], ["jerusalem_1"]),
    ("stephen_1", "Stoning of Stephen", 34, "1 day", 34.0,
     [], ["jerusalem_1"]),
    ("paul_conversion_1", "Conversion of Saul/Paul", 34, "1 day", 34.1,
     ["paul_1"], ["damascus_1"]),
    ("peter_cornelius_1", "Peter's Vision and Cornelius", 40, "1 day", 40.0,
     ["peter_1"], ["caesarea_1", "joppa_1"]),
    ("paul_barnabas_1", "Paul and Barnabas Sent from Antioch", 46, "1 day", 46.0,
     ["paul_1"], ["antioch_1"]),
    ("jerusalem_council_1", "The Jerusalem Council", 49, "days", 49.0,
     ["peter_1", "paul_1", "james_1"], ["jerusalem_1"]),
    ("macedonian_call_1", "The Macedonian Call", 50, "1 night", 50.0,
     ["paul_1", "timothy_1"], ["macedonia_1"]),
    ("philippi_jail_1", "Paul and Silas in Prison at Philippi", 50, "1 night", 50.1,
     ["paul_1"], ["philippi_1"]),
    ("athens_areopagus_1", "Paul at the Areopagus", 51, "1 day", 51.0,
     ["paul_1"], ["athens_1"]),
    ("ephesus_riot_1", "The Riot at Ephesus", 55, "1 day", 55.0,
     ["paul_1"], ["ephesus_1"]),
    ("paul_arrested_1", "Paul Arrested in Jerusalem", 57, "1 day", 57.0,
     ["paul_1"], ["jerusalem_1"]),
    ("paul_shipwreck_1", "Paul Shipwrecked on Malta", 59, "14 days", 59.0,
     ["paul_1"], ["mediterranean_1"]),
    ("paul_rome_1", "Paul Arrives in Rome", 60, "1 day", 60.0,
     ["paul_1"], ["rome_1"]),
    ("john_patmos_1", "John's Vision on Patmos", 95, "1 day", 95.0,
     ["john_1"], []),
]


async def main():
    pg = await asyncpg.connect(DB_URL)

    # Clear existing
    await pg.execute(
        "TRUNCATE graph_events, graph_person_event_edges, "
        "graph_event_place_edges RESTART IDENTITY"
    )

    event_count = 0
    person_edge_count = 0
    place_edge_count = 0

    for (eid, title, year, duration, sort_key, people, places) in EVENTS:
        await pg.execute(
            """INSERT INTO graph_events (id, title, start_year, duration, sort_key)
               VALUES ($1, $2, $3, $4, $5)""",
            eid, title, year, duration, sort_key
        )
        event_count += 1

        for pid in people:
            await pg.execute(
                "INSERT INTO graph_person_event_edges (person_id, event_id) "
                "VALUES ($1, $2)",
                pid, eid
            )
            person_edge_count += 1

        for lid in places:
            await pg.execute(
                "INSERT INTO graph_event_place_edges (event_id, place_id) "
                "VALUES ($1, $2)",
                eid, lid
            )
            place_edge_count += 1

    # Summary
    print(f"\n{'='*50}")
    print("Biblical Events Import Complete")
    print(f"  Events:              {event_count}")
    print(f"  Person→Event edges:  {person_edge_count}")
    print(f"  Event→Place edges:   {place_edge_count}")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
