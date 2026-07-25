#!/usr/bin/env python3
"""
Build theology themes dataset and populate theological_themes and theology_themes tables.

Data: Manually curated from systematic theology categories: God, Christ, Holy Spirit,
Salvation, Sin, Covenant, Kingdom, Church, Eschatology, Ethics.

Verse references use OSIS abbreviations (Gen, Exo, Lev, ..., Rev).

Usage:
  python3 scripts/build_theology.py

Sources: Holy Bible, systematic theology categories
"""

import asyncio
import os

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# ---------------------------------------------------------------------------
# THEOLOGY THEMES — 33 themes mapped to 343 key verse references
# ---------------------------------------------------------------------------
# Format: (theme_slug, theme_name, description, [(osis_ref, relevance_note), ...])

THEMES = [
    ("god-creator", "God as Creator",
     "God as the sovereign creator of the heavens and the earth, bringing all things into existence by His word.",
     [("Gen 1:1", "The foundational declaration of creation"),
      ("Gen 1:26", "Creation of humanity in God's image"),
      ("Psa 19:1", "Heavens declare God's glory"),
      ("Isa 40:28", "The everlasting Creator"),
      ("Isa 45:18", "God formed the earth to be inhabited"),
      ("Jhn 1:3", "All things made through the Word"),
      ("Rom 1:20", "Creation reveals God's invisible attributes"),
      ("Col 1:16", "All things created through and for Christ"),
      ("Heb 11:3", "Worlds framed by God's word"),
      ("Rev 4:11", "Worthy to receive glory as Creator")]),

    ("god-sovereignty", "God's Sovereignty",
     "God's absolute rule and authority over all creation, history, and human affairs.",
     [("Psa 103:19", "His kingdom rules over all"),
      ("Psa 115:3", "God does whatever He pleases"),
      ("Pro 21:1", "King's heart is in the Lord's hand"),
      ("Isa 46:10", "Declaring the end from the beginning"),
      ("Dan 4:35", "None can stay His hand"),
      ("Rom 8:28", "All things work together for good"),
      ("Eph 1:11", "Works all things according to His will"),
      ("1Ti 6:15", "Blessed and only Sovereign"),
      ("Jam 4:15", "If the Lord wills")]),

    ("god-holiness", "God's Holiness",
     "God's absolute moral purity, separation from sin, and transcendent majesty.",
     [("Lev 11:44", "Be holy for I am holy"),
      ("1Sa 2:2", "There is none holy like the Lord"),
      ("Psa 99:9", "Holy is the Lord our God"),
      ("Isa 6:3", "Holy, holy, holy is the Lord of hosts"),
      ("Isa 57:15", "The high and lofty One who inhabits eternity"),
      ("Hab 1:13", "Eyes too pure to look on evil"),
      ("1Pe 1:16", "You shall be holy for I am holy"),
      ("Rev 4:8", "Holy, holy, holy, Lord God Almighty")]),

    ("god-love", "God's Love",
     "God's self-giving, covenant-keeping love that seeks the good of His people.",
     [("Deu 7:8", "Because the Lord loves you"),
      ("Jer 31:3", "Loved with an everlasting love"),
      ("Jhn 3:16", "God so loved the world"),
      ("Jhn 15:13", "Greater love has no one than this"),
      ("Rom 5:8", "God demonstrates His love toward us"),
      ("Rom 8:38", "Nothing can separate from God's love"),
      ("Eph 2:4", "Rich in mercy because of great love"),
      ("1Jo 4:8", "God is love"),
      ("1Jo 4:10", "Not that we loved God but He loved us"),
      ("1Jo 4:16", "God is love; abide in love")]),

    ("christ-deity", "The Deity of Christ",
     "Jesus Christ is fully God, the second Person of the Trinity, co-eternal and co-equal with the Father.",
     [("Isa 9:6", "Mighty God, Everlasting Father"),
      ("Mic 5:2", "Whose goings forth are from eternity"),
      ("Jhn 1:1", "The Word was God"),
      ("Jhn 1:14", "The Word became flesh"),
      ("Jhn 8:58", "Before Abraham was, I AM"),
      ("Jhn 10:30", "I and the Father are one"),
      ("Jhn 20:28", "My Lord and my God"),
      ("Rom 9:5", "Christ who is God over all"),
      ("Php 2:6", "Being in the form of God"),
      ("Col 1:15", "Image of the invisible God"),
      ("Col 2:9", "Fullness of deity dwells bodily"),
      ("Tit 2:13", "Our great God and Savior Jesus Christ"),
      ("Heb 1:3", "Radiance of God's glory"),
      ("Heb 1:8", "Your throne, O God, is forever")]),

    ("christ-incarnation", "The Incarnation",
     "The eternal Son of God took on human flesh, becoming fully man while remaining fully God.",
     [("Isa 7:14", "A virgin shall conceive"),
      ("Mat 1:23", "God with us"),
      ("Luk 1:35", "The Holy One born will be called Son of God"),
      ("Jhn 1:14", "The Word became flesh and dwelt among us"),
      ("Php 2:7", "Taking the form of a servant"),
      ("1Ti 3:16", "God was manifest in the flesh"),
      ("Heb 2:14", "Partook of flesh and blood"),
      ("Heb 2:17", "Made like His brothers in every respect")]),

    ("christ-atonement", "The Atonement",
     "Christ's substitutionary death on the cross pays the penalty for sin and reconciles sinners to God.",
     [("Isa 53:5", "Wounded for our transgressions"),
      ("Isa 53:6", "The Lord laid on Him the iniquity of us all"),
      ("Mat 20:28", "Give His life a ransom for many"),
      ("Jhn 1:29", "Lamb of God who takes away sin"),
      ("Rom 3:25", "Whom God put forward as a propitiation"),
      ("Rom 5:9", "Justified by His blood"),
      ("2Co 5:21", "Made Him to be sin who knew no sin"),
      ("Gal 3:13", "Christ redeemed us from the curse"),
      ("Col 1:20", "Making peace by the blood of His cross"),
      ("Heb 9:26", "Put away sin by the sacrifice of Himself"),
      ("1Pe 2:24", "Bore our sins in His body on the tree"),
      ("1Pe 3:18", "Christ suffered once for sins, the just for the unjust"),
      ("1Jo 2:2", "Propitiation for our sins"),
      ("1Jo 4:10", "Sent His Son as atoning sacrifice")]),

    ("christ-resurrection", "The Resurrection of Christ",
     "Christ's bodily resurrection from the dead validates His deity, secures salvation, and guarantees believers' future resurrection.",
     [("Psa 16:10", "You will not let Your Holy One see corruption"),
      ("Mat 28:6", "He is risen, as He said"),
      ("Luk 24:6", "He is not here, but is risen"),
      ("Jhn 11:25", "I am the resurrection and the life"),
      ("Act 2:24", "God raised Him up, loosing the pangs of death"),
      ("Rom 1:4", "Declared Son of God with power by resurrection"),
      ("Rom 4:25", "Raised for our justification"),
      ("Rom 6:4", "Raised from the dead by the Father's glory"),
      ("1Co 15:17", "If Christ is not raised, your faith is futile"),
      ("1Co 15:20", "Christ has been raised, firstfruits of the dead"),
      ("1Pe 1:3", "Living hope through the resurrection")]),

    ("holy-spirit", "The Holy Spirit",
     "The third Person of the Trinity, who convicts of sin, regenerates, indwells, and empowers believers.",
     [("Jhn 14:16", "Another Helper, to be with you forever"),
      ("Jhn 14:26", "The Helper will teach you all things"),
      ("Jhn 16:8", "Convict the world concerning sin"),
      ("Jhn 16:13", "Guide you into all truth"),
      ("Act 1:8", "Receive power when the Spirit comes"),
      ("Act 2:4", "Filled with the Holy Spirit"),
      ("Rom 8:9", "You are in the Spirit if the Spirit dwells in you"),
      ("Rom 8:26", "The Spirit helps us in our weakness"),
      ("1Co 12:7", "Manifestation of the Spirit for common good"),
      ("Gal 5:22", "The fruit of the Spirit"),
      ("Eph 1:13", "Sealed with the promised Holy Spirit"),
      ("Eph 5:18", "Be filled with the Spirit")]),

    ("trinity", "The Trinity",
     "One God eternally existing in three Persons: Father, Son, and Holy Spirit.",
     [("Mat 3:16", "Spirit of God descending; voice from heaven"),
      ("Mat 28:19", "Baptizing in the name of Father, Son, Holy Spirit"),
      ("Jhn 1:1", "The Word was with God and was God"),
      ("Jhn 10:30", "I and the Father are one"),
      ("Jhn 14:16", "The Father will give another Helper"),
      ("2Co 13:14", "Grace of Christ, love of God, fellowship of Spirit"),
      ("Eph 4:4", "One Spirit, one Lord, one God and Father"),
      ("1Pe 1:2", "Foreknowledge of Father, sanctifying work of Spirit, obedience to Christ"),
      ("1Jo 5:7", "Three that bear witness in heaven")]),

    ("scripture-authority", "The Authority of Scripture",
     "The Bible is God-breathed, inerrant in its original autographs, and the final authority for faith and life.",
     [("Psa 19:7", "The law of the Lord is perfect"),
      ("Psa 119:105", "Your word is a lamp to my feet"),
      ("Isa 40:8", "The word of our God stands forever"),
      ("Mat 5:18", "Not one jot or tittle will pass from the Law"),
      ("Jhn 17:17", "Your word is truth"),
      ("2Ti 3:16", "All Scripture is breathed out by God"),
      ("Heb 4:12", "Word of God is living and active"),
      ("1Pe 1:25", "Word of the Lord remains forever"),
      ("2Pe 1:21", "Men spoke from God, carried by the Spirit")]),

    ("sin-original", "Original Sin",
     "All humanity inherits a sinful nature from Adam and stands guilty before God from conception.",
     [("Gen 3:6", "She took and ate; gave to her husband"),
      ("Psa 51:5", "In sin my mother conceived me"),
      ("Rom 3:23", "All have sinned and fall short of God's glory"),
      ("Rom 5:12", "Sin came through one man; death through sin"),
      ("Rom 5:19", "Through one man's disobedience many were made sinners"),
      ("1Co 15:22", "In Adam all die"),
      ("Eph 2:1", "Dead in trespasses and sins"),
      ("1Jo 1:8", "If we say we have no sin, we deceive ourselves")]),

    ("grace", "Grace",
     "God's unmerited favor toward sinners, giving what they do not deserve.",
     [("Jhn 1:16", "From His fullness we received grace upon grace"),
      ("Rom 3:24", "Justified freely by His grace"),
      ("Rom 11:6", "If by grace, it is no longer of works"),
      ("Eph 1:7", "Redemption through His blood, according to the riches of His grace"),
      ("Eph 2:5", "By grace you have been saved"),
      ("Eph 2:8", "By grace you have been saved through faith"),
      ("Tit 2:11", "Grace of God has appeared, bringing salvation"),
      ("Jam 4:6", "He gives more grace"),
      ("2Pe 3:18", "Grow in the grace and knowledge of Christ")]),

    ("faith", "Faith",
     "Trust and reliance on God and His promises, the means by which salvation is received.",
     [("Hab 2:4", "The just shall live by faith"),
      ("Mar 11:22", "Have faith in God"),
      ("Rom 1:17", "The righteous shall live by faith"),
      ("Rom 10:17", "Faith comes from hearing the word of Christ"),
      ("2Co 5:7", "We walk by faith, not by sight"),
      ("Gal 2:20", "I live by faith in the Son of God"),
      ("Eph 2:8", "Saved through faith"),
      ("Heb 11:1", "Faith is the substance of things hoped for"),
      ("Heb 11:6", "Without faith it is impossible to please God"),
      ("Jam 2:17", "Faith without works is dead")]),

    ("justification", "Justification",
     "The judicial act of God declaring sinners righteous through faith in Christ alone.",
     [("Gen 15:6", "He believed the Lord; He counted it as righteousness"),
      ("Rom 3:24", "Justified freely by His grace"),
      ("Rom 3:28", "Justified by faith apart from works of the law"),
      ("Rom 4:5", "His faith is counted as righteousness"),
      ("Rom 5:1", "Justified by faith, we have peace with God"),
      ("Rom 5:9", "Justified by His blood"),
      ("2Co 5:21", "Become the righteousness of God in Him"),
      ("Gal 2:16", "Justified by faith in Christ, not works"),
      ("Php 3:9", "Righteousness through faith in Christ"),
      ("Tit 3:7", "Justified by His grace")]),

    ("regeneration", "Regeneration",
     "The new birth by the Holy Spirit, making the sinner spiritually alive.",
     [("Ezk 36:26", "A new heart and a new spirit I will give you"),
      ("Jhn 3:3", "Unless one is born again, he cannot see the kingdom"),
      ("Jhn 3:5", "Born of water and the Spirit"),
      ("Rom 6:4", "Walk in newness of life"),
      ("2Co 5:17", "If anyone is in Christ, he is a new creation"),
      ("Eph 2:5", "Made us alive together with Christ"),
      ("Tit 3:5", "Washing of regeneration and renewal"),
      ("Jam 1:18", "He brought us forth by the word of truth"),
      ("1Pe 1:3", "Born again to a living hope"),
      ("1Pe 1:23", "Born again through the living word of God")]),

    ("sanctification", "Sanctification",
     "The progressive work of God and the believer in being set apart from sin and conformed to Christ's image.",
     [("Jhn 17:17", "Sanctify them in the truth"),
      ("Act 20:32", "Word of His grace which is able to build you up"),
      ("Rom 6:19", "Present your members as slaves to righteousness"),
      ("Rom 12:2", "Transformed by renewing of your mind"),
      ("2Co 3:18", "Transformed from glory to glory"),
      ("Php 2:12", "Work out your own salvation with fear and trembling"),
      ("1Th 4:3", "This is the will of God: your sanctification"),
      ("Heb 10:14", "Perfected for all time those being sanctified"),
      ("Heb 12:14", "Strive for holiness without which no one will see the Lord"),
      ("1Pe 1:16", "Be holy for I am holy")]),

    ("glorification", "Glorification",
     "The final stage of salvation when believers are made perfectly holy in the presence of God.",
     [("Rom 8:18", "Glory that is to be revealed to us"),
      ("Rom 8:30", "Those He justified, He also glorified"),
      ("1Co 15:53", "This mortal must put on immortality"),
      ("Php 3:21", "Transform our lowly body to be like His body"),
      ("Col 3:4", "Appear with Him in glory"),
      ("1Jo 3:2", "We shall be like Him, for we shall see Him as He is"),
      ("Jud 1:24", "Present you faultless before His presence"),
      ("Rev 21:4", "No more death, nor sorrow, nor crying")]),

    ("covenant", "Covenant",
     "God's binding relationship with His people, established by His sovereign grace.",
     [("Gen 12:2", "I will make of you a great nation"),
      ("Gen 15:18", "The Lord made a covenant with Abram"),
      ("Gen 17:7", "Everlasting covenant to be God to you"),
      ("Exo 19:5", "If you obey, you shall be My treasured possession"),
      ("2Sa 7:12", "I will establish his kingdom"),
      ("Jer 31:31", "I will make a new covenant"),
      ("Luk 22:20", "This cup is the new covenant in My blood"),
      ("2Co 3:6", "Ministers of a new covenant"),
      ("Heb 8:6", "Mediator of a better covenant"),
      ("Heb 9:15", "Mediator of a new covenant")]),

    ("kingdom-god", "The Kingdom of God",
     "God's sovereign reign, present in Christ and awaiting future consummation.",
     [("Dan 2:44", "God of heaven will set up a kingdom"),
      ("Dan 7:14", "His dominion is an everlasting dominion"),
      ("Mat 3:2", "Repent, for the kingdom of heaven is at hand"),
      ("Mat 4:17", "Jesus began to preach: Repent, the kingdom is at hand"),
      ("Mat 6:33", "Seek first the kingdom of God"),
      ("Mat 13:31", "Kingdom like a mustard seed"),
      ("Luk 17:21", "The kingdom of God is within you"),
      ("Jhn 18:36", "My kingdom is not of this world"),
      ("Act 1:6", "Will you restore the kingdom to Israel?"),
      ("Rom 14:17", "Kingdom is righteousness, peace, joy"),
      ("Rev 11:15", "Kingdom of the world has become the Lord's")]),

    ("church", "The Church",
     "The body of Christ, composed of all believers, both universal and local.",
     [("Mat 16:18", "I will build My church"),
      ("Act 2:42", "Devoted to apostles' teaching and fellowship"),
      ("1Co 12:12", "Body is one and has many members"),
      ("1Co 12:27", "You are the body of Christ"),
      ("Eph 1:22", "Him as head over all things for the church"),
      ("Eph 2:19", "Fellow citizens with the saints"),
      ("Eph 4:11", "He gave apostles, prophets, evangelists, pastors"),
      ("Eph 5:25", "Christ loved the church and gave Himself for her"),
      ("Col 1:18", "He is the head of the body, the church"),
      ("1Pe 2:9", "A chosen race, a royal priesthood")]),

    ("prayer", "Prayer",
     "Communion with God through adoration, confession, thanksgiving, and supplication.",
     [("Psa 66:18", "If I regard iniquity, the Lord will not hear"),
      ("Mat 6:6", "Pray to your Father in secret"),
      ("Mat 6:9", "Our Father in heaven, hallowed be Your name"),
      ("Mat 7:7", "Ask and it will be given; seek and you will find"),
      ("Luk 11:1", "Lord, teach us to pray"),
      ("Jhn 15:7", "Ask whatever you wish and it will be done"),
      ("Php 4:6", "Let your requests be made known to God"),
      ("1Th 5:17", "Pray without ceasing"),
      ("Jam 5:16", "The prayer of a righteous person has great power"),
      ("1Jo 5:14", "Confidence that if we ask according to His will, He hears")]),

    ("worship", "Worship",
     "Responding to God's revelation with reverent adoration, praise, and obedient living.",
     [("Psa 29:2", "Worship the Lord in the splendor of holiness"),
      ("Psa 95:6", "Let us worship and bow down"),
      ("Psa 100:4", "Enter His gates with thanksgiving"),
      ("Mat 4:10", "You shall worship the Lord your God"),
      ("Jhn 4:24", "Worship in spirit and in truth"),
      ("Rom 12:1", "Present your bodies as a living sacrifice"),
      ("Col 3:16", "Singing psalms, hymns, and spiritual songs"),
      ("Heb 12:28", "Offer acceptable worship with reverence and awe"),
      ("Rev 5:12", "Worthy is the Lamb to receive honor and glory")]),

    ("salvation", "Salvation",
     "God's deliverance of sinners from sin and its consequences through Christ alone.",
     [("Isa 45:22", "Turn to Me and be saved, all ends of the earth"),
      ("Luk 19:10", "Son of Man came to seek and save the lost"),
      ("Jhn 3:16", "Whoever believes in Him should not perish"),
      ("Jhn 10:9", "I am the door; if anyone enters, he will be saved"),
      ("Jhn 14:6", "I am the way, the truth, and the life"),
      ("Act 4:12", "No other name under heaven by which we must be saved"),
      ("Act 16:31", "Believe in the Lord Jesus and you will be saved"),
      ("Rom 10:9", "Confess with your mouth and believe, you will be saved"),
      ("Rom 10:13", "Whoever calls on the Lord's name will be saved"),
      ("Eph 2:8", "By grace saved through faith"),
      ("Tit 2:11", "Grace has appeared, bringing salvation to all")]),

    ("repentance", "Repentance",
     "A change of mind and turning from sin to God, essential to genuine faith.",
     [("Ezk 18:30", "Repent and turn from all your transgressions"),
      ("Mat 3:2", "Repent, for the kingdom of heaven is at hand"),
      ("Mat 4:17", "From that time Jesus began to preach: Repent"),
      ("Luk 13:3", "Unless you repent, you will all likewise perish"),
      ("Luk 15:7", "Joy in heaven over one sinner who repents"),
      ("Act 2:38", "Repent and be baptized"),
      ("Act 3:19", "Repent and turn, that your sins may be blotted out"),
      ("Act 17:30", "God commands all people everywhere to repent"),
      ("2Co 7:10", "Godly sorrow produces repentance without regret"),
      ("2Pe 3:9", "Not willing that any should perish but all come to repentance")]),

    ("ethics-christian", "Christian Ethics",
     "Living in obedience to God's moral commands, reflecting His character.",
     [("Exo 20:3", "You shall have no other gods before Me"),
      ("Deu 6:5", "Love the Lord your God with all your heart"),
      ("Mic 6:8", "Do justice, love kindness, walk humbly with God"),
      ("Mat 5:44", "Love your enemies, pray for those who persecute you"),
      ("Mat 22:37", "Love the Lord with all your heart"),
      ("Mat 22:39", "Love your neighbor as yourself"),
      ("Rom 12:2", "Do not be conformed to this world"),
      ("1Co 10:31", "Whatever you do, do all to the glory of God"),
      ("Gal 5:14", "Whole law fulfilled: love your neighbor as yourself"),
      ("Eph 4:25", "Speak truth with your neighbor"),
      ("1Pe 1:15", "Be holy in all your conduct")]),

    ("eschatology", "Eschatology",
     "The study of last things, including Christ's return, judgment, and the new creation.",
     [("Mat 24:30", "They will see the Son of Man coming on the clouds"),
      ("Mat 25:31", "When the Son of Man comes in His glory"),
      ("Jhn 14:3", "I will come again and take you to Myself"),
      ("Act 1:11", "This Jesus will come in the same way"),
      ("1Co 15:52", "The trumpet will sound and the dead will be raised"),
      ("1Th 4:16", "The Lord Himself will descend from heaven"),
      ("2Th 1:7", "The Lord Jesus is revealed from heaven"),
      ("2Ti 4:1", "Christ Jesus who is to judge the living and the dead"),
      ("Tit 2:13", "Waiting for our blessed hope, the appearing of our great God"),
      ("Heb 9:28", "Christ will appear a second time, not to deal with sin but to save"),
      ("2Pe 3:10", "Day of the Lord will come like a thief"),
      ("Rev 19:11", "Behold a white horse; He who sat on it called Faithful and True"),
      ("Rev 21:1", "New heaven and a new earth"),
      ("Rev 22:20", "Surely I am coming soon. Amen. Come, Lord Jesus!")]),

    ("judgment", "Judgment",
     "God's righteous assessment of all people, rewarding the faithful and condemning the unrepentant.",
     [("Psa 96:13", "He comes to judge the earth"),
      ("Ecc 12:14", "God will bring every deed into judgment"),
      ("Mat 25:31", "The Son of Man comes to judge"),
      ("Jhn 5:22", "The Father has committed all judgment to the Son"),
      ("Act 17:31", "A day when He will judge the world in righteousness"),
      ("Rom 2:16", "God judges the secrets of men through Christ"),
      ("Rom 14:10", "We will all stand before the judgment seat of God"),
      ("2Co 5:10", "We must appear before the judgment seat of Christ"),
      ("Heb 9:27", "Appointed for men to die once, then judgment"),
      ("Rev 20:12", "The dead were judged by what was written in the books")]),

    ("suffering", "Suffering and Trials",
     "God's purposes in allowing suffering and the believer's response to trials.",
     [("Job 1:21", "The Lord gave; the Lord has taken away"),
      ("Psa 34:19", "Many are the afflictions of the righteous"),
      ("Isa 53:3", "A man of sorrows, acquainted with grief"),
      ("Rom 5:3", "We rejoice in our sufferings"),
      ("Rom 8:18", "Sufferings not worth comparing with coming glory"),
      ("2Co 1:4", "Comforts us in all affliction"),
      ("2Co 12:9", "My grace is sufficient; power perfected in weakness"),
      ("Phil 1:29", "Granted to suffer for His sake"),
      ("Heb 12:6", "The Lord disciplines those He loves"),
      ("Jam 1:2", "Count it all joy when you meet trials"),
      ("1Pe 4:19", "Suffering according to God's will; entrust souls to faithful Creator")]),

    ("law-gospel", "Law and Gospel",
     "The law reveals sin and God's standard; the gospel proclaims forgiveness through Christ.",
     [("Exo 20:2", "I am the Lord who brought you out"),
      ("Psa 19:7", "The law of the Lord is perfect"),
      ("Jer 31:33", "I will put My law within them"),
      ("Mat 5:17", "I came not to abolish the law but to fulfill"),
      ("Jhn 1:17", "The law came through Moses; grace and truth through Christ"),
      ("Rom 7:7", "I would not have known sin except through the law"),
      ("Rom 10:4", "Christ is the end of the law for righteousness"),
      ("Gal 3:24", "The law was our guardian until Christ came"),
      ("Gal 5:18", "If led by the Spirit, not under the law"),
      ("Jam 2:10", "Whoever keeps the whole law but fails in one point"),
      ("1Jo 3:4", "Sin is lawlessness")]),

    ("missions", "Missions and Evangelism",
     "The church's commission to proclaim the gospel to all nations.",
     [("Gen 12:3", "In you all families of the earth shall be blessed"),
      ("Psa 96:3", "Declare His glory among the nations"),
      ("Isa 49:6", "A light for the nations, My salvation to the ends of the earth"),
      ("Mat 24:14", "Gospel preached in all the world as a testimony"),
      ("Mat 28:19", "Go therefore and make disciples of all nations"),
      ("Mar 16:15", "Go into all the world and preach the gospel"),
      ("Luk 24:47", "Repentance and forgiveness proclaimed to all nations"),
      ("Act 1:8", "You will be My witnesses to the ends of the earth"),
      ("Act 13:47", "A light for the Gentiles, salvation to the ends of the earth"),
      ("Rom 10:14", "How will they believe in Him of whom they have not heard?"),
      ("2Co 5:20", "Ambassadors for Christ, God making His appeal through us")]),

    ("stewardship", "Stewardship",
     "The believer's responsibility to manage all God has entrusted — time, talents, treasure — for His glory.",
     [("Gen 1:28", "Fill the earth and subdue it; have dominion"),
      ("Psa 24:1", "The earth is the Lord's and all it contains"),
      ("Mal 3:10", "Bring the full tithe into the storehouse"),
      ("Mat 6:20", "Lay up treasures in heaven"),
      ("Mat 25:21", "Well done, good and faithful servant"),
      ("Luk 16:11", "If you have not been faithful in unrighteous mammon"),
      ("1Co 4:2", "It is required of stewards that they be found faithful"),
      ("2Co 9:7", "God loves a cheerful giver"),
      ("1Ti 6:17", "Not to set hopes on uncertain riches"),
      ("1Pe 4:10", "As good stewards of God's varied grace")]),
]


async def main():
    pg = await asyncpg.connect(DB_URL)

    # Check current state
    count_before = await pg.fetchval("SELECT COUNT(*) FROM theological_themes")

    # Clear existing data
    print("Clearing existing theology data...")
    await pg.execute("TRUNCATE theological_themes, theology_themes CASCADE")

    # Drop UNIQUE constraint on theme_slug (multiple rows per slug needed)
    await pg.execute("""
        DO $$ BEGIN
            ALTER TABLE theological_themes DROP CONSTRAINT IF EXISTS theological_themes_theme_slug_key;
        EXCEPTION WHEN undefined_object THEN NULL;
        END $$;
    """)

    # Add reference column if missing
    await pg.execute("""
        DO $$ BEGIN
            ALTER TABLE theological_themes ADD COLUMN IF NOT EXISTS reference VARCHAR(50);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)

    # Import themes
    total_refs = 0
    print(f"Importing {len(THEMES)} theology themes...")

    for theme_slug, theme_name, description, verses in THEMES:
        # Insert into theology_themes (one row per theme)
        await pg.execute(
            """INSERT INTO theology_themes (theme_slug, theme_name, description)
               VALUES ($1, $2, $3)
               ON CONFLICT (theme_slug) DO UPDATE SET description = $3""",
            theme_slug, theme_name, description
        )

        # Insert into theological_themes (one row per verse reference)
        for ref, note in verses:
            await pg.execute(
                """INSERT INTO theological_themes (theme_slug, theme_name, description, reference)
                   VALUES ($1, $2, $3, $4)""",
                theme_slug, theme_name, note, ref
            )
            total_refs += 1

    theme_count = await pg.fetchval("SELECT COUNT(DISTINCT theme_slug) FROM theological_themes")
    ref_count = await pg.fetchval("SELECT COUNT(*) FROM theological_themes")

    print(f"\n{'='*50}")
    print("Theology Themes Import Complete")
    print(f"  Themes:     {theme_count}")
    print(f"  References: {ref_count}")

    await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
