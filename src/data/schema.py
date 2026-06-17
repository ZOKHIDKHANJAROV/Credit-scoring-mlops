EXPECTED_COLUMNS = [
    "laufkont",
    "laufzeit",
    "moral",
    "verw",
    "hoehe",
    "sparkont",
    "beszeit",
    "rate",
    "famges",
    "buerge",
    "wohnzeit",
    "verm",
    "alter",
    "weitkred",
    "wohn",
    "bishkred",
    "beruf",
    "pers",
    "telef",
    "gastarb",
    "kredit",
]

TARGET_COLUMN = "kredit"

NUMERIC_COLUMNS = [
    "laufzeit",   # loan duration
    "hoehe",      # credit amount
    "rate",       # installment rate
    "wohnzeit",   # residence duration
    "alter",      # age
    "bishkred",   # number of existing credits
]

CATEGORICAL_COLUMNS = [
    "laufkont",
    "moral",
    "verw",
    "sparkont",
    "beszeit",
    "famges",
    "buerge",
    "verm",
    "weitkred",
    "wohn",
    "beruf",
    "pers",
    "telef",
    "gastarb",
]