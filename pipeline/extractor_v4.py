#!/usr/bin/env python3
"""
extractor_v4.py — Pipeline NLP cuarta generación.

Correcciones sobre v3:
  1. CHUNKING COMPLETO (H1+H2): parse_sections ahora captura headings de nivel
     #, ##, ###, ####, ##### (no solo 3-5 hashes). Para newsletters deep-dive
     cuyo asunto es `# Título`, el H1 se registra como article_title y se
     propaga a todos los events del bloque como headline canónico.
  2. ASOCIACIÓN HÍBRIDA (TÍTULO + CUERPO): si el nombre o alias de una empresa
     aparece en el HEADING de la sección, se asocia automáticamente aunque
     spaCy no la detecte en el cuerpo.
  3. ALIAS DICTIONARY: empresas clave con nombres múltiples (City Express /
     Norte 19, Nubank / Nu México, KOF / Coca-Cola FEMSA, etc.) mapean al
     canónico aunque spaCy solo reconozca uno de los alias.
  4. SNIPPET FALLBACK: cuando la asociación viene del HEADING (no del body),
     se acepta el primer párrafo sustancial sin requerir que la empresa sea
     re-mencionada literalmente en ese párrafo.
"""

import re, json, os, sys, time
from collections import defaultdict, Counter

import spacy

BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_DIR   = os.path.join(BASE, "brief_year_md")
HTML_OUT = os.path.join(BASE, "web", "index.html")
JSON_OUT = os.path.join(BASE, "extracted_v4.json")
DATA_OUT = os.path.join(BASE, "web", "data.json")

# ── SPACY ──────────────────────────────────────────────────────────────────────
print("Cargando spaCy…", flush=True)
nlp = spacy.load("es_core_news_sm", disable=["parser","tagger","attribute_ruler","lemmatizer"])
nlp.max_length = 500_000

# ── AD / SPONSOR MARKERS ───────────────────────────────────────────────────────
AD_PATTERNS = [
    r'presentado\s+por\s*:',
    r'patrocinado\s+por\s*:',
    r'en\s+colaboraci[oó]n\s+con\s*:',
    r'\bsponsor(izado)?\b',
    r'an[uú]nciate\s+aqu[ií]',
    r'publicidad\s+whitepaper',
    r'whitepaper\s+selecci[oó]n',
    r'seleccion\s+editorial',
    r'desuscribirse',
    r'unsubscribe',
    r'este\s+correo\s+(fue|es)\s+(enviado|patrocinado)',
    r'copyright\s+\d{4}',
    r'view\s+in\s+(your\s+)?browser',
    r'ver\s+en\s+el\s+navegador',
    r'sent\s+from\s+',
    r'powered\s+by\s+',
    r'\belevenlab(s)?\b',
]
AD_RE = re.compile('|'.join(AD_PATTERNS), re.IGNORECASE)

# Matches inline sponsor/promo lines so they can be stripped from body text
# before NLP runs. Anchored to line-start to avoid removing legitimate body text
# that merely references a sponsor in passing (e.g. "el sponsor del evento fue…").
_SPONSOR_LINE_RE = re.compile(
    r'^[>\s*_#]*'                              # optional markdown decorators
    r'(?:'
    r'sponsored\s+by'
    r'|patrocinado\s+por'
    r'|presentado\s+por'
    r'|powered\s+by'
    r'|en\s+colaboraci[oó]n\s+con'
    r')\s*:?\s*',
    re.IGNORECASE | re.MULTILINE,
)

def is_ad_section(heading: str, body: str) -> bool:
    if AD_RE.search(heading): return True
    if AD_RE.search(body[:400]): return True
    if re.match(r'^\s*(presentad|patrocin|sponsor|en colabor)', heading, re.IGNORECASE):
        return True
    return False

# ── ALIAS DICTIONARY ───────────────────────────────────────────────────────────
# Maps canonical_name → list of alias strings (lowercased for matching)
# Covers companies that spaCy may not recognize or that use different names.
ALIASES: dict[str, list[str]] = {
    "City Express":    ["city express", "norte 19", "hoteles city express",
                        "hoteles city", "city express by marriott", "promotora de hoteles norte 19"],
    "OXXO":            ["oxxo", "femsa comercio", "spin by oxxo", "spin by oxxo"],
    "Nubank":          ["nubank", "nu méxico", "nu mexico", "nu bank", "nu financial"],
    "KOF":             ["kof", "coca-cola femsa", "coca cola femsa", "femsa coca-cola"],
    "FEMSA":           ["femsa", "fomento económico mexicano", "fomento economico mexicano"],
    "Fibra Inn":       ["fibra inn", "finn"],
    "Fibra Uno":       ["fibra uno", "funo"],
    "Vinte":           ["vinte"],
    "Arca Continental":["arca continental", "arca", "ac"],
    "Gruma":           ["gruma", "maseca", "mission foods"],
    "Bachoco":         ["bachoco", "industrias bachoco"],
    "Grupo Modelo":    ["grupo modelo", "cervecería modelo", "cervezas modelo", "cerveceria modelo"],
    "Sigma Alimentos": ["sigma alimentos", "sigma"],
    "Kavak":           ["kavak", "kavak.com"],
    "Cornershop":      ["cornershop", "cornershop by uber"],
    "DiDi":            ["didi", "didi food", "99"],
    "Aeroméxico":      ["aeromexico", "aeroméxico", "grupo aeromexico", "grupo aeroméxico", "am"],
    "Viva Aerobus":    ["viva aerobus", "vivaaerobus", "viva aerobús"],
    "Mercado Libre":   ["mercado libre", "mercadolibre", "meli", "mercadopago"],
    "Banorte":         ["banorte", "grupo financiero banorte", "gfnorte"],
    "BBVA México":     ["bbva méxico", "bbva mexico", "bbva bancomer", "bancomer"],
    "Citibanamex":     ["citibanamex", "banamex", "citi mexico", "citi méxico"],
    "América Móvil":   ["america movil", "américa móvil", "amx", "claro"],
    "Grupo México":    ["grupo mexico", "grupo méxico", "gmx"],
    "Grupo Salinas":   ["grupo salinas", "salinas", "azteca", "elektra"],
    "Televisa":        ["televisa", "grupo televisa", "televisa univision"],
    "Cemex":           ["cemex", "cemex sab", "cementos mexicanos"],
}

# Reverse map: alias_lower → canonical_name (precomputed for O(1) lookup)
_ALIAS_REVERSE: dict[str, str] = {}
for canonical, aliases in ALIASES.items():
    for a in aliases:
        _ALIAS_REVERSE[a.lower()] = canonical

# ── CURATED PRIORITY LIST ──────────────────────────────────────────────────────
# FIX: City Express, Norte 19, Fibra Inn, Fibra Uno, Arca Continental now included
PRIORITY = [
    # Retail / Consumo
    "Walmart","Soriana","Coppel","Liverpool","Chedraui","La Comer","Casa Ley",
    "HEB","OXXO","Costco","Sam's","Alsea","FEMSA","Bimbo","Gruma","Lala",
    "Bachoco","Grupo Modelo","Heineken México","ConMéxico",
    # KOF / Coca-Cola FEMSA
    "KOF","Coca-Cola FEMSA",
    # Finanzas
    "Banorte","BBVA México","Citibanamex","Banamex","Santander México",
    "HSBC México","Scotiabank","Inbursa","Banco Regional","BanBajío","Actinver",
    "GBM","Klar","Stori","Nubank","Hey Banco","Ualá","Flink",
    # Fintech / Tech
    "Clara","Konfío","Kueski","Clip","OpenPay","Conekta","Spin by OXXO",
    "Kavak","Rappi","Cornershop","Mercado Libre","Amazon México",
    "Uber","DiDi","inDrive",
    # Telecomunicaciones
    "América Móvil","Telmex","Telcel","Izzi","Megacable","Totalplay","Axtel",
    # Aviación
    "Aeroméxico","Volaris","Viva Aerobus","VivaAerobus",
    # Industria / Energía / Infra
    "Cemex","Grupo México","AHMSA","Ternium","Vitro","Nemak","Mabe",
    "Pemex","CFE","Cotemar","Techint",
    "ICA","Pinfra","OHL México","Vinte","Ara","Geo","Urbi",
    # Hotelero (FIX: añadidos)
    "City Express","Norte 19","Hoteles City Express","Marriott",
    "Fibra Inn","Fibra Uno","Arca Continental",
    # Media / Entretenimiento
    "Televisa","TV Azteca","Grupo Salinas","Elektra","Italika","Totalplay",
    "Cinépolis","Cinemex",
    # Proptech / Logística
    "Homie","Flat.mx","La Haus","Habi","Clikalia",
    "Nowports","Nuvocargo","Grupo Traxión","Redpack","Estafeta",
    # Startups / Scale-ups
    "Merama","Jüsto","Jokr","Orchata","Calii","Simetrik","Truora",
    # Educación / Salud
    "Genomma Lab","Farmacias del Ahorro","Farmacias Guadalajara",
    "Sigma Alimentos","Grupo Herdez","Mifel",
]

SHORT_NAMES = {co for co in PRIORITY if len(co) <= 4}

def _make_pattern(co):
    if co in SHORT_NAMES:
        return re.compile(r'\b' + re.escape(co) + r'\b')
    return re.compile(r'\b' + re.escape(co) + r'\b', re.IGNORECASE)

_PRIORITY_PATTERNS = {co: _make_pattern(co) for co in PRIORITY}

CANONICALS = {
    # Existing
    "oxxo":                     "OXXO",
    "viva aerobus":             "Viva Aerobus",
    "vivaaerobus":              "Viva Aerobus",
    "grupo salinas":            "Grupo Salinas",
    "televisa":                 "Televisa",
    "tv azteca":                "TV Azteca",
    "mercadolibre":             "Mercado Libre",
    "meli":                     "Mercado Libre",
    "grupo bimbo":              "Bimbo",
    "bimbo sab":                "Bimbo",
    "grupo modelo":             "Grupo Modelo",
    "cervecería modelo":        "Grupo Modelo",
    "cerveceria modelo":        "Grupo Modelo",
    "cervezas modelo":          "Grupo Modelo",
    "grupo femsa":              "FEMSA",
    "coca-cola femsa":          "KOF",
    "femsa coca-cola":          "KOF",
    "kof":                      "KOF",
    "grupo financiero banorte": "Banorte",
    "bbva bancomer":            "BBVA México",
    "banamex":                  "Citibanamex",
    "citi":                     "Citibanamex",
    "cemex sab":                "Cemex",
    "america movil":            "América Móvil",
    "amx":                      "América Móvil",
    "aeromexico":               "Aeroméxico",
    "grupo aeromexico":         "Aeroméxico",
    "volaris":                  "Volaris",
    "grupo volaris":            "Volaris",
    "konfio":                   "Konfío",
    "elektra":                  "Elektra",
    "italika":                  "Italika",
    "sam's club":               "Sam's",
    "kavak.com":                "Kavak",
    "didi":                     "DiDi",
    "uber eats":                "Uber",
    "cinepolis":                "Cinépolis",
    "farmacias del ahorro":     "Farmacias del Ahorro",
    "la comer":                 "La Comer",
    "nowports":                 "Nowports",
    "nuvocargo":                "Nuvocargo",
    # FIX: City Express aliases
    "norte 19":                 "City Express",
    "hoteles city express":     "City Express",
    "hoteles city":             "City Express",
    "city express":             "City Express",
    "promotora de hoteles norte 19": "City Express",
    # FIX: Nu / Nubank aliases
    "nu méxico":                "Nubank",
    "nu mexico":                "Nubank",
    "nu bank":                  "Nubank",
    # FIX: Fibra Inn / Fibra Uno
    "finn":                     "Fibra Inn",
    "funo":                     "Fibra Uno",
    # FIX: Arca Continental
    "arca":                     "Arca Continental",
    # FIX: Cornershop
    "cornershop by uber":       "Cornershop",
}

SECTOR_MAP = {
    "Walmart":"Retail / Consumo","Soriana":"Retail / Consumo",
    "Coppel":"Retail / Servicios Financieros","Liverpool":"Retail / Lujo",
    "Chedraui":"Retail / Consumo","La Comer":"Retail / Consumo",
    "Casa Ley":"Retail / Consumo","HEB":"Retail / Consumo",
    "OXXO":"Retail / Conveniencia","Costco":"Retail / Consumo",
    "Sam's":"Retail / Consumo","Alsea":"Restaurantes / Franquicias",
    "FEMSA":"Consumo / Conglomerado","KOF":"Consumo / Bebidas",
    "Coca-Cola FEMSA":"Consumo / Bebidas",
    "Bimbo":"Consumo / Alimentos","Gruma":"Consumo / Alimentos","Lala":"Consumo / Lácteos",
    "Bachoco":"Consumo / Alimentos","Grupo Modelo":"Consumo / Bebidas",
    "Heineken México":"Consumo / Bebidas","ConMéxico":"Consumo / Asociación",
    "Banorte":"Servicios Financieros / Banca","BBVA México":"Servicios Financieros / Banca",
    "Citibanamex":"Servicios Financieros / Banca","Banamex":"Servicios Financieros / Banca",
    "Santander México":"Servicios Financieros / Banca","HSBC México":"Servicios Financieros / Banca",
    "Scotiabank":"Servicios Financieros / Banca","Inbursa":"Servicios Financieros / Seguros",
    "Banco Regional":"Servicios Financieros / Banca","BanBajío":"Servicios Financieros / Banca",
    "Actinver":"Servicios Financieros / Inversiones","GBM":"Fintech / Inversiones",
    "Klar":"Fintech / Banca Digital","Stori":"Fintech / Crédito","Nubank":"Fintech / Banca Digital",
    "Hey Banco":"Fintech / Banca Digital","Ualá":"Fintech / Banca Digital","Flink":"Fintech / Inversiones",
    "Clara":"Fintech / B2B","Konfío":"Fintech / Crédito PYME","Kueski":"Fintech / Crédito",
    "Clip":"Fintech / Pagos","OpenPay":"Fintech / Pagos","Conekta":"Fintech / Pagos",
    "Spin by OXXO":"Fintech / Pagos",
    "Kavak":"Tecnología / Automotriz","Rappi":"Tecnología / Delivery",
    "Cornershop":"Tecnología / Delivery","Mercado Libre":"Tecnología / E-commerce",
    "Amazon México":"Tecnología / E-commerce","Uber":"Tecnología / Movilidad",
    "DiDi":"Tecnología / Movilidad","inDrive":"Tecnología / Movilidad",
    "América Móvil":"Telecomunicaciones","Telmex":"Telecomunicaciones",
    "Telcel":"Telecomunicaciones","Izzi":"Telecomunicaciones",
    "Megacable":"Telecomunicaciones","Totalplay":"Telecomunicaciones","Axtel":"Telecomunicaciones",
    "Aeroméxico":"Aviación","Volaris":"Aviación / Low Cost","Viva Aerobus":"Aviación / Low Cost",
    "Cemex":"Construcción / Materiales","Grupo México":"Minería / Transporte",
    "Ternium":"Industria / Acero","Vitro":"Industria / Vidrio","Nemak":"Industria / Automotriz",
    "Mabe":"Industria / Electrodomésticos","Pemex":"Energía / Petróleo","CFE":"Energía / Electricidad",
    "ICA":"Infraestructura / Construcción","Pinfra":"Infraestructura / Concesiones",
    "Televisa":"Media / Entretenimiento","TV Azteca":"Media / Entretenimiento",
    "Grupo Salinas":"Conglomerado / Retail & Media","Elektra":"Retail / Servicios Financieros",
    "Italika":"Movilidad / Motocicletas","Cinépolis":"Media / Entretenimiento",
    "Cinemex":"Media / Entretenimiento","Homie":"Proptech","Flat.mx":"Proptech",
    "La Haus":"Proptech","Habi":"Proptech","Clikalia":"Proptech",
    "Nowports":"Logística / Tecnología","Nuvocargo":"Logística / Tecnología",
    "Grupo Traxión":"Logística / Transporte","Redpack":"Logística / Mensajería",
    "Merama":"Tecnología / E-commerce","Jüsto":"Retail / D2C","Jokr":"Tecnología / Quick Commerce",
    "Simetrik":"Tecnología / B2B SaaS","Genomma Lab":"Salud / Consumer",
    "Farmacias del Ahorro":"Salud / Farmacias","Farmacias Guadalajara":"Salud / Farmacias",
    "Sigma Alimentos":"Consumo / Alimentos","Grupo Herdez":"Consumo / Alimentos",
    "Mifel":"Servicios Financieros / Banca",
    # FIX: nuevos sectores
    "City Express":"Hotelería / Negocios","Norte 19":"Hotelería / Negocios",
    "Hoteles City Express":"Hotelería / Negocios","Marriott":"Hotelería / Internacional",
    "Fibra Inn":"Bienes Raíces / FIBRA","Fibra Uno":"Bienes Raíces / FIBRA",
    "Arca Continental":"Consumo / Bebidas",
}

CITY_MAP = {
    "Walmart":"CDMX","Soriana":"Monterrey","Coppel":"Culiacán","Liverpool":"CDMX",
    "FEMSA":"Monterrey","KOF":"Monterrey","Coca-Cola FEMSA":"Monterrey",
    "Bimbo":"CDMX","Gruma":"Monterrey","Lala":"Torreón",
    "Alsea":"CDMX","Banorte":"Monterrey","BBVA México":"CDMX","Citibanamex":"CDMX",
    "GBM":"CDMX","Kavak":"CDMX","Rappi":"CDMX","Mercado Libre":"Buenos Aires",
    "Uber":"CDMX","América Móvil":"CDMX","Aeroméxico":"CDMX","Volaris":"CDMX",
    "Viva Aerobus":"Monterrey","Cemex":"Monterrey","Grupo México":"Sonora",
    "Pemex":"CDMX","CFE":"CDMX","Televisa":"CDMX","TV Azteca":"CDMX",
    "Grupo Salinas":"CDMX","Elektra":"CDMX","Cinépolis":"Morelia",
    "Nowports":"Monterrey","Nubank":"CDMX","Clara":"CDMX","Konfío":"CDMX",
    "Megacable":"Guadalajara","Axtel":"Monterrey","Kueski":"Guadalajara",
    "City Express":"Monterrey","Fibra Inn":"Monterrey","Fibra Uno":"CDMX",
    "Arca Continental":"Monterrey",
}

COLOR_MAP = {
    "Retail / Consumo":"#34D399","Retail / Lujo":"#4ADE80",
    "Retail / Servicios Financieros":"#34D399","Retail / Conveniencia":"#6EE7B7",
    "Retail / D2C":"#A7F3D0","Consumo / Conglomerado":"#34D399",
    "Consumo / Alimentos":"#A3E635","Consumo / Lácteos":"#BEF264",
    "Consumo / Bebidas":"#86EFAC","Restaurantes / Franquicias":"#4ADE80",
    "Servicios Financieros / Banca":"#38BDF8","Servicios Financieros / Seguros":"#7DD3FC",
    "Servicios Financieros / Inversiones":"#BAE6FD",
    "Fintech / Banca Digital":"#818CF8","Fintech / Inversiones":"#A78BFA",
    "Fintech / Crédito":"#C084FC","Fintech / Crédito PYME":"#E879F9",
    "Fintech / B2B":"#F0ABFC","Fintech / Pagos":"#D946EF",
    "Telecomunicaciones":"#F87171","Aviación":"#FBBF24","Aviación / Low Cost":"#FCD34D",
    "Tecnología / Movilidad":"#FB923C","Tecnología / Delivery":"#FDBA74",
    "Tecnología / E-commerce":"#FDE68A","Tecnología / Automotriz":"#FCA5A5",
    "Tecnología / Quick Commerce":"#FED7AA","Tecnología / B2B SaaS":"#BAE6FD",
    "Construcción / Materiales":"#94A3B8","Industria / Acero":"#CBD5E1",
    "Industria / Automotriz":"#D1D5DB","Minería / Transporte":"#9CA3AF",
    "Industria / Vidrio":"#CBD5E1","Industria / Electrodomésticos":"#D1D5DB",
    "Energía / Petróleo":"#FCA5A5","Energía / Electricidad":"#FCD34D",
    "Infraestructura / Construcción":"#94A3B8","Infraestructura / Concesiones":"#CBD5E1",
    "Media / Entretenimiento":"#F9A8D4","Conglomerado / Retail & Media":"#FDA4AF",
    "Movilidad / Motocicletas":"#FDE68A","Proptech":"#C7D2FE",
    "Logística / Tecnología":"#67E8F9","Logística / Transporte":"#A5F3FC",
    "Logística / Mensajería":"#CFFAFE","Salud / Consumer":"#BBF7D0",
    "Salud / Farmacias":"#D1FAE5","Consumo / Asociación":"#A7F3D0",
    "Hotelería / Negocios":"#FDE68A","Hotelería / Internacional":"#FCD34D",
    "Bienes Raíces / FIBRA":"#C7D2FE",
}

# ── BLACKLIST ──────────────────────────────────────────────────────────────────
BLACKLIST = {
    "whitepaper","cinco minutos","comentario","la","el","los","las","un","una",
    "en","de","del","al","que","se","su","sus","si","no","pero","como","también",
    "este","esta","estos","estas","ese","esa","eso","hay","muy","ya","sin",
    "entre","sobre","bajo","tras","ante","desde","hasta","hacia","durante",
    "startup","startups","empresa","empresas","compañía","grupo genérico",
    "fondo","capital","inversión","banco","mercado","industria","sector",
    "modelo","negocio","servicio","producto","cliente","usuario","equipo",
    "plataforma","categoría","canal","marca","tienda","proyecto","programa",
    "acuerdo","alianza","resultado","meta","objetivo","plan","estrategia",
    "reuters","bloomberg","wsj","ft","cnbc","the information","forbes",
    "reforma","expansión","milenio","el financiero","el economista",
    "inegi","cnbv","cofece","sat","imss","shcp","sre","sep","ssa",
    "gobierno","secretaría","estados unidos","usa","eua","latam","cdmx",
    "monterrey","guadalajara","nuevo leon","jalisco","sonora","brasil",
    "q1","q2","q3","q4","t1","t2","t3","t4","h1","h2",
    "venture capital","private equity","ipo","bmv","nyse","nasdaq",
    "ebitda","roi","roe","roa","nps","gmv","arr","mrr",
    "enero","febrero","marzo","abril","mayo","junio","julio","agosto",
    "septiembre","octubre","noviembre","diciembre","lunes","martes","miércoles",
    "co","sa","sv","cv","inc","ltd","llc","srl",
    "harvard","stanford","mit","wharton","yale","oxford","cambridge",
    "microsoft","apple","google","amazon","meta","netflix","spotify",
    "toyota","bmw","volkswagen","nissan","honda","volvo","porsche","adidas","nike",
    "ny times","new york times","financial times","wall street journal",
    "sec","fbi","cia","otan","fifa","uefa","conmebol",
    "burger king","mcdonald's","kfc","starbucks","domino's",
    "elevenlab","elevenlabs","médica sur","medica sur",
    "presmed","clínica","hospital","doctor","medicamento",
}

# ── CATEGORY & SENTIMENT ───────────────────────────────────────────────────────
CAT_RULES = [
    ("Análisis", [
        "rene lankenau","rené lankenau","estos son sus planes","historia de",
        "hace 22 años","hace 20 años","hace 10 años","historia completa",
        "fondo de la historia","detrás de","así funciona","¿cómo llegó",
        "¿por qué","así nació","nacimiento de","el origen de","la historia de",
        "análisis:","análisis whitepaper","un vistazo a","deep dive","paid",
    ]),
    ("Alertas/Caídas", [
        "quiebra","concurso mercantil","demanda","litigio","multa","fraude",
        "escándalo","investigación de la","caída en","declive","recorte de",
        "despido","despidos masivos","cierre de","pérdida operativa","crisis financiera",
        "colapso","sanción","penalización","alerta regulatoria","cofece",
        "cnbv sanciona","sat investiga","regulación en contra","falla en juicio",
        "amparo negado","sentencia en contra","interdicto","embargo","insolvencia",
    ]),
    ("Movimientos Directivos", [
        "nombró a","designó a","nombra a","designa a","nombra como","asumió como",
        "nuevo ceo","nueva ceo","nuevo director general","nueva directora general",
        "nuevo cfo","nuevo cto","nuevo coo","nuevo presidente","nueva presidenta",
        "presidenta ejecutiva","presidente ejecutivo","asumió la dirección",
        "tomó las riendas","renuncia de","renunció el","renunció la",
        "salida de","salida del","salida definitiva","se va de","cofundador sale",
        "cofundadora sale","retiro del","sucesor de","sucesión en",
        "incorporó a","llegó como director","contrata a","ficha a","fichó a",
    ]),
    ("Chismes de Mercado", [
        "rumores","fuentes cercanas","se dice que","extraoficialmente","sin confirmar",
        "negó las versiones","conversaciones preliminares","explora la posibilidad",
        "negocia con","estaría en pláticas","posible fusión","posible adquisición",
        "podría adquirir","podría comprar","fuentes del mercado","según fuentes",
        "no confirmó","no negó","declinó comentar","no hizo comentarios",
        "oferta no solicitada","proceso de venta","se especula","rumor de",
    ]),
    ("Resultados", [
        "ingresos de","utilidad neta de","ebitda de","reportó resultados",
        "resultados del trimestre","cifras del primer","cifras del segundo",
        "ronda serie a","ronda serie b","ronda serie c","ronda seed",
        "levantó capital por","captó","valuación de","debutó en bolsa","cotiza en",
        "creció","crecimiento de","superó","récord de ventas","record histórico",
        "retorno de","múltiplo de","distribuciones a","flujo de caja",
        "millones de pesos","millones de dólares","mil millones","miles de millones",
        "pérdida de","ganancia de","margen bruto","margen operativo",
        "Q1","Q2","Q3","Q4","primer trimestre","segundo trimestre",
        "tercer trimestre","cuarto trimestre","semestral","anual",
    ]),
    ("Anuncios", [
        "anunció","anuncia","lanzó","lanza","presentó","presenta",
        "firmó acuerdo","firma acuerdo","alianza con","expansión a",
        "inauguró","abrió","abre tienda","nuevo producto","nueva línea",
        "adquirió a","compró a","compra de","fusión con","inversión en",
        "plan de inversión","joint venture","asociación estratégica",
        "entra al mercado","ingresa a","incursiona","diversificación hacia",
        "lanzamiento de","nuevo servicio","nueva plataforma","acuerdo con",
    ]),
]

DEEPDIVE_SIGNALS = re.compile(
    r'(rene\s+lankenau|rené\s+lankenau|luis\s+barrios|estos\s+son\s+sus\s+planes|'
    r'hace\s+\d{1,2}\s+años|la\s+historia\s+de|el\s+origen\s+de|así\s+nació|'
    r'detrás\s+de|deep\s+dive|\bpaid\b)', re.IGNORECASE
)

def classify_event(text: str, body_full: str = "") -> str:
    # Long editorial pieces (> 800 chars) or deep-dive signals → "Análisis"
    if len(body_full) > 800 or DEEPDIVE_SIGNALS.search(body_full):
        return "Análisis"
    t = text.lower()
    for cat, kws in CAT_RULES:
        if any(kw in t for kw in kws):
            return cat
    return "Anuncios"

SENT_POS = [
    "récord","máximo histórico","superó","creció","crecimiento","logró","éxito",
    "expansión","lanzó","alianza","firmó","captó","levantó","valuación",
    "debut bursátil","primer lugar","primera mujer","innovación","liderazgo",
    "positivo","fortalecimiento","consolidación","aumento de","incremento de",
]
SENT_NEG = [
    "pérdida","declive","caída","demanda judicial","multa","fraude","quiebra",
    "despidos","cierre","crisis","escándalo","sanción","renuncia","salida",
    "recorte","reducción","desplome","colapso","investigación","problema",
    "en contra","falla","negativo","contracción","deuda","default",
]

def classify_sentiment(text, cat):
    if cat == "Alertas/Caídas": return "negative"
    t = text.lower()
    p = sum(1 for w in SENT_POS if w in t)
    n = sum(1 for w in SENT_NEG if w in t)
    if n > p:  return "negative"
    if p > 0:  return "positive"
    return "neutral"

# ── CLEANING ───────────────────────────────────────────────────────────────────
URL_RE    = re.compile(r'https?://\S+')
LINK_RE   = re.compile(r'\[([^\]]+)\]\([^)]+\)')
BOLD_RE   = re.compile(r'\*{1,3}([^*\n]+)\*{1,3}')
TABLE_RE  = re.compile(r'^\s*\|.*\|.*$', re.MULTILINE)
TRAIL_RE  = re.compile(r'‌[\s‌]*')
WSPACE_RE = re.compile(r'[ \t]{2,}')

def clean_text(t):
    # FIX v4.2: LINK_RE must run BEFORE URL_RE.
    # URL_RE (r'https?://\S+') consumes the closing ')' of a markdown link
    # because ')' is non-whitespace. If URL_RE runs first, LINK_RE finds
    # "[text](" with no closing ')' and matches across many paragraphs until
    # the next ')' in the article body, silently eating large text blocks.
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)   # images first
    t = LINK_RE.sub(r'\1', t)                     # [text](url) → text
    t = URL_RE.sub('', t)                          # bare URLs gone
    t = BOLD_RE.sub(r'\1', t)
    t = TABLE_RE.sub('', t)
    t = TRAIL_RE.sub(' ', t)
    t = re.sub(r'_([^_\n]+)_', r'\1', t)
    t = re.sub(r'`[^`]+`', '', t)
    # Strip inline sponsor/promo lines so entities after "Sponsored by: X"
    # are never passed to spaCy as editorial mentions.
    lines = t.splitlines()
    t = '\n'.join(l for l in lines if not _SPONSOR_LINE_RE.match(l))
    t = WSPACE_RE.sub(' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def is_toc_line(line):
    return line.count(';') >= 3 or line.count('—') >= 3

def is_metadata(line):
    l = line.strip()
    return (
        l.startswith('**Date:**') or l.startswith('**From:**') or
        l.startswith('# Whitepaper') or l.startswith('# [Whitepaper') or
        l.startswith('### Whitepaper') or l.startswith('**Whitepaper**') or
        l == '> _**Cinco minutos bien invertidos**_' or
        l.startswith('> _**Cinco minutos') or
        bool(re.match(r'^#{1,3}\s+(Whitepaper|hoy|HOY)', l)) or
        l.startswith('[Open in browser]') or
        l.startswith('[Ver en el navegador]') or
        l.startswith('_**Suscripciones corporativas**_') or
        bool(re.match(r'^#{3,5}\s+\*?\*?Presentado', l, re.IGNORECASE)) or
        bool(re.match(r'^#{3,5}\s+\*?\*?Patrocinado', l, re.IGNORECASE)) or
        bool(re.match(r'^#{3,5}\s+\*?\*?En colaboraci', l, re.IGNORECASE)) or
        bool(re.match(r'^#{3,5}\s+\*?\*?Sponsor', l, re.IGNORECASE))
    )

COMMENTARY_RE = re.compile(
    r'>\s*_?\*?\*?Comentario Whitepaper[^:]*:\*?\*?_?\s*', re.IGNORECASE
)

def extract_comment(text):
    m = COMMENTARY_RE.search(text)
    if m:
        after = text[m.end():].strip()
        after = clean_text(after).strip('_*> ')
        if len(after) > 30:
            return after[:220] + ('…' if len(after) > 220 else '')
    return ''

# ── NEWSLETTER PARSER ──────────────────────────────────────────────────────────
DATE_RE   = re.compile(r'\*\*Date:\*\*\s*(.+?)(?:\n|$)')
FROM_RE   = re.compile(r'\*\*From:\*\*\s*(.+?)(?:\n|$)')
MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dic":12,
    "ene":1,"abr":4,"ago":8,
}

def parse_date(block):
    m = DATE_RE.search(block)
    if m:
        ds = m.group(1).strip()
        m2 = re.search(r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', ds)
        if m2:
            d, mo_s, y = m2.groups()
            mo = MONTH_MAP.get(mo_s.lower()[:3], 1)
            return f"{y}-{mo:02d}-{int(d):02d}", int(y)
    return None, None


def parse_source(block) -> str:
    m = FROM_RE.search(block)
    if m:
        val = m.group(1).strip()
        if "espresso" in val.lower():
            return "Espresso Matutino"
    return "Whitepaper"


def parse_sections(block):
    """
    Returns list of (article_title, heading, body_text) tuples.

    FIX v4: now handles ALL heading levels (# to #####).
    - H1 (#): treated as the article/newsletter title for the whole block.
      If a H1 is seen and it is NOT a standard metadata/roundup title, it is
      recorded as `article_title`. That title is attached to every subsequent
      section in the same block.
    - H2 (##) and H3-H5 (###-#####): section headings as before.
    - Ad/sponsor sections are still discarded.
    """
    lines        = block.split('\n')
    sections: list[tuple[str | None, str, str]] = []
    article_title: str | None = None   # H1 of a deep-dive email
    cur_head:  str | None = None
    cur_body:  list[str]  = []

    def flush():
        if cur_head and cur_body:
            body = '\n'.join(cur_body)
            if not is_ad_section(cur_head, body):
                sections.append((article_title, cur_head, body))

    for line in lines:
        if is_metadata(line):
            continue
        if is_toc_line(line):
            continue

        # --- H1 heading: deep-dive article title ----------------------------
        m1 = re.match(r'^#\s+(.+)$', line)
        if m1:
            raw_h1 = m1.group(1).strip()
            cleaned = clean_text(raw_h1)
            # Ignore Whitepaper-branded titles (already caught by is_metadata
            # in most cases, but belt-and-suspenders)
            if re.match(r'whitepaper|cinco minutos', cleaned, re.IGNORECASE):
                continue
            if is_toc_line(cleaned) or len(cleaned) < 4:
                continue
            # If there's already a body under a heading, flush it first
            flush()
            # Record as the deep-dive article title (overrides any previous H1
            # within the same newsletter block – last H1 wins for article title)
            article_title = cleaned
            cur_head, cur_body = None, []
            continue

        # --- H2 heading: subtitle / secondary article heading ---------------
        m2 = re.match(r'^##\s+(.+)$', line)
        if m2:
            raw_h2 = m2.group(1).strip()
            cleaned = clean_text(raw_h2)
            if is_toc_line(cleaned) or len(cleaned) < 4:
                continue
            if AD_RE.search(cleaned):
                cur_head, cur_body = None, []
                continue
            flush()
            cur_head = cleaned
            cur_body = []
            continue

        # --- H3-H5 headings: standard section headings ----------------------
        m35 = re.match(r'^#{3,5}\s+(.+)$', line)
        if m35:
            flush()
            heading = m35.group(1).strip()
            if is_toc_line(heading) or len(clean_text(heading)) < 2:
                cur_head, cur_body = None, []
                continue
            if AD_RE.search(heading):
                cur_head, cur_body = None, []
                continue
            cur_head = clean_text(heading)
            cur_body = []
            continue

        # --- Body line -------------------------------------------------------
        # If article_title exists but no section heading yet, use article_title
        # itself as the section heading (whole-article deep-dive)
        if cur_head is None and article_title is not None:
            # Start an implicit section under the article title
            cur_head = article_title
            cur_body = []

        if cur_head is not None:
            cur_body.append(line)

    flush()
    return sections


# ── QUALITY GATE ───────────────────────────────────────────────────────────────
HAS_SUBSTANCE = re.compile(
    r'(\d[\d,%\.]+|\$[\d,.]+|millones|miles de millones|'
    r'adquirió|compró|lanzó|reportó|superó|firmó|anunció|'
    r'nombró|renunció|presentó|crecieron|cayeron|invertirá|'
    r'valora|acuerdo|alianza|fusión|adquisición|ronda|capital|'
    r'creó|fundó|nació|inauguró|vendió|compró)', re.IGNORECASE
)

def is_substantive(text, min_len=160):
    t = clean_text(text)
    if len(t) < min_len: return False
    return bool(HAS_SUBSTANCE.search(t))


def _clean_paras(section_body: str) -> list[str]:
    """Shared paragraph cleaning used by both snippet functions."""
    clean = clean_text(section_body)
    clean = COMMENTARY_RE.sub('', clean)
    clean = re.sub(r'^>\s*', '', clean, flags=re.MULTILINE)
    # Remove standalone horizontal rule lines (--- and * * *) left by Substack layout
    clean = re.sub(r'^\s*-{3,}\s*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\s*\*\s*\*\s*\*\s*$', '', clean, flags=re.MULTILINE)
    # Remove residual table separator artifacts (---|---|---)
    clean = re.sub(r'^\s*[-|]{3,}(\s*[-|]+)*\s*$', '', clean, flags=re.MULTILINE)
    # Strip Substack zero-width spacer sequences (U+034F, U+00AD repeating)
    clean = re.sub(r'[͏­​‌‍﻿]+', ' ', clean)
    clean = re.sub(r'[ \t]{2,}', ' ', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    paras = [p.strip() for p in re.split(r'\n{2,}', clean) if p.strip()]
    return [
        p for p in paras
        if len(p) > 50
        and not p.startswith('|')
        and not p.startswith('[')
        and 'substack.com' not in p.lower()
        and 'unsubscribe' not in p.lower()
        and not AD_RE.search(p[:200])
    ]


def get_snippet_for(section_body: str, company: str, max_chars=220) -> str:
    """
    Returns the first paragraph that directly mentions `company`.
    Kept short (220 chars) — used as preview only; full text lives in body.
    """
    paras = _clean_paras(section_body)
    pat   = re.compile(r'\b' + re.escape(company) + r'\b', re.IGNORECASE)
    for p in paras:
        if pat.search(p):
            s = re.sub(r'\s+', ' ', p).strip()
            return s[:max_chars] + ('…' if len(s) > max_chars else '')
    return ''


def get_snippet_fallback(section_body: str, max_chars=220) -> str:
    """
    FIX v4: used when company was matched via HEADING (not body).
    Returns the first substantive paragraph regardless of company mention.
    Short — just enough for a preview; full text goes in get_full_body().
    """
    paras = _clean_paras(section_body)
    for p in paras:
        if is_substantive(p, min_len=80):
            s = re.sub(r'\s+', ' ', p).strip()
            return s[:max_chars] + ('…' if len(s) > max_chars else '')
    for p in paras:
        if len(p) >= 120:
            s = re.sub(r'\s+', ' ', p).strip()
            return s[:max_chars] + ('…' if len(s) > max_chars else '')
    return ''


def get_full_body(section_body: str, max_chars: int = 8000) -> str:
    """
    Returns ALL substantive paragraphs joined with double newlines.
    Used for the accordion "read full article" expansion.
    Strips URL boilerplate and table rows but keeps editorial prose intact.
    """
    paras = _clean_paras(section_body)
    # Join all paragraphs with double newline so JS can split them into <p> tags
    result = "\n\n".join(re.sub(r'\s+', ' ', p).strip() for p in paras)
    if len(result) > max_chars:
        # Cut at last paragraph boundary before the limit
        cut = result.rfind('\n\n', 0, max_chars)
        result = result[:cut if cut > 0 else max_chars] + "\n\n…"
    return result


def make_headline(article_title, section_heading, company, body_snippet):
    """
    FIX v4: prefers article_title (H1) over section_heading for deep-dive
    articles, since H1 is the canonical story title written by the editor.
    """
    # Use H1 title when it clearly references the company (deep-dive)
    if article_title:
        at_lower = article_title.lower()
        co_lower = company.lower()
        if co_lower in at_lower or any(
            a in at_lower for a in (ALIASES.get(company) or [company.lower()])
        ):
            return article_title[:140]

    h = section_heading.strip()
    GENERIC = {
        'resultados','anuncios','noticias','actualización','update',
        'hoy','news','resumen','inversiones','lanzamiento','alianza',
        'empresas','startups','sector','mercado','movimiento','dato',
        'noticias de hoy','breves','breve','panorama','contexto',
    }
    if AD_RE.search(h):
        first = re.split(r'[.;]', body_snippet)[0].strip() if body_snippet else ''
        return (first[:100] + '…') if len(first) > 15 else f"{company}: nota"

    if h.lower() in GENERIC:
        first = re.split(r'[.;]', body_snippet)[0].strip() if body_snippet else ''
        if len(first) > 15:
            return first[:100] + ('…' if len(first) > 100 else '')
        return f"{company}: {h}"

    # If section heading IS the article subtitle (long descriptive line), use it
    return h[:140]


# ── ENTITY DETECTION ──────────────────────────────────────────────────────────
LEGAL_RE = re.compile(
    r'\b(S\.?A\.?(\s*de\s*C\.?V\.?)?|S\.?A\.?P\.?I\.?|S\.?C\.?|S\.?de\s*R\.?L\.?'
    r'|S\.?A\.?B\.?|Inc\.?|Corp\.?|LLC\.?|Ltd\.?)\b\.?', re.IGNORECASE)
STRIP_RE = re.compile(r'^[\s\"\'\(\)\[\]]+|[\s\"\'\(\)\[\].]+$')

def clean_entity(name):
    name = LEGAL_RE.sub('', name)
    name = STRIP_RE.sub('', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def find_companies_in_heading(heading: str) -> set[str]:
    """
    FIX v4 — Hybrid matching: scan heading text for company names and aliases.
    Returns canonical names.
    """
    found = set()
    h_lower = heading.lower()

    # Priority list exact match
    for co in PRIORITY:
        if _PRIORITY_PATTERNS[co].search(heading):
            canon = CANONICALS.get(co.lower(), co)
            found.add(canon)

    # Alias reverse map (substring match in heading)
    for alias_lower, canonical in _ALIAS_REVERSE.items():
        if alias_lower in h_lower:
            found.add(canonical)

    return found


def find_companies_in_body(body: str) -> set[str]:
    """
    Returns set of canonical company names found in BODY only.
    """
    found = set()

    # 1. Priority list
    for co in PRIORITY:
        if _PRIORITY_PATTERNS[co].search(body):
            canon = CANONICALS.get(co.lower(), co)
            found.add(canon)

    # 2. spaCy ORG entities
    chunk = clean_text(body)[:5000]
    if len(chunk) > 30:
        doc = nlp(chunk)
        for ent in doc.ents:
            if ent.label_ != "ORG": continue
            raw = ent.text.strip()
            if len(raw) < 3: continue
            c = clean_entity(raw)
            if not c or len(c) < 3: continue
            low = c.lower()
            if low in BLACKLIST: continue
            if c == c.lower() and len(c.split()) == 1: continue
            if re.match(r'^[\d\s.,]+$', c): continue
            canon = CANONICALS.get(low, c)
            if canon.lower() in BLACKLIST: continue
            found.add(canon)

    return found


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 60)
    print("extractor_v4.py — Chunking H1+H2, matching híbrido")
    print("=" * 60, flush=True)

    # ── 1. Parse newsletters ───────────────────────────────────────────────────
    print("\nPARSEANDO newsletters…", flush=True)
    all_newsletters = []

    for fname in sorted(os.listdir(MD_DIR)):
        if not fname.endswith('.md'): continue
        with open(os.path.join(MD_DIR, fname), 'r', encoding='utf-8') as f:
            raw = f.read()

        # FIX v4.1: re-join multi-block newsletters.
        # Substack uses `---` both as newsletter separator AND as in-article
        # horizontal rule (e.g. deep-dive articles). After splitting by `---`,
        # any block that has no **Date:** is part of the previous dated block.
        raw_blocks = re.split(r'\n---\n', raw)
        blocks: list[str] = []
        for rb in raw_blocks:
            if '**Date:**' in rb:
                blocks.append(rb)
            elif blocks:
                blocks[-1] = blocks[-1] + "\n\n" + rb
            # Orphaned no-date block before first email → discard

        count  = 0
        for block in blocks:
            date_str, year = parse_date(block)
            if not date_str: continue
            source   = parse_source(block)
            sections = parse_sections(block)
            if sections:
                all_newsletters.append((date_str, year, source, sections))
                count += 1
        print(f"  {fname}: {count} newsletters", flush=True)

    total_sections = sum(len(s) for _,_,_,s in all_newsletters)
    print(f"\n  Total newsletters : {len(all_newsletters)}")
    print(f"  Total secciones   : {total_sections}", flush=True)

    # ── 2. Extract events ──────────────────────────────────────────────────────
    print("\nEXTRAYENDO eventos por empresa…", flush=True)

    company_events = defaultdict(list)
    seen       = set()
    year_counts = defaultdict(lambda: defaultdict(int))
    stats = Counter()

    for idx, (date_str, year, source, sections) in enumerate(all_newsletters):
        if idx % 200 == 0:
            print(f"  [{idx}/{len(all_newsletters)}] {time.time()-t0:.0f}s…", flush=True)

        for article_title, heading, body in sections:
            if len(body.strip()) < 60:
                continue

            # Hybrid detection:
            # - heading_companies: matched via heading or alias (may differ from body)
            # - body_companies: matched strictly in body text
            heading_companies = find_companies_in_heading(heading)
            body_companies    = find_companies_in_body(body)
            all_companies     = heading_companies | body_companies

            if not all_companies:
                stats['no_companies'] += 1
                continue

            for co in all_companies:
                if year_counts[co][year] >= 6:   # raised cap slightly for deep-dives
                    continue

                key = (co, date_str, heading[:40])
                if key in seen:
                    continue

                from_heading = co in heading_companies and co not in body_companies

                if from_heading:
                    # FIX: heading-matched → use fallback snippet
                    snippet = get_snippet_fallback(body)
                    stats['heading_match'] += 1
                else:
                    snippet = get_snippet_for(body, co)

                if not snippet:
                    # Last resort: try any alias that might appear in body
                    for alias in (ALIASES.get(co) or []):
                        s = get_snippet_for(body, alias)
                        if s:
                            snippet = s
                            break

                if not snippet:
                    stats['no_snippet'] += 1
                    continue

                if len(snippet) < 120:
                    stats['short_snippet'] += 1
                    continue

                if not is_substantive(snippet, min_len=100):
                    stats['not_substantive'] += 1
                    continue

                seen.add(key)

                headline = make_headline(article_title, heading, co, snippet)
                if AD_RE.search(headline):
                    headline = re.split(r'[.;]', snippet)[0][:100]

                # Full body for accordion expansion
                full_body = get_full_body(body)

                cat  = classify_event(snippet + ' ' + headline, full_body)
                sent = classify_sentiment(snippet + ' ' + headline, cat)

                company_events[co].append({
                    "date":     date_str,
                    "cat":      cat,
                    "sentiment":sent,
                    "headline": headline,
                    "snippet":  snippet[:200],
                    "body":     full_body,
                    "quote":    extract_comment(body),
                    "source":   source,
                })
                year_counts[co][year] += 1

    elapsed = time.time() - t0
    print(f"\n  Extracción completada en {elapsed:.1f}s")
    print(f"  Entidades únicas        : {len(company_events)}")
    print(f"  Heading-match (fallback): {stats['heading_match']}")
    print(f"  Omitidos (sin snippet)  : {stats['no_snippet']}")
    print(f"  Omitidos (muy corto)    : {stats['short_snippet']}")
    print(f"  Omitidos (sin sustancia): {stats['not_substantive']}")

    # ── 2b. Post-dedup: same (date, headline) → keep longest body ─────────────
    for co in company_events:
        best: dict[tuple, dict] = {}
        for ev in company_events[co]:
            k = (ev['date'], ev['headline'].lower().strip())
            if k not in best or len(ev.get('body','')) > len(best[k].get('body','')):
                best[k] = ev
        company_events[co] = list(best.values())

    # ── 3. Filter and rank ─────────────────────────────────────────────────────
    print("\nFILTRANDO y construyendo dataset final…")
    filtered = {k: v for k, v in company_events.items() if len(v) >= 2}
    for k in filtered:
        filtered[k].sort(key=lambda e: e['date'])

    ranked = sorted(filtered.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"  Empresas con ≥2 eventos: {len(ranked)}")

    print("\nTop 20 empresas:")
    for name, evs in ranked[:20]:
        yrs = Counter(e['date'][:4] for e in evs)
        dist = " | ".join(f"{y}:{n}" for y, n in sorted(yrs.items()))
        print(f"  {name:<35} {len(evs):3d} ev  [{dist}]")

    # ── 4. Build COMPANIES array ───────────────────────────────────────────────
    def summary(name, sector, events):
        total = len(events)
        years = sorted({e['date'][:4] for e in events})
        period = f"{years[0]}–{years[-1]}" if len(years) > 1 else years[0]
        cats   = Counter(e['cat'] for e in events)
        tc     = cats.most_common(1)[0][0]
        sents  = Counter(e['sentiment'] for e in events)
        tone   = ("mayormente positiva"    if sents['positive'] > sents['negative']
                  else "con momentos de tensión" if sents['negative'] > 0
                  else "neutral")
        return (f"<em>{name}</em> acumuló {total} registros entre {period} "
                f"en los newsletters de Whitepaper. Sector: <em>{sector}</em>. "
                f"Cobertura {tone}, con énfasis en <em>{tc}</em>.")

    companies_list = []
    for name, events in ranked:
        sector = SECTOR_MAP.get(name, "Corporativo / Negocios")
        city   = CITY_MAP.get(name, "México")
        color  = COLOR_MAP.get(sector, "#94A3B8")
        slug   = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        companies_list.append({
            "id":      slug,
            "name":    name,
            "sector":  sector,
            "city":    city,
            "color":   color,
            "summary": summary(name, sector, events),
            "entries": events,
        })

    total_events = sum(len(c['entries']) for c in companies_list)
    print(f"\n  Total eventos finales: {total_events}")

    # ── 5. KOF Validation ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VALIDACIÓN KOF (0 entradas contaminadas esperadas):")
    print("=" * 60)
    kof = next((c for c in companies_list if c['name'] == 'KOF'), None)
    if kof:
        print(f"  {len(kof['entries'])} eventos para KOF")
        for i, e in enumerate(kof['entries'][:4], 1):
            print(f"  [{i:02d}] {e['date']}  Snippet[:80]: {e['snippet'][:80]}")

    # ── 6. City Express Validation ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VALIDACIÓN City Express — debe incluir 'De City Express, a Norte 19':")
    print("=" * 60)
    ce = next((c for c in companies_list if c['name'] == 'City Express'), None)
    if not ce:
        print("  [!] City Express NO encontrada — revisar PRIORITY/CANONICALS")
    else:
        print(f"  {len(ce['entries'])} eventos para City Express\n")
        for i, e in enumerate(ce['entries'], 1):
            found_norte19 = 'norte 19' in e['headline'].lower() or \
                            'luis barrios' in e['snippet'].lower() or \
                            'estos son sus planes' in e['snippet'].lower()
            marker = " ← TARGET" if found_norte19 else ""
            print(f"  [{i:02d}] {e['date']}  [{e['cat']}]{marker}")
            print(f"       Titular: {e['headline'][:80]}")
            print(f"       Snippet: {e['snippet'][:120]}")
            print()

    # ── 7. Save extracted JSON ─────────────────────────────────────────────────
    with open(JSON_OUT, 'w', encoding='utf-8') as f:
        json.dump(companies_list, f, ensure_ascii=False, indent=2)
    print(f"\n✓ extracted_v4.json guardado ({os.path.getsize(JSON_OUT):,} bytes)")

    # ── 8. Update data.json for the dashboard ─────────────────────────────────
    print(f"\nActualizando {DATA_OUT}…")
    # Load existing data.json to preserve investment events
    try:
        with open(DATA_OUT, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        investment_data = existing.get("investment", [])
    except Exception:
        investment_data = []

    data_payload  = {"companies": companies_list, "investment": investment_data}
    data_str      = json.dumps(data_payload, ensure_ascii=False, separators=(',', ':'))
    with open(DATA_OUT, 'w', encoding='utf-8') as f:
        f.write(data_str)
    print(f"✓ data.json actualizado ({os.path.getsize(DATA_OUT):,} bytes)")

    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  extractor_v4.py — COMPLETADO                        ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║  Newsletters : {len(all_newsletters):<5}                           ║")
    print(f"║  Secciones   : {total_sections:<5}                           ║")
    print(f"║  Empresas    : {len(companies_list):<5}                           ║")
    print(f"║  Eventos     : {total_events:<5}                           ║")
    print(f"║  Tiempo      : {elapsed:.1f}s                            ║")
    print(f"╚══════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()
