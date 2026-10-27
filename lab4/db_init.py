import os
import re
import unicodedata

import psycopg

DSN = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS countries (
    id   serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    code char(2) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS prizes (
    id       serial PRIMARY KEY,
    category text NOT NULL CHECK (category IN (
        'physics', 'chemistry', 'medicine',
        'literature', 'peace', 'economics')),
    year     integer NOT NULL CHECK (year BETWEEN 1901 AND 2100),
    UNIQUE (category, year)
);

CREATE TABLE IF NOT EXISTS laureates (
    id         serial PRIMARY KEY,
    full_name  text NOT NULL,
    email      text NOT NULL UNIQUE,
    birth_year integer NOT NULL CHECK (birth_year BETWEEN 1800 AND 2100),
    country_id integer NOT NULL REFERENCES countries (id)
);

CREATE TABLE IF NOT EXISTS laureate_prizes (
    laureate_id integer NOT NULL
        REFERENCES laureates (id) ON DELETE CASCADE,
    prize_id    integer NOT NULL
        REFERENCES prizes (id) ON DELETE CASCADE,
    PRIMARY KEY (laureate_id, prize_id)
);
"""

COUNTRIES = [
    ("US", "United States"), ("GB", "United Kingdom"), ("DE", "Germany"),
    ("FR", "France"), ("PL", "Poland"), ("UA", "Ukraine"),
    ("CH", "Switzerland"), ("IN", "India"), ("JP", "Japan"),
    ("IT", "Italy"), ("RU", "Russia"), ("DK", "Denmark"),
    ("AT", "Austria"), ("BE", "Belgium"), ("CO", "Colombia"),
    ("ZA", "South Africa"), ("PK", "Pakistan"), ("IL", "Israel"),
]  # fmt: skip

# (full_name, birth_year, country_code, [(category, year), ...])
LAUREATES: list[tuple[str, int, str, list[tuple[str, int]]]] = [
    ("Albert Einstein", 1879, "DE", [("physics", 1921)]),
    ("Marie Curie", 1867, "PL", [("physics", 1903), ("chemistry", 1911)]),
    ("Pierre Curie", 1859, "FR", [("physics", 1903)]),
    ("Henri Becquerel", 1852, "FR", [("physics", 1903)]),
    ("Niels Bohr", 1885, "DK", [("physics", 1922)]),
    ("Max Planck", 1858, "DE", [("physics", 1918)]),
    ("Erwin Schrödinger", 1887, "AT", [("physics", 1933)]),
    ("Paul Dirac", 1902, "GB", [("physics", 1933)]),
    ("Werner Heisenberg", 1901, "DE", [("physics", 1932)]),
    ("Enrico Fermi", 1901, "IT", [("physics", 1938)]),
    ("Richard Feynman", 1918, "US", [("physics", 1965)]),
    ("Wilhelm Röntgen", 1845, "DE", [("physics", 1901)]),
    ("Hideki Yukawa", 1907, "JP", [("physics", 1949)]),
    ("Peter Higgs", 1929, "GB", [("physics", 2013)]),
    ("François Englert", 1932, "BE", [("physics", 2013)]),
    ("Ernest Rutherford", 1871, "GB", [("chemistry", 1908)]),
    ("Linus Pauling", 1901, "US", [("chemistry", 1954), ("peace", 1962)]),
    ("Frederick Sanger", 1918, "GB", [("chemistry", 1958), ("chemistry", 1980)]),
    ("Dorothy Hodgkin", 1910, "GB", [("chemistry", 1964)]),
    ("Fritz Haber", 1868, "DE", [("chemistry", 1918)]),
    ("Jennifer Doudna", 1964, "US", [("chemistry", 2020)]),
    ("Emmanuelle Charpentier", 1968, "FR", [("chemistry", 2020)]),
    ("Alexander Fleming", 1881, "GB", [("medicine", 1945)]),
    ("Howard Florey", 1898, "GB", [("medicine", 1945)]),
    ("Ernst Chain", 1906, "GB", [("medicine", 1945)]),
    ("Ivan Pavlov", 1849, "RU", [("medicine", 1904)]),
    ("Ilya Mechnikov", 1845, "UA", [("medicine", 1908)]),
    ("Paul Ehrlich", 1854, "DE", [("medicine", 1908)]),
    ("Robert Koch", 1843, "DE", [("medicine", 1905)]),
    ("James Watson", 1928, "US", [("medicine", 1962)]),
    ("Francis Crick", 1916, "GB", [("medicine", 1962)]),
    ("Maurice Wilkins", 1916, "GB", [("medicine", 1962)]),
    ("Shinya Yamanaka", 1962, "JP", [("medicine", 2012)]),
    ("John Gurdon", 1933, "GB", [("medicine", 2012)]),
    ("Ernest Hemingway", 1899, "US", [("literature", 1954)]),
    ("Rabindranath Tagore", 1861, "IN", [("literature", 1913)]),
    ("Thomas Mann", 1875, "DE", [("literature", 1929)]),
    ("Gabriel García Márquez", 1927, "CO", [("literature", 1982)]),
    ("Wisława Szymborska", 1923, "PL", [("literature", 1996)]),
    ("Czesław Miłosz", 1911, "PL", [("literature", 1980)]),
    ("Bob Dylan", 1941, "US", [("literature", 2016)]),
    ("Kazuo Ishiguro", 1954, "GB", [("literature", 2017)]),
    ("Olga Tokarczuk", 1962, "PL", [("literature", 2018)]),
    ("Mother Teresa", 1910, "IN", [("peace", 1979)]),
    ("Martin Luther King Jr.", 1929, "US", [("peace", 1964)]),
    ("Nelson Mandela", 1918, "ZA", [("peace", 1993)]),
    ("Frederik de Klerk", 1936, "ZA", [("peace", 1993)]),
    ("Barack Obama", 1961, "US", [("peace", 2009)]),
    ("Malala Yousafzai", 1997, "PK", [("peace", 2014)]),
    ("Kailash Satyarthi", 1954, "IN", [("peace", 2014)]),
    ("Lech Wałęsa", 1943, "PL", [("peace", 1983)]),
    ("Mikhail Gorbachev", 1931, "RU", [("peace", 1990)]),
    ("Andrei Sakharov", 1921, "RU", [("peace", 1975)]),
    ("Henry Dunant", 1828, "CH", [("peace", 1901)]),
    ("Frédéric Passy", 1822, "FR", [("peace", 1901)]),
    ("Paul Krugman", 1953, "US", [("economics", 2008)]),
    ("Milton Friedman", 1912, "US", [("economics", 1976)]),
    ("Amartya Sen", 1933, "IN", [("economics", 1998)]),
    ("Daniel Kahneman", 1934, "IL", [("economics", 2002)]),
    ("Vernon Smith", 1927, "US", [("economics", 2002)]),
]  # fmt: skip


def make_email(full_name: str) -> str:
    """Будує email виду albert.einstein@example.org з імені."""
    name = full_name.lower().replace("ł", "l")
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", ".", ascii_name).strip(".")
    return f"{slug}@example.org"


def init_db() -> None:
    with psycopg.connect(DSN) as conn:
        conn.execute(SCHEMA)

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO countries (code, name) VALUES (%s, %s) "
                "ON CONFLICT (code) DO NOTHING",
                COUNTRIES,
            )

            for full_name, birth_year, code, prizes in LAUREATES:
                cur.execute(
                    "INSERT INTO laureates "
                    "(full_name, email, birth_year, country_id) "
                    "VALUES (%s, %s, %s, "
                    "(SELECT id FROM countries WHERE code = %s)) "
                    "ON CONFLICT (email) DO UPDATE "
                    "SET full_name = EXCLUDED.full_name RETURNING id",
                    (full_name, make_email(full_name), birth_year, code),
                )
                row = cur.fetchone()
                assert row is not None
                laureate_id = row[0]

                for category, year in prizes:
                    cur.execute(
                        "INSERT INTO prizes (category, year) VALUES (%s, %s) "
                        "ON CONFLICT (category, year) DO NOTHING",
                        (category, year),
                    )
                    cur.execute(
                        "INSERT INTO laureate_prizes (laureate_id, prize_id) "
                        "SELECT %s, id FROM prizes "
                        "WHERE category = %s AND year = %s "
                        "ON CONFLICT DO NOTHING",
                        (laureate_id, category, year),
                    )
    # commit виконується автоматично при виході з блоку with

    print("База ініціалізована.")


if __name__ == "__main__":
    init_db()
