# -*- coding: utf-8 -*-
"""カラー定数"""

COL = dict(
    NAVY="1E3A5F", WHITE="FFFFFF", GOLD="FFD700",
    G1_BG="8B0000", G2_BG="00008B", G3_BG="006400",
    OP_BG="4A4A4A", COND_BG="2E4E7E",
    HONMEI="FF5252", TAIKOU="FF9800", ANA="4CAF50",
    CHUUI="2196F3", KESHI="9E9E9E",
    PENDING="FFF9C4", NEW_F="E8F4FD", OLD_F="F0F8E8",
    ROW_ODD="FFFFFF", ROW_EVEN="F8F9FA",
    NAKAYAMA="E3F2FD", HANSHIN="FFF3E0", FUKUSHIMA="F3E5F5",
    ALERT="FFEBEE", GOOD="E8F5E9",
)

GRADE_COLOR = {
    "G1": COL["G1_BG"], "G2": COL["G2_BG"], "G3": COL["G3_BG"],
    "OP": COL["OP_BG"],
    "3勝": "2F4F4F", "2勝": "3D5A80", "1勝": "5E6472",
    "未勝利": "7B7B7B", "新馬": "8B4513",
}

VENUE_BG   = {"中山": COL["NAKAYAMA"], "阪神": COL["HANSHIN"], "福島": COL["FUKUSHIMA"]}
VENUE_DARK = {"中山": "0D47A1",        "阪神": "E65100",        "福島": "6A1B9A"}

SHIRUSHI_COLOR = {
    "◎": COL["HONMEI"], "○": COL["TAIKOU"],
    "▲": COL["ANA"],    "△": COL["CHUUI"],
    "—": COL["KESHI"],
}

SHIRUSHI_ESTBG = {
    "◎": "FFCDD2", "○": "FFE0B2", "▲": "DCEDC8",
    "△": "BBDEFB", "—": "F5F5F5",
}
