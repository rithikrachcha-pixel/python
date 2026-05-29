"""
World Cup 2026 squad data.

For each of the 32 nations we define a curated list of well-known real players
(by position) and then top each squad up to 23 players with realistic,
region-appropriate generated names so every team has a full, valid squad.

Exported:
    SQUADS: list[dict]  ->  [{"nation": str, "group": str, "players": [ {...}, ... ]}]
    GROUPS: dict[str, list[str]]
    FIXTURES: list[dict]  -> group stage fixtures
"""

import random

# Deterministic generation so the DB seed is stable across runs.
random.seed(2026)

# 8 groups of 4 -> 32 nations
GROUPS = {
    "A": ["USA", "Mexico", "Canada", "Colombia"],
    "B": ["Brazil", "Argentina", "Uruguay", "Ecuador"],
    "C": ["France", "England", "Spain", "Portugal"],
    "D": ["Germany", "Netherlands", "Belgium", "Croatia"],
    "E": ["Italy", "Switzerland", "Denmark", "Serbia"],
    "F": ["Morocco", "Senegal", "Egypt", "Cameroon"],
    "G": ["Japan", "South Korea", "Australia", "Iran"],
    "H": ["Saudi Arabia", "Qatar", "Tunisia", "Algeria"],
}

# Squad shape: 3 GK, 8 DEF, 8 MID, 4 FWD = 23
SQUAD_SHAPE = {"GK": 3, "DEF": 8, "MID": 8, "FWD": 4}

# Price bands per position (millions)
PRICE_BANDS = {
    "GK": (4.5, 7.0),
    "DEF": (5.0, 12.0),
    "MID": (6.0, 14.0),
    "FWD": (7.0, 15.0),
}

# Curated real players. Each entry: (name, position, club, age, price)
# Stars get explicit prices; remaining slots are auto-filled.
CURATED = {
    "France": [
        ("Mike Maignan", "GK", "AC Milan", 29, 6.0),
        ("Theo Hernandez", "DEF", "AC Milan", 28, 8.0),
        ("Jules Kounde", "DEF", "Barcelona", 27, 8.5),
        ("William Saliba", "DEF", "Arsenal", 25, 9.0),
        ("Dayot Upamecano", "DEF", "Bayern Munich", 27, 7.5),
        ("Aurelien Tchouameni", "MID", "Real Madrid", 26, 9.5),
        ("Eduardo Camavinga", "MID", "Real Madrid", 23, 8.5),
        ("Antoine Griezmann", "MID", "Atletico Madrid", 35, 9.0),
        ("Kylian Mbappe", "FWD", "Real Madrid", 27, 15.0),
        ("Ousmane Dembele", "FWD", "PSG", 28, 10.5),
        ("Marcus Thuram", "FWD", "Inter", 28, 9.0),
    ],
    "England": [
        ("Jordan Pickford", "GK", "Everton", 32, 5.5),
        ("Kyle Walker", "DEF", "Man City", 36, 6.0),
        ("John Stones", "DEF", "Man City", 32, 6.5),
        ("Trent Alexander-Arnold", "DEF", "Real Madrid", 27, 8.0),
        ("Declan Rice", "MID", "Arsenal", 27, 9.5),
        ("Jude Bellingham", "MID", "Real Madrid", 23, 13.0),
        ("Phil Foden", "MID", "Man City", 26, 11.0),
        ("Bukayo Saka", "MID", "Arsenal", 25, 11.5),
        ("Harry Kane", "FWD", "Bayern Munich", 33, 13.0),
        ("Cole Palmer", "MID", "Chelsea", 24, 11.0),
        ("Marcus Rashford", "FWD", "Aston Villa", 28, 8.5),
    ],
    "Spain": [
        ("Unai Simon", "GK", "Athletic Bilbao", 29, 5.5),
        ("Dani Carvajal", "DEF", "Real Madrid", 34, 6.0),
        ("Robin Le Normand", "DEF", "Atletico Madrid", 29, 6.0),
        ("Pau Cubarsi", "DEF", "Barcelona", 19, 6.5),
        ("Rodri", "MID", "Man City", 30, 10.5),
        ("Pedri", "MID", "Barcelona", 23, 11.0),
        ("Gavi", "MID", "Barcelona", 21, 8.5),
        ("Fabian Ruiz", "MID", "PSG", 30, 7.5),
        ("Lamine Yamal", "FWD", "Barcelona", 19, 13.0),
        ("Nico Williams", "FWD", "Athletic Bilbao", 24, 10.0),
        ("Alvaro Morata", "FWD", "Como", 33, 7.5),
    ],
    "Portugal": [
        ("Diogo Costa", "GK", "Porto", 26, 6.0),
        ("Ruben Dias", "DEF", "Man City", 29, 7.5),
        ("Joao Cancelo", "DEF", "Al-Hilal", 32, 6.5),
        ("Nuno Mendes", "DEF", "PSG", 24, 7.0),
        ("Bruno Fernandes", "MID", "Man United", 31, 10.0),
        ("Vitinha", "MID", "PSG", 26, 9.0),
        ("Bernardo Silva", "MID", "Man City", 31, 9.0),
        ("Rafael Leao", "FWD", "AC Milan", 27, 10.5),
        ("Cristiano Ronaldo", "FWD", "Al-Nassr", 41, 9.0),
        ("Goncalo Ramos", "FWD", "PSG", 25, 7.5),
    ],
    "Brazil": [
        ("Alisson", "GK", "Liverpool", 33, 6.5),
        ("Ederson", "GK", "Man City", 33, 6.0),
        ("Marquinhos", "DEF", "PSG", 32, 6.5),
        ("Gabriel Magalhaes", "DEF", "Arsenal", 28, 7.0),
        ("Danilo", "DEF", "Flamengo", 35, 5.5),
        ("Casemiro", "MID", "Man United", 34, 7.0),
        ("Bruno Guimaraes", "MID", "Newcastle", 28, 9.0),
        ("Lucas Paqueta", "MID", "West Ham", 28, 7.5),
        ("Vinicius Junior", "FWD", "Real Madrid", 26, 14.0),
        ("Rodrygo", "FWD", "Real Madrid", 25, 11.0),
        ("Raphinha", "FWD", "Barcelona", 29, 11.5),
    ],
    "Argentina": [
        ("Emiliano Martinez", "GK", "Aston Villa", 33, 6.5),
        ("Nahuel Molina", "DEF", "Atletico Madrid", 28, 6.0),
        ("Cristian Romero", "DEF", "Tottenham", 28, 7.5),
        ("Nicolas Otamendi", "DEF", "Benfica", 38, 5.5),
        ("Rodrigo De Paul", "MID", "Atletico Madrid", 32, 7.5),
        ("Enzo Fernandez", "MID", "Chelsea", 25, 9.5),
        ("Alexis Mac Allister", "MID", "Liverpool", 27, 9.5),
        ("Lionel Messi", "FWD", "Inter Miami", 39, 12.0),
        ("Lautaro Martinez", "FWD", "Inter", 28, 11.5),
        ("Julian Alvarez", "FWD", "Atletico Madrid", 26, 11.0),
    ],
    "Uruguay": [
        ("Sergio Rochet", "GK", "Internacional", 33, 5.0),
        ("Ronald Araujo", "DEF", "Barcelona", 27, 7.0),
        ("Jose Maria Gimenez", "DEF", "Atletico Madrid", 31, 6.0),
        ("Federico Valverde", "MID", "Real Madrid", 27, 11.0),
        ("Manuel Ugarte", "MID", "Man United", 25, 6.5),
        ("Nicolas De La Cruz", "MID", "Flamengo", 29, 6.5),
        ("Darwin Nunez", "FWD", "Liverpool", 26, 9.0),
        ("Facundo Pellistri", "FWD", "Panathinaikos", 24, 6.0),
    ],
    "Ecuador": [
        ("Hernan Galindez", "GK", "Huracan", 39, 4.5),
        ("Piero Hincapie", "DEF", "Bayer Leverkusen", 24, 6.5),
        ("Pervis Estupinan", "DEF", "AC Milan", 28, 6.0),
        ("Moises Caicedo", "MID", "Chelsea", 24, 9.0),
        ("Kendry Paez", "MID", "Chelsea", 19, 6.0),
        ("Enner Valencia", "FWD", "Internacional", 36, 6.0),
    ],
    "USA": [
        ("Matt Turner", "GK", "Crystal Palace", 31, 5.0),
        ("Sergino Dest", "DEF", "PSV", 25, 6.0),
        ("Chris Richards", "DEF", "Crystal Palace", 26, 5.5),
        ("Antonee Robinson", "DEF", "Fulham", 28, 6.0),
        ("Tyler Adams", "MID", "Bournemouth", 27, 6.5),
        ("Weston McKennie", "MID", "Juventus", 27, 7.0),
        ("Yunus Musah", "MID", "AC Milan", 23, 6.5),
        ("Christian Pulisic", "FWD", "AC Milan", 27, 10.0),
        ("Gio Reyna", "MID", "Borussia Dortmund", 23, 6.5),
        ("Folarin Balogun", "FWD", "Monaco", 24, 7.5),
    ],
    "Mexico": [
        ("Guillermo Ochoa", "GK", "AVS", 40, 5.0),
        ("Cesar Montes", "DEF", "Lokomotiv Moscow", 28, 5.5),
        ("Jorge Sanchez", "DEF", "Cruz Azul", 28, 5.0),
        ("Edson Alvarez", "MID", "West Ham", 28, 7.0),
        ("Luis Romo", "MID", "Monterrey", 30, 5.5),
        ("Hirving Lozano", "FWD", "San Diego", 30, 7.5),
        ("Santiago Gimenez", "FWD", "AC Milan", 24, 8.0),
        ("Raul Jimenez", "FWD", "Fulham", 34, 6.5),
    ],
    "Canada": [
        ("Maxime Crepeau", "GK", "Portland Timbers", 31, 4.5),
        ("Alphonso Davies", "DEF", "Bayern Munich", 25, 9.0),
        ("Moise Bombito", "DEF", "Nice", 25, 5.5),
        ("Stephen Eustaquio", "MID", "Porto", 29, 6.0),
        ("Jonathan David", "FWD", "Juventus", 26, 9.0),
        ("Cyle Larin", "FWD", "Mallorca", 30, 6.0),
    ],
    "Colombia": [
        ("Camilo Vargas", "GK", "Atlas", 36, 4.5),
        ("Daniel Munoz", "DEF", "Crystal Palace", 29, 6.0),
        ("Davinson Sanchez", "DEF", "Galatasaray", 29, 6.0),
        ("James Rodriguez", "MID", "Leon", 34, 7.5),
        ("Jefferson Lerma", "MID", "Crystal Palace", 31, 5.5),
        ("Luis Diaz", "FWD", "Bayern Munich", 29, 11.0),
        ("Jhon Duran", "FWD", "Al-Nassr", 22, 7.0),
    ],
    "Germany": [
        ("Marc-Andre ter Stegen", "GK", "Barcelona", 33, 6.0),
        ("Antonio Rudiger", "DEF", "Real Madrid", 33, 7.0),
        ("Joshua Kimmich", "MID", "Bayern Munich", 31, 9.5),
        ("Jamal Musiala", "MID", "Bayern Munich", 23, 12.5),
        ("Florian Wirtz", "MID", "Liverpool", 23, 12.0),
        ("Ilkay Gundogan", "MID", "Man City", 35, 7.5),
        ("Kai Havertz", "FWD", "Arsenal", 27, 9.5),
        ("Leroy Sane", "FWD", "Galatasaray", 30, 8.5),
        ("Niclas Fullkrug", "FWD", "West Ham", 33, 7.0),
    ],
    "Netherlands": [
        ("Bart Verbruggen", "GK", "Brighton", 23, 5.5),
        ("Virgil van Dijk", "DEF", "Liverpool", 35, 7.5),
        ("Denzel Dumfries", "DEF", "Inter", 30, 6.5),
        ("Nathan Ake", "DEF", "Man City", 31, 6.0),
        ("Frenkie de Jong", "MID", "Barcelona", 29, 9.5),
        ("Tijjani Reijnders", "MID", "Man City", 27, 8.0),
        ("Cody Gakpo", "FWD", "Liverpool", 27, 9.5),
        ("Memphis Depay", "FWD", "Corinthians", 32, 7.5),
        ("Xavi Simons", "MID", "Tottenham", 23, 9.0),
    ],
    "Belgium": [
        ("Koen Casteels", "GK", "Al-Qadsiah", 33, 5.0),
        ("Wout Faes", "DEF", "Leicester", 28, 5.5),
        ("Zeno Debast", "DEF", "Sporting CP", 22, 5.5),
        ("Kevin De Bruyne", "MID", "Napoli", 35, 10.0),
        ("Youri Tielemans", "MID", "Aston Villa", 29, 7.0),
        ("Jeremy Doku", "FWD", "Man City", 24, 9.0),
        ("Romelu Lukaku", "FWD", "Napoli", 33, 8.5),
        ("Leandro Trossard", "FWD", "Arsenal", 31, 7.5),
    ],
    "Croatia": [
        ("Dominik Livakovic", "GK", "Fenerbahce", 31, 5.0),
        ("Josko Gvardiol", "DEF", "Man City", 24, 8.0),
        ("Josip Stanisic", "DEF", "Bayern Munich", 26, 5.5),
        ("Luka Modric", "MID", "AC Milan", 40, 7.5),
        ("Mateo Kovacic", "MID", "Man City", 32, 7.0),
        ("Marcelo Brozovic", "MID", "Al-Nassr", 33, 6.0),
        ("Andrej Kramaric", "FWD", "Hoffenheim", 35, 6.5),
    ],
    "Italy": [
        ("Gianluigi Donnarumma", "GK", "PSG", 27, 6.5),
        ("Alessandro Bastoni", "DEF", "Inter", 27, 7.0),
        ("Giovanni Di Lorenzo", "DEF", "Napoli", 32, 6.0),
        ("Federico Dimarco", "DEF", "Inter", 28, 6.5),
        ("Nicolo Barella", "MID", "Inter", 29, 8.5),
        ("Sandro Tonali", "MID", "Newcastle", 26, 7.5),
        ("Davide Frattesi", "MID", "Inter", 26, 6.5),
        ("Mateo Retegui", "FWD", "Al-Qadsiah", 26, 8.0),
        ("Federico Chiesa", "FWD", "Liverpool", 28, 7.5),
    ],
    "Switzerland": [
        ("Yann Sommer", "GK", "Inter", 37, 5.5),
        ("Manuel Akanji", "DEF", "Man City", 30, 6.5),
        ("Nico Elvedi", "DEF", "Monchengladbach", 29, 5.0),
        ("Granit Xhaka", "MID", "Bayer Leverkusen", 33, 7.0),
        ("Remo Freuler", "MID", "Bologna", 33, 5.5),
        ("Dan Ndoye", "FWD", "Nottingham Forest", 25, 6.5),
        ("Breel Embolo", "FWD", "Monaco", 29, 6.5),
    ],
    "Denmark": [
        ("Kasper Schmeichel", "GK", "Celtic", 39, 5.0),
        ("Joachim Andersen", "DEF", "Fulham", 29, 5.5),
        ("Joakim Maehle", "DEF", "Wolfsburg", 28, 5.0),
        ("Pierre-Emile Hojbjerg", "MID", "Marseille", 30, 6.5),
        ("Morten Hjulmand", "MID", "Sporting CP", 26, 6.0),
        ("Christian Eriksen", "MID", "Wolverhampton", 34, 6.5),
        ("Rasmus Hojlund", "FWD", "Napoli", 23, 8.0),
    ],
    "Serbia": [
        ("Vanja Milinkovic-Savic", "GK", "Torino", 28, 5.0),
        ("Nikola Milenkovic", "DEF", "Nottingham Forest", 28, 5.5),
        ("Strahinja Pavlovic", "DEF", "AC Milan", 24, 5.5),
        ("Sergej Milinkovic-Savic", "MID", "Al-Hilal", 31, 7.0),
        ("Filip Kostic", "MID", "Juventus", 33, 5.5),
        ("Dusan Vlahovic", "FWD", "Juventus", 26, 9.0),
        ("Aleksandar Mitrovic", "FWD", "Al-Hilal", 31, 8.0),
    ],
    "Morocco": [
        ("Yassine Bounou", "GK", "Al-Hilal", 35, 5.5),
        ("Achraf Hakimi", "DEF", "PSG", 27, 8.5),
        ("Noussair Mazraoui", "DEF", "Man United", 28, 6.0),
        ("Nayef Aguerd", "DEF", "Real Sociedad", 30, 5.5),
        ("Sofyan Amrabat", "MID", "Fenerbahce", 29, 6.0),
        ("Azzedine Ounahi", "MID", "Girona", 26, 5.5),
        ("Brahim Diaz", "MID", "Real Madrid", 26, 8.0),
        ("Youssef En-Nesyri", "FWD", "Fenerbahce", 28, 7.5),
    ],
    "Senegal": [
        ("Edouard Mendy", "GK", "Al-Ahli", 34, 5.5),
        ("Kalidou Koulibaly", "DEF", "Al-Hilal", 35, 6.0),
        ("Abdou Diallo", "DEF", "Al-Arabi", 30, 5.0),
        ("Ismail Jakobs", "DEF", "Galatasaray", 26, 5.0),
        ("Idrissa Gueye", "MID", "Everton", 36, 5.5),
        ("Pape Matar Sarr", "MID", "Tottenham", 23, 7.0),
        ("Sadio Mane", "FWD", "Al-Nassr", 34, 8.5),
        ("Nicolas Jackson", "FWD", "Chelsea", 24, 8.0),
    ],
    "Egypt": [
        ("Mohamed El Shenawy", "GK", "Al Ahly", 37, 4.5),
        ("Mohamed Abdelmonem", "DEF", "Al Ahly", 27, 5.0),
        ("Ahmed Hegazy", "DEF", "Al Ittihad", 35, 5.0),
        ("Mohamed Elneny", "MID", "Al Jazira", 33, 5.0),
        ("Mahmoud Trezeguet", "MID", "Al Ahly", 31, 5.5),
        ("Mohamed Salah", "FWD", "Liverpool", 33, 12.5),
        ("Omar Marmoush", "FWD", "Man City", 27, 9.0),
    ],
    "Cameroon": [
        ("Andre Onana", "GK", "Man United", 30, 5.5),
        ("Jean-Charles Castelletto", "DEF", "Nantes", 31, 4.5),
        ("Nouhou Tolo", "DEF", "Seattle Sounders", 29, 4.5),
        ("Andre-Frank Zambo Anguissa", "MID", "Napoli", 30, 7.0),
        ("Carlos Baleba", "MID", "Brighton", 22, 7.0),
        ("Bryan Mbeumo", "FWD", "Man United", 26, 8.0),
        ("Vincent Aboubakar", "FWD", "Hatayspor", 34, 5.5),
    ],
    "Japan": [
        ("Zion Suzuki", "GK", "Parma", 23, 5.0),
        ("Ko Itakura", "DEF", "Ajax", 29, 5.0),
        ("Takehiro Tomiyasu", "DEF", "Arsenal", 27, 5.5),
        ("Wataru Endo", "MID", "Liverpool", 33, 6.0),
        ("Daichi Kamada", "MID", "Crystal Palace", 30, 6.5),
        ("Takefusa Kubo", "MID", "Real Sociedad", 25, 8.0),
        ("Kaoru Mitoma", "FWD", "Brighton", 29, 8.5),
        ("Takumi Minamino", "FWD", "Monaco", 31, 6.0),
    ],
    "South Korea": [
        ("Kim Seung-gyu", "GK", "Al-Shabab", 35, 4.5),
        ("Kim Min-jae", "DEF", "Bayern Munich", 30, 7.0),
        ("Kim Young-gwon", "DEF", "Ulsan HD", 36, 4.5),
        ("Hwang In-beom", "MID", "Feyenoord", 29, 6.0),
        ("Lee Kang-in", "MID", "PSG", 25, 8.0),
        ("Son Heung-min", "FWD", "LAFC", 34, 9.5),
        ("Hwang Hee-chan", "FWD", "Wolverhampton", 30, 6.5),
    ],
    "Australia": [
        ("Mat Ryan", "GK", "Roma", 34, 4.5),
        ("Harry Souttar", "DEF", "Sheffield United", 27, 5.0),
        ("Kye Rowles", "DEF", "Hearts", 27, 4.5),
        ("Aiden O'Neill", "MID", "Standard Liege", 27, 5.0),
        ("Riley McGree", "MID", "Middlesbrough", 27, 5.0),
        ("Mathew Leckie", "FWD", "Melbourne City", 35, 5.0),
        ("Mitchell Duke", "FWD", "Machida Zelvia", 35, 4.5),
    ],
    "Iran": [
        ("Alireza Beiranvand", "GK", "Tractor", 33, 4.5),
        ("Sadegh Moharrami", "DEF", "Dinamo Zagreb", 29, 4.5),
        ("Majid Hosseini", "DEF", "Kayserispor", 29, 4.5),
        ("Saeid Ezatolahi", "MID", "Esteghlal", 29, 4.5),
        ("Alireza Jahanbakhsh", "MID", "Heerenveen", 32, 5.5),
        ("Mehdi Taremi", "FWD", "Inter", 33, 7.5),
        ("Sardar Azmoun", "FWD", "Shabab Al-Ahli", 31, 6.5),
    ],
    "Saudi Arabia": [
        ("Nawaf Al-Aqidi", "GK", "Al-Nassr", 25, 4.5),
        ("Sultan Al-Ghannam", "DEF", "Al-Nassr", 31, 4.5),
        ("Ali Al-Bulaihi", "DEF", "Al-Hilal", 36, 4.5),
        ("Mohamed Kanno", "MID", "Al-Hilal", 31, 5.0),
        ("Salem Al-Dawsari", "MID", "Al-Hilal", 34, 6.0),
        ("Firas Al-Buraikan", "FWD", "Al-Ahli", 26, 5.5),
        ("Saleh Al-Shehri", "FWD", "Al-Ittihad", 32, 5.0),
    ],
    "Qatar": [
        ("Meshaal Barsham", "GK", "Al-Sadd", 28, 4.5),
        ("Pedro Miguel", "DEF", "Al-Sadd", 35, 4.5),
        ("Boualem Khoukhi", "DEF", "Al-Arabi", 35, 4.5),
        ("Hassan Al-Haydos", "MID", "Al-Sadd", 35, 5.0),
        ("Akram Afif", "MID", "Al-Sadd", 29, 6.5),
        ("Almoez Ali", "FWD", "Al-Duhail", 29, 5.5),
        ("Ahmed Alaaeldin", "FWD", "Al-Gharafa", 32, 4.5),
    ],
    "Tunisia": [
        ("Aymen Dahmen", "GK", "CS Sfaxien", 28, 4.5),
        ("Montassar Talbi", "DEF", "Al-Khaleej", 27, 4.5),
        ("Yassine Meriah", "DEF", "Esperance", 33, 4.5),
        ("Aissa Laidouni", "MID", "Al-Wakrah", 29, 5.0),
        ("Ellyes Skhiri", "MID", "Eintracht Frankfurt", 30, 6.0),
        ("Hannibal Mejbri", "MID", "Burnley", 23, 5.5),
        ("Youssef Msakni", "FWD", "Al-Arabi", 35, 5.0),
    ],
    "Algeria": [
        ("Alexandre Oukidja", "GK", "Metz", 37, 4.5),
        ("Aissa Mandi", "DEF", "Lille", 34, 5.0),
        ("Ramy Bensebaini", "DEF", "Borussia Dortmund", 31, 5.5),
        ("Ismael Bennacer", "MID", "AC Milan", 28, 7.0),
        ("Nabil Bentaleb", "MID", "Lille", 31, 5.0),
        ("Riyad Mahrez", "FWD", "Al-Ahli", 35, 8.0),
        ("Mohamed Amoura", "FWD", "Wolfsburg", 26, 7.0),
    ],
}

# Region-appropriate filler name pools (first, last) for generating remaining
# squad members. Keyed by nation; falls back to a generic pool.
FIRST_NAMES = {
    "default": ["Alex", "Daniel", "Leo", "Marco", "Tomas", "Andre", "Luca",
                "Diego", "Nikola", "Stefan", "Pablo", "Ivan", "Adam", "Felix"],
    "Brazil": ["Joao", "Gabriel", "Lucas", "Matheus", "Pedro", "Bruno", "Felipe", "Rafael"],
    "Argentina": ["Juan", "Mateo", "Santiago", "Nicolas", "Joaquin", "Tomas", "Lucas"],
    "France": ["Lucas", "Hugo", "Matteo", "Nathan", "Theo", "Enzo", "Maxime"],
    "Germany": ["Leon", "Felix", "Jonas", "Maximilian", "Niklas", "Lukas", "Tim"],
    "Spain": ["Pablo", "Hugo", "Marcos", "Sergio", "Diego", "Adrian", "Carlos"],
    "Japan": ["Yuki", "Sho", "Ren", "Hiroki", "Daisuke", "Kenta", "Sota"],
    "South Korea": ["Min-jun", "Ji-ho", "Seo-jun", "Do-yoon", "Joon-ho", "Hyun-woo"],
    "Morocco": ["Youssef", "Anas", "Bilal", "Hamza", "Ayoub", "Reda", "Soufiane"],
    "Senegal": ["Mamadou", "Cheikh", "Ousmane", "Ibrahima", "Moussa", "Lamine"],
    "Egypt": ["Ahmed", "Mahmoud", "Mostafa", "Karim", "Amr", "Tarek"],
    "Saudi Arabia": ["Abdullah", "Fahad", "Khalid", "Saud", "Nasser", "Turki"],
    "Qatar": ["Khalid", "Hamad", "Jassim", "Mohammed", "Ali", "Tariq"],
}

LAST_NAMES = {
    "default": ["Silva", "Kovac", "Novak", "Muller", "Garcia", "Rossi", "Petrov",
                "Hansen", "Berg", "Costa", "Vargas", "Horvat", "Nowak"],
    "Brazil": ["Santos", "Oliveira", "Souza", "Costa", "Pereira", "Almeida", "Lima"],
    "Argentina": ["Gonzalez", "Rodriguez", "Fernandez", "Lopez", "Diaz", "Sosa"],
    "France": ["Bernard", "Dubois", "Moreau", "Laurent", "Girard", "Faure"],
    "Germany": ["Schmidt", "Wagner", "Becker", "Hofmann", "Weber", "Koch"],
    "Spain": ["Garcia", "Martinez", "Lopez", "Sanchez", "Gomez", "Ruiz"],
    "Japan": ["Tanaka", "Sato", "Suzuki", "Yamamoto", "Nakamura", "Watanabe"],
    "South Korea": ["Park", "Lee", "Choi", "Jung", "Kang", "Yoon"],
    "Morocco": ["El Amrani", "Bennani", "Tahiri", "Saidi", "Chakir", "Bouzid"],
    "Senegal": ["Diop", "Ndiaye", "Fall", "Sow", "Ba", "Sarr"],
    "Egypt": ["Hassan", "Ibrahim", "Mohamed", "Said", "Fathy", "Gomaa"],
    "Saudi Arabia": ["Al-Otaibi", "Al-Harbi", "Al-Qahtani", "Al-Shamrani", "Al-Dosari"],
    "Qatar": ["Al-Sulaiti", "Al-Hajri", "Al-Rawi", "Khoukhi", "Al-Ali"],
}

CLUBS = {
    "default": ["Local FC", "City United", "Athletic Club", "Sporting", "Rovers",
                "FC Domestic", "Olympic", "United SC"],
}


def _price_for(position):
    lo, hi = PRICE_BANDS[position]
    return round(random.uniform(lo, hi), 1)


def _gen_name(nation, used):
    firsts = FIRST_NAMES.get(nation, FIRST_NAMES["default"])
    lasts = LAST_NAMES.get(nation, LAST_NAMES["default"])
    for _ in range(50):
        name = f"{random.choice(firsts)} {random.choice(lasts)}"
        if name not in used:
            used.add(name)
            return name
    # fallback guaranteed-unique
    name = f"{random.choice(firsts)} {random.choice(lasts)} {len(used)}"
    used.add(name)
    return name


def _build_squad(nation):
    curated = CURATED.get(nation, [])
    players = []
    used_names = set()
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}

    for name, pos, club, age, price in curated:
        players.append({
            "name": name, "position": pos, "club": club,
            "age": age, "price": price,
        })
        used_names.add(name)
        counts[pos] += 1

    # Fill remaining slots to reach SQUAD_SHAPE
    for pos, target in SQUAD_SHAPE.items():
        while counts[pos] < target:
            name = _gen_name(nation, used_names)
            players.append({
                "name": name, "position": pos,
                "club": random.choice(CLUBS["default"]),
                "age": random.randint(20, 33),
                "price": _price_for(pos),
            })
            counts[pos] += 1

    return players


SQUADS = []
for group, nations in GROUPS.items():
    for nation in nations:
        SQUADS.append({
            "nation": nation,
            "group": group,
            "players": _build_squad(nation),
        })


def _build_fixtures():
    """Round-robin within each group: 6 matches per group, 48 total."""
    fixtures = []
    base_day = 11  # June 11, 2026 kickoff
    match_no = 0
    for group, teams in GROUPS.items():
        pairings = [
            (teams[0], teams[1]), (teams[2], teams[3]),
            (teams[0], teams[2]), (teams[1], teams[3]),
            (teams[0], teams[3]), (teams[1], teams[2]),
        ]
        for home, away in pairings:
            day = base_day + (match_no // 8)
            fixtures.append({
                "home_team": home,
                "away_team": away,
                "match_date": f"2026-06-{day:02d}",
                "stage": "group",
            })
            match_no += 1
    return fixtures


FIXTURES = _build_fixtures()
