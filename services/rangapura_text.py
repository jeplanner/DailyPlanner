"""
Rangapura Vihara — Muthuswami Dikshitar, raga Brindavana Saranga.
As rendered by M.S. Subbulakshmi.

Text preserved exactly as provided by the user, including the sangati
repetitions natural to a Carnatic rendition. If corrections are needed
later, edit this file — nothing else holds the text.
"""

# Each tuple: (section_label, [line, line, ...])
SECTIONS = [
    ("Pallavi", [
        "Sriranga mangala nidim karuna nivasam",
        "Sri venkataadri sikarlaya kala mekam",
        "Sri hasthisaila sikarrojvala parijatham",
        "Ragnapure vihara",
        "Sri rangapaura vihara",
        "Jaya kodanda ramavathara raghuveera",
        "Sri rangapura vihara",
        "Jaya kodanda ramavathara raghuvira",
    ]),
    ("Anupallavi", [
        "Angaja janaka deva",
        "Angaja janaka deva",
        "Brindavana saragendra",
        "Varada ramanta ranga",
        "Angaja janaka deva",
        "Brindavana sarangendra",
        "Varada ramanta ranga",
        "Shymalanga vihanga turanga",
        "Sadayapanga sastanga",
        "Rangapura vihara",
        "Shymalanga vihanga turanga",
        "Sadayapanga satsanga",
        "Rangapura vihara",
        "Jaya kodanada rama vathara raghuveera",
    ]),
    ("Charanam", [
        "Pankarajapta kula jalanidi soma",
        "Pankarajapta kula jalanidi soma vara",
        "Pankaja mukha pattabhi rama",
        "Pankajapatka kula jalanidhi soma vara",
        "Pankaja mukha pattabhi rama",
        "Pada pankaja jita kama raghurama",
        "Vamanka gata sitavara vesha",
        "Shesanka shayana bhakta santosa",
        "Enahnka ravi nayana mruduthara bhasa",
        "Akalan darpana kapola visesa muni",
        "Sankata harana govindha",
        "Venkata ramana mukundha",
        "Sankat harana govindha",
        "Venkata ramana mukundha",
        "Sankat harana govindha",
        "Venkata ramana mukundha",
        "Sankarshana mula kanda",
        "Rangapura Vihara",
        "Jaya kodanda ramavthara raghuveera",
        "Rangahpura Vihara",
        "Sri rangapura vihara",
        "Jaya kodanda ramavthara raghuvira",
        "Sri rangapura vihara",
    ]),
]


def get_sections():
    return [{"label": lbl, "lines": lines} for lbl, lines in SECTIONS]
