"""Major Chinese listed companies, plus what is known about how each sells in the US.

Two kinds of data live here and they must not be confused with each other:

* Everything in `US_EXPOSURE` is **hand-curated and dated**. It is not fetched, it
  does not update nightly, and it reflects public reporting as of the
  CURATED_AS_OF date below. Each entry carries a `confidence`.
* Everything else about a company — financials, prices, the US-market beta — is
  computed from live data at build time.

The page keeps them visually separate for the same reason. A regulatory status
that is eighteen months stale is worse than no status at all if the reader
cannot tell which is which.

Access ratings:
    blocked     — effectively cannot sell its main product to US customers
    restricted  — sells, but under sanctions, export controls or a US ban
    tariffed    — sells into the US, materially exposed to tariff policy
    open        — sells into the US on ordinary commercial terms
    domestic    — essentially no US-facing business; exposure is indirect
"""

from dataclasses import dataclass, field

CURATED_AS_OF = "2026-05"


@dataclass(frozen=True)
class Co:
    ticker: str
    name: str
    sector: str
    adr: str = ""          # US-listed line, if one exists
    tags: tuple = field(default_factory=tuple)


SECTORS = {
    "auto": "Automotive & EV",
    "tech": "Internet & AI",
    "semis": "Semiconductors & Hardware",
    "consumer": "Consumer & Retail",
    "finance": "Financials & Fintech",
    "industrial": "Industrial & Energy",
}

UNIVERSE: list[Co] = [
    # ---- Automotive & EV ----
    Co("1211.HK", "BYD", "auto", tags=("ev", "battery")),
    Co("0175.HK", "Geely Automobile", "auto", tags=("oem",)),
    Co("2015.HK", "Li Auto", "auto", adr="LI", tags=("ev",)),
    Co("9868.HK", "XPeng", "auto", adr="XPEV", tags=("ev",)),
    Co("9866.HK", "NIO", "auto", adr="NIO", tags=("ev",)),
    Co("2333.HK", "Great Wall Motor", "auto", tags=("oem",)),
    Co("2238.HK", "GAC Group", "auto", tags=("oem",)),
    Co("9863.HK", "Leapmotor", "auto", tags=("ev",)),
    Co("3750.HK", "CATL", "auto", tags=("battery",)),
    Co("2338.HK", "Weichai Power", "auto", tags=("powertrain",)),

    # ---- Internet & AI ----
    Co("0700.HK", "Tencent", "tech", tags=("platform", "games")),
    Co("9988.HK", "Alibaba", "tech", adr="BABA", tags=("platform", "cloud")),
    Co("3690.HK", "Meituan", "tech", tags=("platform",)),
    Co("9618.HK", "JD.com", "tech", adr="JD", tags=("ecommerce",)),
    Co("9888.HK", "Baidu", "tech", adr="BIDU", tags=("ai", "search")),
    Co("1024.HK", "Kuaishou", "tech", tags=("video",)),
    Co("0020.HK", "SenseTime", "tech", tags=("ai",)),
    Co("9660.HK", "Horizon Robotics", "tech", tags=("ai", "chips")),
    Co("6682.HK", "4Paradigm", "tech", tags=("ai",)),
    Co("0268.HK", "Kingdee International", "tech", tags=("software",)),
    Co("3888.HK", "Kingsoft", "tech", tags=("software",)),
    Co("KC", "Kingsoft Cloud", "tech", tags=("cloud",)),
    Co("PDD", "PDD Holdings (Temu)", "tech", tags=("ecommerce",)),
    Co("TCOM", "Trip.com", "tech", tags=("travel",)),
    Co("BILI", "Bilibili", "tech", tags=("video",)),
    Co("NTES", "NetEase", "tech", tags=("games",)),

    # ---- Semiconductors & Hardware ----
    Co("0981.HK", "SMIC", "semis", tags=("foundry",)),
    Co("1347.HK", "Hua Hong Semiconductor", "semis", tags=("foundry",)),
    Co("0522.HK", "ASMPT", "semis", tags=("equipment",)),
    Co("1385.HK", "Shanghai Fudan Micro", "semis", tags=("design",)),
    Co("2382.HK", "Sunny Optical", "semis", tags=("optics",)),
    Co("2018.HK", "AAC Technologies", "semis", tags=("acoustics",)),
    Co("1478.HK", "Q Technology", "semis", tags=("camera",)),
    Co("6088.HK", "FIT Hon Teng", "semis", tags=("connectors",)),
    Co("0285.HK", "BYD Electronic", "semis", tags=("ems",)),
    Co("1810.HK", "Xiaomi", "semis", tags=("phones", "ev")),
    Co("0992.HK", "Lenovo", "semis", tags=("pc", "phones")),
    Co("0763.HK", "ZTE", "semis", tags=("telecom",)),
    Co("1415.HK", "Cowell e Holdings", "semis", tags=("camera",)),

    # ---- Consumer & Retail ----
    Co("9633.HK", "Nongfu Spring", "consumer", tags=("beverages",)),
    Co("2020.HK", "Anta Sports", "consumer", tags=("apparel",)),
    Co("2331.HK", "Li Ning", "consumer", tags=("apparel",)),
    Co("1928.HK", "Sands China", "consumer", tags=("gaming",)),
    Co("YUMC", "Yum China", "consumer", tags=("restaurants",)),
    Co("6862.HK", "Haidilao", "consumer", tags=("restaurants",)),
    Co("0322.HK", "Tingyi", "consumer", tags=("food",)),
    Co("2313.HK", "Shenzhou International", "consumer", tags=("apparel", "oem")),
    Co("1044.HK", "Hengan International", "consumer", tags=("household",)),

    # ---- Financials & Fintech ----
    Co("2318.HK", "Ping An Insurance", "finance", tags=("insurance",)),
    Co("3968.HK", "China Merchants Bank", "finance", tags=("bank",)),
    Co("1398.HK", "ICBC", "finance", tags=("bank",)),
    Co("0388.HK", "HKEX", "finance", tags=("exchange",)),
    Co("6060.HK", "ZhongAn Online", "finance", tags=("insurtech",)),
    Co("FUTU", "Futu Holdings", "finance", tags=("broker",)),
    Co("QFIN", "Qifu Technology", "finance", tags=("lending",)),
    Co("FINV", "FinVolution", "finance", tags=("lending",)),

    # ---- Industrial & Energy ----
    Co("0857.HK", "PetroChina", "industrial", tags=("energy",)),
    Co("0386.HK", "Sinopec", "industrial", tags=("energy",)),
    Co("1088.HK", "China Shenhua Energy", "industrial", tags=("coal",)),
    Co("0669.HK", "Techtronic Industries", "industrial", tags=("tools",)),
    Co("1919.HK", "COSCO Shipping", "industrial", tags=("shipping",)),
]


# ---------------------------------------------------------------------------
# Curated US exposure. Hand-researched, dated CURATED_AS_OF, not auto-updated.
# `us_revenue_share` is filled only where a company discloses a geographic split
# or it is otherwise well documented — a guess here would be worse than a blank.
# ---------------------------------------------------------------------------

US_EXPOSURE: dict[str, dict] = {
    "1211.HK": dict(
        access="blocked", confidence="high", us_revenue_share=None,
        channel="Electric buses and trucks through BYD North America (Lancaster, "
                "California). No passenger cars sold in the US.",
        policy=["Section 301 tariffs on Chinese EVs raised to 100% in 2024",
                "Effectively shut out of the US passenger-vehicle market"],
        note="BYD's global expansion runs through Europe, Latin America and "
             "Southeast Asia specifically because the US is closed to it."),
    "3750.HK": dict(
        access="restricted", confidence="high", us_revenue_share=None,
        channel="No direct US manufacturing. Licenses LFP battery technology to "
                "Ford for its Michigan plant.",
        policy=["Named on the US Department of Defense Chinese military companies list (Jan 2025)",
                "IRA foreign-entity-of-concern rules limit its batteries qualifying for US credits"],
        note="The Ford licensing structure exists to route around direct-ownership rules."),
    "2015.HK": dict(access="blocked", confidence="high", us_revenue_share=0.0,
        channel="No US sales. Sells in mainland China with early moves into the Middle East.",
        policy=["100% tariff on Chinese EVs"], note=""),
    "9868.HK": dict(access="blocked", confidence="high", us_revenue_share=0.0,
        channel="No US sales. Expanding into Europe.",
        policy=["100% tariff on Chinese EVs"], note=""),
    "9866.HK": dict(access="blocked", confidence="high", us_revenue_share=0.0,
        channel="No US sales despite a US listing and a US R&D office.",
        policy=["100% tariff on Chinese EVs"],
        note="A US listing is not US revenue — NIO is a clean example of the gap."),
    "0175.HK": dict(access="blocked", confidence="medium", us_revenue_share=None,
        channel="No Geely-brand sales in the US. Owns Volvo and Polestar, which do sell there.",
        policy=["Tariffs on Chinese-built vehicles"],
        note="US exposure is indirect, through European brands it owns."),
    "2333.HK": dict(access="blocked", confidence="medium", us_revenue_share=0.0,
        channel="No US presence.", policy=["Tariffs on Chinese-built vehicles"], note=""),
    "2238.HK": dict(access="domestic", confidence="medium", us_revenue_share=0.0,
        channel="Domestic joint ventures with Toyota and Honda.", policy=[], note=""),
    "9863.HK": dict(access="domestic", confidence="medium", us_revenue_share=0.0,
        channel="Domestic, expanding into Europe via the Stellantis partnership.",
        policy=[], note=""),
    "2338.HK": dict(access="open", confidence="low", us_revenue_share=None,
        channel="Sells engines and powertrain globally; owns KION, which has US operations.",
        policy=[], note=""),

    "0981.HK": dict(
        access="restricted", confidence="high", us_revenue_share=None,
        channel="Sells foundry capacity globally, including to US fabless customers, "
                "but cannot buy advanced US equipment.",
        policy=["Added to the US Entity List in December 2020",
                "Export controls block EUV and advanced DUV lithography"],
        note="The binding constraint is what SMIC can buy, not what it can sell. "
             "Its process roadmap is gated by equipment it is barred from importing."),
    "1347.HK": dict(access="restricted", confidence="medium", us_revenue_share=None,
        channel="Mature-node foundry serving international customers.",
        policy=["Subject to US export controls on advanced semiconductor equipment"],
        note="Mature nodes face looser restrictions than SMIC's leading edge."),
    "0020.HK": dict(
        access="blocked", confidence="high", us_revenue_share=0.0,
        channel="No US commercial business.",
        policy=["US Entity List (2019)",
                "US Treasury investment ban — Americans are barred from buying its shares"],
        note="One of the few names here that US investors legally cannot hold."),
    "0763.HK": dict(
        access="blocked", confidence="high", us_revenue_share=None,
        channel="Effectively excluded from US telecom infrastructure.",
        policy=["FCC Covered List — equipment barred from US networks",
                "2018 US export ban, settled with a $1bn penalty"],
        note=""),
    "1810.HK": dict(
        access="tariffed", confidence="high", us_revenue_share=None,
        channel="Phones are not sold through US carriers; accessories and ecosystem "
                "products reach US buyers online. EVs are China-only.",
        policy=["Placed on the US DoD Chinese military companies list in Jan 2021, "
                "removed after litigation in May 2021"],
        note="Global revenue is large but the US is a deliberate gap in its footprint."),
    "0992.HK": dict(
        access="open", confidence="high", us_revenue_share=None,
        channel="Genuine US presence — ThinkPad, Motorola phones through US carriers, "
                "and data-centre infrastructure. North Carolina headquarters.",
        policy=["Tariff exposure on China-manufactured hardware"],
        note="The most US-integrated company in this universe. Incorporated in Hong Kong, "
             "with manufacturing diversified beyond China."),
    "2382.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Camera modules and lenses sold into the Apple and Android supply chains.",
        policy=["Indirect tariff exposure through customers"],
        note="US exposure is indirect — it sells to companies that sell to Americans."),
    "2018.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Acoustic and haptic components; a long-standing Apple supplier.",
        policy=["Indirect tariff exposure"], note=""),
    "0285.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Contract manufacturing, including for Apple.",
        policy=["Indirect tariff exposure"], note=""),
    "6088.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Connectors and components; Foxconn affiliate with global customers.",
        policy=["Tariff exposure"], note=""),
    "0522.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Semiconductor assembly equipment sold worldwide. Singapore-managed.",
        policy=[], note=""),
    "1478.HK": dict(access="open", confidence="low", us_revenue_share=None,
        channel="Camera modules into the Android supply chain.", policy=[], note=""),
    "1385.HK": dict(access="domestic", confidence="low", us_revenue_share=None,
        channel="Chips largely for the domestic market.",
        policy=["Export-control exposure"], note=""),
    "1415.HK": dict(access="open", confidence="low", us_revenue_share=None,
        channel="Camera modules, substantially for Apple.", policy=[], note=""),

    "0700.HK": dict(
        access="restricted", confidence="high", us_revenue_share=None,
        channel="Owns Riot Games outright and holds a large stake in Epic Games, so it "
                "earns meaningful US consumer revenue. WeChat has no US footprint.",
        policy=["Added to the DoD Chinese military companies list in Jan 2025; contests it",
                "A 2020 executive order targeting WeChat was blocked in court"],
        note="Its US revenue arrives through American studios it owns rather than "
             "Chinese products it exports."),
    "9988.HK": dict(
        access="tariffed", confidence="high", us_revenue_share=None,
        channel="AliExpress sells to US consumers; Alibaba Cloud has minimal US share. "
                "The bulk of revenue is domestic Chinese commerce.",
        policy=["End of the de minimis exemption raised costs on low-value parcels",
                "Cloud faces US procurement restrictions"],
        note=""),
    "PDD": dict(
        access="tariffed", confidence="high", us_revenue_share=None,
        channel="Temu is one of the largest Chinese-owned consumer brands in the US by "
                "user count, shipping direct to American households.",
        policy=["Ending the $800 de minimis exemption in 2025 struck directly at its "
                "shipping model", "Continuing tariff and customs scrutiny"],
        note="The most tariff-sensitive company in this universe — its US business model "
             "was built on a customs exemption that no longer exists."),
    "9618.HK": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Overwhelmingly domestic Chinese retail; small cross-border operations.",
        policy=[], note=""),
    "3690.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Purely domestic local services.", policy=[], note=""),
    "9888.HK": dict(access="restricted", confidence="medium", us_revenue_share=None,
        channel="Search and advertising are domestic. Apollo autonomous driving is not "
                "deployed commercially in the US.",
        policy=["US restrictions on Chinese connected-vehicle software"], note=""),
    "1024.HK": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Domestic short video; the international app has little US traction.",
        policy=[], note=""),
    "9660.HK": dict(access="domestic", confidence="medium", us_revenue_share=0.0,
        channel="Automotive AI chips for Chinese carmakers.",
        policy=["Export-control exposure"], note=""),
    "6682.HK": dict(access="domestic", confidence="low", us_revenue_share=None,
        channel="Enterprise AI for Chinese customers.", policy=[], note=""),
    "KC": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Domestic cloud; US-listed but not US-selling.", policy=[], note=""),
    "0268.HK": dict(access="domestic", confidence="low", us_revenue_share=None,
        channel="Enterprise software for Chinese businesses.", policy=[], note=""),
    "3888.HK": dict(access="open", confidence="low", us_revenue_share=None,
        channel="WPS Office and games have some international distribution.", policy=[], note=""),
    "NTES": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Games published internationally; owns US studios and partners with Blizzard.",
        policy=[], note=""),
    "BILI": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Domestic video platform; US-listed only.", policy=[], note=""),
    "TCOM": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Trip.com sells travel internationally, including to US customers.",
        policy=[], note=""),

    "9633.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic bottled water and beverages.", policy=[], note=""),
    "2020.HK": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Domestic sportswear; owns Amer Sports (Salomon, Arc'teryx), which sells in the US.",
        policy=[], note="US exposure is indirect through Amer Sports."),
    "2331.HK": dict(access="domestic", confidence="medium", us_revenue_share=None,
        channel="Almost entirely domestic.", policy=[], note=""),
    "1928.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Macau casinos. US-listed parent Las Vegas Sands, but operations are Macau.",
        policy=[], note=""),
    "YUMC": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Operates KFC and Pizza Hut inside China. US-listed, zero US revenue.",
        policy=[], note="A US-listed company whose entire business is Chinese consumers — "
                        "the mirror image of the usual assumption."),
    "6862.HK": dict(access="open", confidence="medium", us_revenue_share=None,
        channel="Restaurants in China plus a small US restaurant footprint.", policy=[], note=""),
    "0322.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic instant noodles and beverages.", policy=[], note=""),
    "2313.HK": dict(access="open", confidence="high", us_revenue_share=None,
        channel="Contract apparel manufacturing for Nike, Adidas and Uniqlo — much of the "
                "output ends up on US shelves.",
        policy=["Apparel tariff exposure"],
        note="Manufactures in Vietnam and Cambodia as well as China, which softens tariff risk."),
    "1044.HK": dict(access="domestic", confidence="medium", us_revenue_share=0.0,
        channel="Domestic tissue and personal care.", policy=[], note=""),

    "2318.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic insurance and banking.", policy=[], note=""),
    "3968.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic retail and corporate banking.", policy=[], note=""),
    "1398.HK": dict(access="domestic", confidence="high", us_revenue_share=None,
        channel="Domestic banking with international branches.",
        policy=["Exposed to US financial sanctions policy"], note=""),
    "0388.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Operates the Hong Kong exchange.", policy=[], note=""),
    "6060.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic online insurance.", policy=[], note=""),
    "FUTU": dict(access="restricted", confidence="medium", us_revenue_share=None,
        channel="Online brokerage for Chinese investors; a US entity serves some clients.",
        policy=["Chinese regulators forced it to stop onboarding mainland clients (2022)"],
        note="Its regulatory risk sits in Beijing rather than Washington."),
    "QFIN": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic consumer lending. US-listed only.", policy=[], note=""),
    "FINV": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic and Southeast Asian lending.", policy=[], note=""),

    "0857.HK": dict(access="domestic", confidence="high", us_revenue_share=None,
        channel="Oil and gas, overwhelmingly domestic.",
        policy=["Delisted from the NYSE in 2021 under a US investment order"], note=""),
    "0386.HK": dict(access="domestic", confidence="high", us_revenue_share=None,
        channel="Refining and chemicals, domestic.",
        policy=["Delisted from the NYSE in 2021"], note=""),
    "1088.HK": dict(access="domestic", confidence="high", us_revenue_share=0.0,
        channel="Domestic coal and power.", policy=[], note=""),
    "0669.HK": dict(access="open", confidence="high", us_revenue_share=None,
        channel="Milwaukee Tool and Ryobi — sold through Home Depot. The US is its "
                "single largest market.",
        policy=["Tariff exposure on China-manufactured tools"],
        note="Hong Kong-listed, but a majority of revenue comes from North America. "
             "The strongest US-facing name in this universe."),
    "1919.HK": dict(access="tariffed", confidence="medium", us_revenue_share=None,
        channel="Container shipping on transpacific routes into US ports.",
        policy=["Proposed US port fees on Chinese-built and Chinese-operated vessels"],
        note=""),
}

ACCESS_META = {
    "open":       {"label": "Sells openly in the US", "rank": 4, "color": "#1a7f4b"},
    "tariffed":   {"label": "Sells, exposed to tariffs", "rank": 3, "color": "#b8860b"},
    "restricted": {"label": "Restricted by US policy", "rank": 2, "color": "#c2691c"},
    "blocked":    {"label": "Effectively blocked", "rank": 1, "color": "#b3392e"},
    "domestic":   {"label": "Little or no US business", "rank": 0, "color": "#6b7f92"},
}

BENCHMARK = "^GSPC"   # S&P 500, for the computed US-market beta


def tickers() -> list[str]:
    return [c.ticker for c in UNIVERSE]


def by_ticker() -> dict[str, Co]:
    return {c.ticker: c for c in UNIVERSE}
