"""
World Cup 2026 squad data — real 48-team format (Dec 2025 final draw).

Each nation is anchored on real, well-known players (curated from public squad
news as of May 2026) and topped up to a full 26-man squad with realistic,
region-appropriate generated names so every team is complete and valid.

Exported:
    GROUPS:   dict[str, list[str]]   -> 12 groups A..L, 4 nations each
    SQUADS:   list[dict]             -> [{"nation","group","players":[{...}]}]
    FIXTURES: list[dict]             -> group-stage round-robin fixtures
"""

import random

random.seed(2026)

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia-Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# 26-man squad: 3 GK, 9 DEF, 9 MID, 5 FWD
SQUAD_SHAPE = {"GK": 3, "DEF": 9, "MID": 9, "FWD": 5}

PRICE_BANDS = {
    "GK": (4.5, 7.0),
    "DEF": (5.0, 12.0),
    "MID": (6.0, 14.0),
    "FWD": (7.0, 15.0),
}

# Curated real players: (name, position, club, age, price)
CURATED = {
    "Mexico": [
        ("Guillermo Ochoa", "GK", "AVS", 40, 5.0),
        ("Julian Araujo", "DEF", "Bournemouth", 24, 5.5),
        ("Cesar Montes", "DEF", "Lokomotiv Moscow", 28, 5.5),
        ("Jorge Sanchez", "DEF", "Cruz Azul", 28, 5.0),
        ("Johan Vasquez", "DEF", "Genoa", 27, 5.5),
        ("Edson Alvarez", "MID", "Fenerbahce", 28, 7.0),
        ("Luis Romo", "MID", "Monterrey", 30, 5.5),
        ("Orbelin Pineda", "MID", "AEK Athens", 30, 6.0),
        ("Hirving Lozano", "FWD", "San Diego FC", 30, 7.5),
        ("Santiago Gimenez", "FWD", "AC Milan", 24, 8.5),
        ("Raul Jimenez", "FWD", "Fulham", 35, 6.5),
    ],
    "South Africa": [
        ("Ronwen Williams", "GK", "Mamelodi Sundowns", 33, 5.0),
        ("Siyanda Xulu", "DEF", "Sekhukhune", 33, 4.5),
        ("Nyiko Mobbie", "DEF", "Mamelodi Sundowns", 25, 4.5),
        ("Mothobi Mvala", "DEF", "Mamelodi Sundowns", 31, 4.5),
        ("Teboho Mokoena", "MID", "Mamelodi Sundowns", 28, 6.0),
        ("Themba Zwane", "MID", "Mamelodi Sundowns", 36, 5.5),
        ("Bongokuhle Hlongwane", "FWD", "Minnesota United", 25, 5.5),
        ("Lyle Foster", "FWD", "Burnley", 25, 6.5),
        ("Percy Tau", "FWD", "Qatar SC", 31, 5.5),
    ],
    "South Korea": [
        ("Kim Seung-gyu", "GK", "Al-Shabab", 35, 4.5),
        ("Kim Min-jae", "DEF", "Bayern Munich", 30, 7.5),
        ("Kim Young-gwon", "DEF", "Ulsan HD", 36, 4.5),
        ("Lee Jae-sung", "MID", "Mainz", 33, 6.0),
        ("Hwang In-beom", "MID", "Feyenoord", 29, 6.0),
        ("Lee Kang-in", "MID", "PSG", 25, 8.5),
        ("Son Heung-min", "FWD", "LAFC", 34, 10.0),
        ("Hwang Hee-chan", "FWD", "Wolverhampton", 30, 6.5),
        ("Oh Hyeon-gyu", "FWD", "Genk", 25, 5.5),
    ],
    "Czechia": [
        ("Jindrich Stanek", "GK", "Slavia Prague", 29, 5.0),
        ("Vladimir Coufal", "DEF", "Hoffenheim", 33, 5.0),
        ("Tomas Vlcek", "DEF", "Slavia Prague", 24, 4.5),
        ("David Zima", "DEF", "Slavia Prague", 25, 5.0),
        ("Tomas Soucek", "MID", "West Ham", 31, 7.0),
        ("Lukas Provod", "MID", "Slavia Prague", 29, 6.0),
        ("Antonin Barak", "MID", "Fiorentina", 31, 6.0),
        ("Adam Hlozek", "FWD", "Hoffenheim", 23, 7.0),
        ("Patrik Schick", "FWD", "Bayer Leverkusen", 30, 9.0),
    ],
    "Canada": [
        ("Maxime Crepeau", "GK", "Portland Timbers", 31, 4.5),
        ("Alphonso Davies", "DEF", "Bayern Munich", 25, 9.0),
        ("Moise Bombito", "DEF", "Nice", 25, 5.5),
        ("Derek Cornelius", "DEF", "Marseille", 28, 5.0),
        ("Alistair Johnston", "DEF", "Celtic", 27, 5.5),
        ("Stephen Eustaquio", "MID", "Porto", 29, 6.5),
        ("Ismael Kone", "MID", "Sassuolo", 23, 6.0),
        ("Tajon Buchanan", "MID", "Villarreal", 26, 6.5),
        ("Jonathan David", "FWD", "Juventus", 26, 9.5),
        ("Cyle Larin", "FWD", "Mallorca", 30, 6.0),
        ("Jonathan Osorio", "MID", "Toronto FC", 33, 5.5),
    ],
    "Bosnia-Herzegovina": [
        ("Nikola Vasilj", "GK", "St. Pauli", 30, 4.5),
        ("Sead Kolasinac", "DEF", "Atalanta", 32, 5.5),
        ("Amar Dedic", "DEF", "Benfica", 23, 6.0),
        ("Nihad Mujakic", "DEF", "Samsunspor", 27, 4.5),
        ("Miralem Pjanic", "MID", "CSKA Moscow", 35, 6.0),
        ("Edon Zhegrova", "MID", "Juventus", 26, 8.0),
        ("Benjamin Tahirovic", "MID", "Ajax", 22, 5.5),
        ("Edin Dzeko", "FWD", "Fiorentina", 40, 6.5),
        ("Ermedin Demirovic", "FWD", "Stuttgart", 28, 7.0),
    ],
    "Qatar": [
        ("Meshaal Barsham", "GK", "Al-Sadd", 28, 4.5),
        ("Pedro Miguel", "DEF", "Al-Sadd", 35, 4.5),
        ("Boualem Khoukhi", "DEF", "Al-Arabi", 35, 4.5),
        ("Tarek Salman", "DEF", "Al-Sadd", 28, 4.5),
        ("Hassan Al-Haydos", "MID", "Al-Sadd", 35, 5.0),
        ("Akram Afif", "MID", "Al-Sadd", 29, 7.0),
        ("Karim Boudiaf", "MID", "Al-Gharafa", 35, 4.5),
        ("Almoez Ali", "FWD", "Al-Duhail", 29, 6.0),
        ("Ahmed Alaaeldin", "FWD", "Al-Gharafa", 32, 4.5),
    ],
    "Switzerland": [
        ("Yann Sommer", "GK", "Inter", 37, 5.5),
        ("Manuel Akanji", "DEF", "Inter", 30, 6.5),
        ("Nico Elvedi", "DEF", "Borussia Monchengladbach", 29, 5.0),
        ("Ricardo Rodriguez", "DEF", "Real Betis", 33, 5.0),
        ("Granit Xhaka", "MID", "Sunderland", 33, 7.0),
        ("Remo Freuler", "MID", "Bologna", 33, 5.5),
        ("Xherdan Shaqiri", "MID", "FC Basel", 34, 6.0),
        ("Dan Ndoye", "FWD", "Nottingham Forest", 25, 7.0),
        ("Breel Embolo", "FWD", "Rennes", 29, 6.5),
        ("Ruben Vargas", "FWD", "Sevilla", 27, 6.0),
    ],
    "Brazil": [
        ("Alisson", "GK", "Liverpool", 33, 6.5),
        ("Ederson", "GK", "Fenerbahce", 32, 6.0),
        ("Marquinhos", "DEF", "PSG", 32, 6.5),
        ("Gabriel Magalhaes", "DEF", "Arsenal", 28, 7.5),
        ("Wesley", "DEF", "Roma", 22, 6.0),
        ("Vanderson", "DEF", "Monaco", 24, 5.5),
        ("Casemiro", "MID", "Man United", 34, 7.0),
        ("Bruno Guimaraes", "MID", "Newcastle", 28, 9.0),
        ("Lucas Paqueta", "MID", "West Ham", 28, 7.5),
        ("Vinicius Junior", "FWD", "Real Madrid", 26, 14.0),
        ("Rodrygo", "FWD", "Real Madrid", 25, 11.0),
        ("Raphinha", "FWD", "Barcelona", 29, 12.0),
        ("Estevao", "FWD", "Chelsea", 18, 9.0),
    ],
    "Morocco": [
        ("Yassine Bounou", "GK", "Al-Hilal", 35, 5.5),
        ("Achraf Hakimi", "DEF", "PSG", 27, 9.0),
        ("Noussair Mazraoui", "DEF", "Man United", 28, 6.0),
        ("Nayef Aguerd", "DEF", "Real Sociedad", 30, 5.5),
        ("Romain Saiss", "DEF", "Al-Shabab", 36, 5.0),
        ("Sofyan Amrabat", "MID", "Real Betis", 29, 6.0),
        ("Azzedine Ounahi", "MID", "Girona", 26, 5.5),
        ("Brahim Diaz", "MID", "Real Madrid", 26, 8.5),
        ("Youssef En-Nesyri", "FWD", "Fenerbahce", 28, 7.5),
        ("Hakim Ziyech", "FWD", "Al-Duhail", 33, 6.0),
        ("Eljif Elmas", "MID", "Leipzig", 26, 6.5),
    ],
    "Haiti": [
        ("Johny Placide", "GK", "Pau FC", 37, 4.5),
        ("Ricardo Ade", "DEF", "Beerschot", 30, 4.5),
        ("Carl Sainte", "DEF", "Real Esppor", 27, 4.5),
        ("Jems Geffrard", "DEF", "Hapoel Hadera", 30, 4.5),
        ("Danley Jean Jacques", "MID", "Metz", 25, 5.0),
        ("Leverton Pierre", "MID", "Violette", 24, 4.5),
        ("Frantzdy Pierrot", "FWD", "Cardiff City", 30, 6.0),
        ("Duckens Nazon", "FWD", "Al-Tadhamon", 31, 5.0),
        ("Don Deedson Louicius", "FWD", "Auxerre", 22, 5.0),
    ],
    "Scotland": [
        ("Angus Gunn", "GK", "Nottingham Forest", 29, 5.0),
        ("Andrew Robertson", "DEF", "Liverpool", 32, 6.5),
        ("Kieran Tierney", "DEF", "Celtic", 28, 6.0),
        ("Jack Hendry", "DEF", "Al-Ettifaq", 30, 5.0),
        ("Ryan Porteous", "DEF", "Watford", 27, 5.0),
        ("Scott McTominay", "MID", "Napoli", 29, 9.0),
        ("Billy Gilmour", "MID", "Napoli", 24, 6.0),
        ("John McGinn", "MID", "Aston Villa", 31, 7.0),
        ("Ryan Christie", "MID", "Bournemouth", 31, 5.5),
        ("Che Adams", "FWD", "Torino", 29, 6.5),
        ("Lyndon Dykes", "FWD", "Birmingham City", 30, 5.5),
    ],
    "United States": [
        ("Matt Turner", "GK", "New England Revolution", 31, 5.0),
        ("Sergino Dest", "DEF", "PSV", 25, 6.0),
        ("Chris Richards", "DEF", "Crystal Palace", 26, 5.5),
        ("Antonee Robinson", "DEF", "Fulham", 28, 6.5),
        ("Tim Ream", "DEF", "Charlotte FC", 38, 5.0),
        ("Tyler Adams", "MID", "Bournemouth", 27, 6.5),
        ("Weston McKennie", "MID", "Juventus", 27, 7.0),
        ("Yunus Musah", "MID", "Atalanta", 23, 6.5),
        ("Christian Pulisic", "FWD", "AC Milan", 27, 10.0),
        ("Folarin Balogun", "FWD", "Monaco", 24, 7.5),
        ("Gio Reyna", "MID", "Borussia Monchengladbach", 23, 6.5),
    ],
    "Paraguay": [
        ("Roberto Fernandez", "GK", "Olimpia", 26, 4.5),
        ("Gustavo Gomez", "DEF", "Palmeiras", 32, 5.5),
        ("Omar Alderete", "DEF", "Getafe", 29, 5.5),
        ("Fabian Balbuena", "DEF", "Corinthians", 34, 5.0),
        ("Andres Cubas", "MID", "Vancouver Whitecaps", 30, 5.5),
        ("Mathias Villasanti", "MID", "Gremio", 28, 5.5),
        ("Miguel Almiron", "MID", "Atlanta United", 32, 6.5),
        ("Julio Enciso", "FWD", "Ipswich Town", 22, 7.0),
        ("Antonio Sanabria", "FWD", "Cremonese", 30, 6.0),
        ("Diego Gomez", "MID", "Brighton", 22, 6.0),
    ],
    "Australia": [
        ("Mat Ryan", "GK", "Lens", 34, 4.5),
        ("Harry Souttar", "DEF", "Sheffield United", 27, 5.0),
        ("Kye Rowles", "DEF", "Hearts", 27, 4.5),
        ("Aziz Behich", "DEF", "Melbourne City", 35, 4.5),
        ("Cameron Burgess", "DEF", "Ipswich Town", 30, 4.5),
        ("Aiden O'Neill", "MID", "Standard Liege", 27, 5.0),
        ("Riley McGree", "MID", "Middlesbrough", 27, 5.0),
        ("Connor Metcalfe", "MID", "St. Pauli", 26, 5.0),
        ("Martin Boyle", "FWD", "Hibernian", 32, 5.0),
        ("Mitchell Duke", "FWD", "Machida Zelvia", 35, 4.5),
        ("Nestory Irankunda", "FWD", "Watford", 20, 5.5),
    ],
    "Turkiye": [
        ("Altay Bayindir", "GK", "Man United", 28, 5.0),
        ("Merih Demiral", "DEF", "Al-Ahli", 28, 5.5),
        ("Abdulkerim Bardakci", "DEF", "Galatasaray", 31, 5.0),
        ("Samet Akaydin", "DEF", "Panathinaikos", 31, 5.0),
        ("Ferdi Kadioglu", "DEF", "Brighton", 26, 6.0),
        ("Hakan Calhanoglu", "MID", "Inter", 32, 9.0),
        ("Arda Guler", "MID", "Real Madrid", 21, 9.5),
        ("Orkun Kokcu", "MID", "Benfica", 25, 7.0),
        ("Kenan Yildiz", "FWD", "Juventus", 21, 9.0),
        ("Yusuf Yazici", "MID", "Trabzonspor", 29, 6.0),
        ("Baris Alper Yilmaz", "FWD", "Galatasaray", 26, 6.5),
    ],
    "Germany": [
        ("Marc-Andre ter Stegen", "GK", "Barcelona", 33, 6.0),
        ("Oliver Baumann", "GK", "Hoffenheim", 35, 5.0),
        ("Antonio Rudiger", "DEF", "Real Madrid", 33, 7.0),
        ("Jonathan Tah", "DEF", "Bayern Munich", 30, 6.5),
        ("Joshua Kimmich", "MID", "Bayern Munich", 31, 9.5),
        ("Nico Schlotterbeck", "DEF", "Borussia Dortmund", 26, 6.5),
        ("Jamal Musiala", "MID", "Bayern Munich", 23, 12.5),
        ("Florian Wirtz", "MID", "Liverpool", 23, 12.0),
        ("Aleksandar Pavlovic", "MID", "Bayern Munich", 22, 7.0),
        ("Kai Havertz", "FWD", "Arsenal", 27, 9.5),
        ("Leroy Sane", "FWD", "Galatasaray", 30, 8.5),
        ("Niclas Fullkrug", "FWD", "West Ham", 33, 7.0),
    ],
    "Curacao": [
        ("Eloy Room", "GK", "Columbus Crew", 37, 4.5),
        ("Cuco Martina", "DEF", "RKC Waalwijk", 36, 4.5),
        ("Shurandy Sambo", "DEF", "PEC Zwolle", 25, 4.5),
        ("Juriaen Gaari", "DEF", "Vejle", 28, 4.5),
        ("Leandro Bacuna", "MID", "Adana Demirspor", 34, 5.0),
        ("Juninho Bacuna", "MID", "Kayserispor", 28, 5.0),
        ("Sontje Hansen", "MID", "NEC Nijmegen", 23, 5.5),
        ("Tahith Chong", "MID", "Sheffield United", 26, 5.5),
        ("Jurien Gaari", "FWD", "Vejle", 28, 4.5),
        ("Kenji Gorre", "FWD", "Sabah FK", 31, 5.0),
    ],
    "Ivory Coast": [
        ("Yahia Fofana", "GK", "Angers", 25, 4.5),
        ("Odilon Kossounou", "DEF", "Atalanta", 25, 6.0),
        ("Willy Boly", "DEF", "Al-Shabab", 35, 5.0),
        ("Ghislain Konan", "DEF", "Al-Wahda", 30, 4.5),
        ("Evan Ndicka", "DEF", "Roma", 26, 6.0),
        ("Franck Kessie", "MID", "Al-Ahli", 29, 7.5),
        ("Seko Fofana", "MID", "Rennes", 30, 6.5),
        ("Ibrahim Sangare", "MID", "Nottingham Forest", 28, 6.5),
        ("Sebastien Haller", "FWD", "Utrecht", 31, 7.0),
        ("Nicolas Pepe", "FWD", "Villarreal", 30, 6.5),
        ("Simon Adingra", "FWD", "Sunderland", 24, 7.0),
    ],
    "Ecuador": [
        ("Hernan Galindez", "GK", "Huracan", 39, 4.5),
        ("Piero Hincapie", "DEF", "Arsenal", 24, 7.0),
        ("Pervis Estupinan", "DEF", "AC Milan", 28, 6.0),
        ("Joel Ordonez", "DEF", "Club Brugge", 21, 6.0),
        ("William Pacho", "DEF", "PSG", 24, 7.0),
        ("Moises Caicedo", "MID", "Chelsea", 24, 9.5),
        ("Kendry Paez", "MID", "Chelsea", 19, 6.5),
        ("Alan Franco", "MID", "Al-Rayyan", 27, 5.0),
        ("Enner Valencia", "FWD", "Pachuca", 36, 6.0),
        ("Kevin Rodriguez", "FWD", "Union SG", 26, 5.5),
        ("Gonzalo Plata", "FWD", "Flamengo", 25, 6.5),
    ],
    "Netherlands": [
        ("Bart Verbruggen", "GK", "Brighton", 23, 5.5),
        ("Virgil van Dijk", "DEF", "Liverpool", 35, 7.5),
        ("Denzel Dumfries", "DEF", "Inter", 30, 6.5),
        ("Nathan Ake", "DEF", "Man City", 31, 6.0),
        ("Micky van de Ven", "DEF", "Tottenham", 25, 6.5),
        ("Jurrien Timber", "DEF", "Arsenal", 24, 6.5),
        ("Frenkie de Jong", "MID", "Barcelona", 29, 9.5),
        ("Tijjani Reijnders", "MID", "Man City", 27, 8.5),
        ("Ryan Gravenberch", "MID", "Liverpool", 23, 8.0),
        ("Cody Gakpo", "FWD", "Liverpool", 27, 9.5),
        ("Memphis Depay", "FWD", "Corinthians", 32, 7.5),
        ("Xavi Simons", "MID", "Tottenham", 23, 9.0),
    ],
    "Japan": [
        ("Zion Suzuki", "GK", "Parma", 23, 5.5),
        ("Ko Itakura", "DEF", "Ajax", 29, 5.0),
        ("Takehiro Tomiyasu", "DEF", "Arsenal", 27, 5.5),
        ("Hiroki Ito", "DEF", "Bayern Munich", 27, 5.5),
        ("Takefusa Kubo", "MID", "Real Sociedad", 25, 8.5),
        ("Wataru Endo", "MID", "Liverpool", 33, 6.0),
        ("Hidemasa Morita", "MID", "Sporting CP", 31, 6.0),
        ("Daichi Kamada", "MID", "Crystal Palace", 30, 6.5),
        ("Kaoru Mitoma", "FWD", "Brighton", 29, 9.0),
        ("Takumi Minamino", "FWD", "Monaco", 31, 6.5),
        ("Ayase Ueda", "FWD", "Feyenoord", 27, 6.5),
    ],
    "Sweden": [
        ("Robin Olsen", "GK", "Aston Villa", 36, 4.5),
        ("Victor Lindelof", "DEF", "Aston Villa", 31, 5.5),
        ("Isak Hien", "DEF", "Aston Villa", 26, 6.0),
        ("Gabriel Gudmundsson", "DEF", "Leeds United", 26, 5.0),
        ("Emil Krafth", "DEF", "Newcastle", 31, 4.5),
        ("Lucas Bergvall", "MID", "Tottenham", 19, 7.5),
        ("Yasin Ayari", "MID", "Brighton", 22, 6.0),
        ("Anthony Elanga", "MID", "Newcastle", 23, 7.5),
        ("Dejan Kulusevski", "MID", "Tottenham", 25, 8.0),
        ("Alexander Isak", "FWD", "Liverpool", 26, 12.0),
        ("Viktor Gyokeres", "FWD", "Arsenal", 27, 11.5),
    ],
    "Tunisia": [
        ("Aymen Dahmen", "GK", "CS Sfaxien", 28, 4.5),
        ("Montassar Talbi", "DEF", "Al-Khaleej", 27, 5.0),
        ("Yassine Meriah", "DEF", "Esperance", 33, 4.5),
        ("Ali Abdi", "DEF", "Nice", 32, 4.5),
        ("Dylan Bronn", "DEF", "Salernitana", 30, 4.5),
        ("Aissa Laidouni", "MID", "Al-Wakrah", 29, 5.0),
        ("Ellyes Skhiri", "MID", "Eintracht Frankfurt", 30, 6.5),
        ("Hannibal Mejbri", "MID", "Burnley", 23, 5.5),
        ("Youssef Msakni", "FWD", "Al-Arabi", 35, 5.0),
        ("Elias Achouri", "FWD", "Copenhagen", 26, 5.5),
        ("Seifeddine Jaziri", "FWD", "Zamalek", 32, 5.0),
    ],
    "Belgium": [
        ("Thibaut Courtois", "GK", "Real Madrid", 33, 6.5),
        ("Wout Faes", "DEF", "Leicester", 28, 5.5),
        ("Zeno Debast", "DEF", "Sporting CP", 22, 5.5),
        ("Maxim De Cuyper", "DEF", "Brighton", 25, 5.5),
        ("Koni De Winter", "DEF", "AC Milan", 23, 5.5),
        ("Kevin De Bruyne", "MID", "Napoli", 35, 10.0),
        ("Youri Tielemans", "MID", "Aston Villa", 29, 7.5),
        ("Amadou Onana", "MID", "Aston Villa", 24, 7.0),
        ("Jeremy Doku", "FWD", "Man City", 24, 9.0),
        ("Romelu Lukaku", "FWD", "Napoli", 33, 8.5),
        ("Leandro Trossard", "FWD", "Arsenal", 31, 7.5),
    ],
    "Egypt": [
        ("Mohamed El Shenawy", "GK", "Al Ahly", 37, 4.5),
        ("Mohamed Abdelmonem", "DEF", "Al Ahly", 27, 5.0),
        ("Ahmed Hegazy", "DEF", "Al Ittihad", 35, 5.0),
        ("Omar Kamal", "DEF", "Al Ahly", 26, 4.5),
        ("Mohamed Elneny", "MID", "Al Jazira", 33, 5.0),
        ("Mahmoud Trezeguet", "MID", "Al Ahly", 31, 5.5),
        ("Mohamed Shawky", "MID", "Pyramids", 25, 4.5),
        ("Mohamed Salah", "FWD", "Liverpool", 33, 12.5),
        ("Omar Marmoush", "FWD", "Man City", 27, 9.5),
        ("Mostafa Mohamed", "FWD", "Nantes", 28, 6.0),
    ],
    "Iran": [
        ("Alireza Beiranvand", "GK", "Tractor", 33, 4.5),
        ("Sadegh Moharrami", "DEF", "Dinamo Zagreb", 29, 4.5),
        ("Majid Hosseini", "DEF", "Kayserispor", 29, 4.5),
        ("Shojae Khalilzadeh", "DEF", "Tractor", 36, 4.5),
        ("Saeid Ezatolahi", "MID", "Esteghlal", 29, 4.5),
        ("Alireza Jahanbakhsh", "MID", "Heerenveen", 32, 5.5),
        ("Mehdi Ghayedi", "MID", "Ittihad Kalba", 27, 5.0),
        ("Mehdi Taremi", "FWD", "Olympiacos", 33, 7.5),
        ("Sardar Azmoun", "FWD", "Shabab Al-Ahli", 31, 6.5),
        ("Saman Ghoddos", "MID", "Brentford", 32, 5.0),
    ],
    "New Zealand": [
        ("Max Crocombe", "GK", "Burton Albion", 32, 4.5),
        ("Tyler Bindon", "DEF", "Nottingham Forest", 20, 5.0),
        ("Michael Boxall", "DEF", "Minnesota United", 37, 4.5),
        ("Nando Pijnaker", "DEF", "Rosenborg", 26, 4.5),
        ("Finn Surman", "DEF", "Portland Timbers", 22, 4.5),
        ("Marko Stamenic", "MID", "Olympiacos", 23, 5.0),
        ("Joe Bell", "MID", "Viking", 26, 5.0),
        ("Matthew Garbett", "MID", "Torino", 23, 5.0),
        ("Chris Wood", "FWD", "Nottingham Forest", 34, 7.5),
        ("Ben Old", "FWD", "St. Mirren", 23, 5.0),
        ("Eli Just", "FWD", "Sonderjyske", 25, 4.5),
    ],
    "Spain": [
        ("Unai Simon", "GK", "Athletic Bilbao", 29, 5.5),
        ("David Raya", "GK", "Arsenal", 30, 5.5),
        ("Dani Carvajal", "DEF", "Real Madrid", 34, 6.0),
        ("Robin Le Normand", "DEF", "Atletico Madrid", 29, 6.0),
        ("Pau Cubarsi", "DEF", "Barcelona", 19, 6.5),
        ("Marc Cucurella", "DEF", "Chelsea", 27, 6.0),
        ("Rodri", "MID", "Man City", 30, 10.5),
        ("Pedri", "MID", "Barcelona", 23, 11.0),
        ("Fabian Ruiz", "MID", "PSG", 30, 7.5),
        ("Lamine Yamal", "FWD", "Barcelona", 19, 14.0),
        ("Nico Williams", "FWD", "Athletic Bilbao", 24, 10.0),
        ("Mikel Oyarzabal", "FWD", "Real Sociedad", 29, 8.0),
    ],
    "Cape Verde": [
        ("Vozinha", "GK", "AVS", 39, 4.5),
        ("Diney Borges", "DEF", "Casa Pia", 31, 4.5),
        ("Roberto Lopes", "DEF", "Shamrock Rovers", 33, 4.5),
        ("Stopira", "DEF", "Fehervar", 37, 4.5),
        ("Kenny Rocha", "DEF", "Hapoel Beer Sheva", 29, 4.5),
        ("Jamiro Monteiro", "MID", "San Jose Earthquakes", 32, 5.5),
        ("Deroy Duarte", "MID", "Sparta Rotterdam", 26, 5.0),
        ("Kevin Pina", "MID", "Casa Pia", 27, 5.0),
        ("Garry Rodrigues", "FWD", "PAOK", 35, 5.0),
        ("Ryan Mendes", "FWD", "Al-Wakrah", 35, 5.0),
        ("Bryan Teixeira", "FWD", "Boavista", 24, 5.0),
    ],
    "Saudi Arabia": [
        ("Nawaf Al-Aqidi", "GK", "Al-Nassr", 25, 4.5),
        ("Sultan Al-Ghannam", "DEF", "Al-Nassr", 31, 4.5),
        ("Ali Al-Bulaihi", "DEF", "Al-Hilal", 36, 4.5),
        ("Hassan Tambakti", "DEF", "Al-Hilal", 26, 5.0),
        ("Saud Abdulhamid", "DEF", "Roma", 26, 5.0),
        ("Mohamed Kanno", "MID", "Al-Hilal", 31, 5.0),
        ("Salem Al-Dawsari", "MID", "Al-Hilal", 34, 6.0),
        ("Nasser Al-Dawsari", "MID", "Al-Hilal", 27, 5.0),
        ("Firas Al-Buraikan", "FWD", "Al-Ahli", 26, 5.5),
        ("Saleh Al-Shehri", "FWD", "Al-Ittihad", 32, 5.0),
        ("Abdullah Al-Hamdan", "FWD", "Al-Hilal", 26, 5.0),
    ],
    "Uruguay": [
        ("Sergio Rochet", "GK", "Internacional", 33, 5.0),
        ("Ronald Araujo", "DEF", "Barcelona", 27, 7.0),
        ("Jose Maria Gimenez", "DEF", "Atletico Madrid", 31, 6.0),
        ("Mathias Olivera", "DEF", "Napoli", 28, 5.5),
        ("Nahitan Nandez", "DEF", "Al-Qadsiah", 30, 5.0),
        ("Federico Valverde", "MID", "Real Madrid", 27, 11.0),
        ("Manuel Ugarte", "MID", "Man United", 25, 6.5),
        ("Nicolas De La Cruz", "MID", "Flamengo", 29, 6.5),
        ("Rodrigo Bentancur", "MID", "Tottenham", 28, 6.5),
        ("Darwin Nunez", "FWD", "Al-Hilal", 26, 9.0),
        ("Federico Pellistri", "FWD", "Panathinaikos", 24, 6.0),
    ],
    "France": [
        ("Mike Maignan", "GK", "AC Milan", 30, 6.0),
        ("Brice Samba", "GK", "Rennes", 31, 5.0),
        ("Theo Hernandez", "DEF", "Al-Hilal", 28, 7.5),
        ("Jules Kounde", "DEF", "Barcelona", 27, 8.5),
        ("William Saliba", "DEF", "Arsenal", 25, 9.0),
        ("Dayot Upamecano", "DEF", "Bayern Munich", 27, 7.5),
        ("Aurelien Tchouameni", "MID", "Real Madrid", 26, 9.5),
        ("Eduardo Camavinga", "MID", "Real Madrid", 23, 8.5),
        ("Adrien Rabiot", "MID", "AC Milan", 31, 7.5),
        ("Kylian Mbappe", "FWD", "Real Madrid", 27, 15.0),
        ("Ousmane Dembele", "FWD", "PSG", 28, 11.0),
        ("Bradley Barcola", "FWD", "PSG", 23, 8.5),
        ("Michael Olise", "MID", "Bayern Munich", 24, 9.5),
    ],
    "Senegal": [
        ("Edouard Mendy", "GK", "Al-Ahli", 34, 5.5),
        ("Kalidou Koulibaly", "DEF", "Al-Hilal", 35, 6.0),
        ("Abdou Diallo", "DEF", "Al-Arabi", 30, 5.0),
        ("Ismail Jakobs", "DEF", "Galatasaray", 26, 5.0),
        ("Antoine Mendy", "DEF", "Nice", 21, 5.0),
        ("Idrissa Gueye", "MID", "Everton", 36, 5.5),
        ("Pape Matar Sarr", "MID", "Tottenham", 23, 7.0),
        ("Lamine Camara", "MID", "Monaco", 22, 6.5),
        ("Sadio Mane", "FWD", "Al-Nassr", 34, 8.5),
        ("Nicolas Jackson", "FWD", "Bayern Munich", 24, 8.0),
        ("Ismaila Sarr", "FWD", "Crystal Palace", 28, 7.0),
    ],
    "Iraq": [
        ("Jalal Hassan", "GK", "Al-Shorta", 31, 4.5),
        ("Merchas Doski", "DEF", "Duhok", 26, 4.5),
        ("Zaid Tahseen", "DEF", "Al-Quwa Al-Jawiya", 27, 4.5),
        ("Akam Hashim", "DEF", "Al-Shorta", 26, 4.5),
        ("Frans Putros", "DEF", "Umm Salal", 32, 4.5),
        ("Amir Al-Ammari", "MID", "Halmstad", 28, 5.0),
        ("Ibrahim Bayesh", "MID", "Al-Quwa Al-Jawiya", 28, 5.0),
        ("Osama Rashid", "MID", "Santa Clara", 33, 5.0),
        ("Aymen Hussein", "FWD", "Al-Najma", 29, 5.5),
        ("Ali Jasim", "FWD", "Como", 22, 6.0),
        ("Mohanad Ali", "FWD", "Al-Duhail", 25, 6.0),
    ],
    "Norway": [
        ("Orjan Nyland", "GK", "Sevilla", 35, 4.5),
        ("Kristoffer Ajer", "DEF", "Brentford", 27, 5.5),
        ("Leo Ostigard", "DEF", "Rennes", 26, 5.0),
        ("Julian Ryerson", "DEF", "Borussia Dortmund", 28, 5.5),
        ("David Moller Wolfe", "DEF", "AZ Alkmaar", 23, 5.0),
        ("Martin Odegaard", "MID", "Arsenal", 27, 10.0),
        ("Sander Berge", "MID", "Fulham", 27, 6.0),
        ("Patrick Berg", "MID", "Bodo/Glimt", 28, 5.5),
        ("Antonio Nusa", "FWD", "Leipzig", 20, 7.5),
        ("Erling Haaland", "FWD", "Man City", 25, 15.0),
        ("Alexander Sorloth", "FWD", "Atletico Madrid", 30, 8.0),
    ],
    "Argentina": [
        ("Emiliano Martinez", "GK", "Aston Villa", 33, 6.5),
        ("Nahuel Molina", "DEF", "Atletico Madrid", 28, 6.0),
        ("Cristian Romero", "DEF", "Tottenham", 28, 7.5),
        ("Nicolas Otamendi", "DEF", "Benfica", 38, 5.5),
        ("Nicolas Tagliafico", "DEF", "Lyon", 33, 5.5),
        ("Rodrigo De Paul", "MID", "Inter Miami", 32, 7.0),
        ("Enzo Fernandez", "MID", "Chelsea", 25, 9.5),
        ("Alexis Mac Allister", "MID", "Liverpool", 27, 9.5),
        ("Lionel Messi", "FWD", "Inter Miami", 39, 12.0),
        ("Lautaro Martinez", "FWD", "Inter", 28, 11.5),
        ("Julian Alvarez", "FWD", "Atletico Madrid", 26, 11.0),
        ("Franco Mastantuono", "MID", "Real Madrid", 18, 8.0),
    ],
    "Algeria": [
        ("Alexandre Oukidja", "GK", "Metz", 37, 4.5),
        ("Aissa Mandi", "DEF", "Lille", 34, 5.0),
        ("Ramy Bensebaini", "DEF", "Borussia Dortmund", 31, 5.5),
        ("Mohamed Amine Tougai", "DEF", "Esperance", 24, 4.5),
        ("Youcef Atal", "DEF", "Al-Sadd", 29, 5.0),
        ("Ismael Bennacer", "MID", "AC Milan", 28, 7.0),
        ("Nabil Bentaleb", "MID", "Lille", 31, 5.0),
        ("Houssem Aouar", "MID", "Ittihad", 27, 5.5),
        ("Riyad Mahrez", "FWD", "Al-Ahli", 35, 8.0),
        ("Mohamed Amoura", "FWD", "Wolfsburg", 26, 7.5),
        ("Said Benrahma", "FWD", "Neom", 30, 6.0),
    ],
    "Austria": [
        ("Patrick Pentz", "GK", "Brondby", 29, 4.5),
        ("David Alaba", "DEF", "Real Madrid", 33, 6.0),
        ("Kevin Danso", "DEF", "Tottenham", 27, 5.5),
        ("Maximilian Wober", "DEF", "Borussia Monchengladbach", 28, 5.0),
        ("Philipp Mwene", "DEF", "Mainz", 31, 4.5),
        ("Konrad Laimer", "MID", "Bayern Munich", 28, 6.5),
        ("Nicolas Seiwald", "MID", "Leipzig", 24, 6.0),
        ("Christoph Baumgartner", "MID", "Leipzig", 26, 7.0),
        ("Marcel Sabitzer", "MID", "Borussia Dortmund", 31, 6.5),
        ("Marko Arnautovic", "FWD", "Red Star Belgrade", 36, 5.5),
        ("Michael Gregoritsch", "FWD", "Freiburg", 31, 6.0),
    ],
    "Jordan": [
        ("Yazeed Abulaila", "GK", "Al-Ramtha", 31, 4.5),
        ("Salem Al-Ajalin", "DEF", "Al-Wehdat", 27, 4.5),
        ("Abdallah Nasib", "DEF", "Al-Faisaly", 29, 4.5),
        ("Yazan Al-Arab", "DEF", "Al-Wehdat", 28, 4.5),
        ("Ihsan Haddad", "DEF", "Al-Hussein", 27, 4.5),
        ("Nour Al-Rawabdeh", "MID", "Al-Wehdat", 24, 4.5),
        ("Noor Al-Rawabdeh", "MID", "Al-Faisaly", 26, 4.5),
        ("Mahmoud Al-Mardi", "MID", "Al-Hussein", 27, 4.5),
        ("Musa Al-Taamari", "FWD", "Montpellier", 28, 6.5),
        ("Yazan Al-Naimat", "FWD", "Al-Ahli", 26, 5.5),
        ("Ali Olwan", "FWD", "Zakho", 27, 5.0),
    ],
    "Portugal": [
        ("Diogo Costa", "GK", "Porto", 26, 6.0),
        ("Ruben Dias", "DEF", "Man City", 29, 7.5),
        ("Joao Cancelo", "DEF", "Al-Hilal", 32, 6.5),
        ("Nuno Mendes", "DEF", "PSG", 24, 7.5),
        ("Antonio Silva", "DEF", "Benfica", 22, 5.5),
        ("Bruno Fernandes", "MID", "Man United", 31, 10.0),
        ("Vitinha", "MID", "PSG", 26, 9.5),
        ("Bernardo Silva", "MID", "Man City", 31, 8.5),
        ("Joao Neves", "MID", "PSG", 21, 8.0),
        ("Rafael Leao", "FWD", "AC Milan", 27, 10.5),
        ("Cristiano Ronaldo", "FWD", "Al-Nassr", 41, 9.0),
        ("Goncalo Ramos", "FWD", "PSG", 25, 7.5),
    ],
    "Congo DR": [
        ("Lionel Mpasi", "GK", "Rodez", 30, 4.5),
        ("Chancel Mbemba", "DEF", "Lille", 31, 5.5),
        ("Arthur Masuaku", "DEF", "Sunderland", 32, 5.0),
        ("Gedeon Kalulu", "DEF", "Lorient", 28, 4.5),
        ("Joris Kayembe", "DEF", "Genk", 31, 4.5),
        ("Samuel Moutoussamy", "MID", "Nantes", 29, 5.0),
        ("Charles Pickel", "MID", "Cremonese", 28, 5.0),
        ("Aaron Wan-Bissaka", "DEF", "West Ham", 28, 6.0),
        ("Yoane Wissa", "FWD", "Newcastle", 29, 7.5),
        ("Cedric Bakambu", "FWD", "Real Betis", 34, 5.5),
        ("Silas Katompa", "FWD", "Stuttgart", 27, 6.5),
    ],
    "Uzbekistan": [
        ("Utkir Yusupov", "GK", "Pakhtakor", 30, 4.5),
        ("Abdukodir Khusanov", "DEF", "Man City", 22, 6.5),
        ("Rustamjon Ashurmatov", "DEF", "Gangwon", 29, 4.5),
        ("Sherzod Nasrullaev", "DEF", "Pakhtakor", 28, 4.5),
        ("Farrukh Sayfiev", "DEF", "Pakhtakor", 27, 4.5),
        ("Jaloliddin Masharipov", "MID", "Pakhtakor", 32, 5.0),
        ("Otabek Shukurov", "MID", "Al-Wakrah", 29, 5.0),
        ("Abbosbek Fayzullaev", "MID", "CSKA Moscow", 22, 6.0),
        ("Eldor Shomurodov", "FWD", "Roma", 30, 6.5),
        ("Igor Sergeev", "FWD", "Pakhtakor", 32, 5.0),
        ("Khojiakbar Alijonov", "MID", "Nasaf", 26, 5.0),
    ],
    "Colombia": [
        ("Camilo Vargas", "GK", "Atlas", 36, 4.5),
        ("Daniel Munoz", "DEF", "Crystal Palace", 29, 6.0),
        ("Davinson Sanchez", "DEF", "Galatasaray", 29, 6.0),
        ("Jhon Lucumi", "DEF", "Bologna", 27, 5.5),
        ("Johan Mojica", "DEF", "Mallorca", 33, 5.0),
        ("James Rodriguez", "MID", "Club Leon", 34, 7.5),
        ("Jefferson Lerma", "MID", "Crystal Palace", 31, 5.5),
        ("Richard Rios", "MID", "Benfica", 25, 6.5),
        ("Luis Diaz", "FWD", "Bayern Munich", 29, 11.0),
        ("Jhon Duran", "FWD", "Fenerbahce", 22, 7.5),
        ("Luis Sinisterra", "FWD", "Bournemouth", 26, 6.5),
    ],
    "England": [
        ("Jordan Pickford", "GK", "Everton", 32, 5.5),
        ("Dean Henderson", "GK", "Crystal Palace", 29, 5.0),
        ("Kyle Walker", "DEF", "Burnley", 36, 5.5),
        ("John Stones", "DEF", "Man City", 32, 6.0),
        ("Marc Guehi", "DEF", "Crystal Palace", 26, 6.0),
        ("Trent Alexander-Arnold", "DEF", "Real Madrid", 27, 7.5),
        ("Declan Rice", "MID", "Arsenal", 27, 9.5),
        ("Jude Bellingham", "MID", "Real Madrid", 23, 13.0),
        ("Phil Foden", "MID", "Man City", 26, 10.5),
        ("Bukayo Saka", "MID", "Arsenal", 25, 11.5),
        ("Harry Kane", "FWD", "Bayern Munich", 33, 13.0),
        ("Cole Palmer", "MID", "Chelsea", 24, 11.0),
        ("Jude Bellingham", "MID", "Real Madrid", 23, 13.0),
    ],
    "Croatia": [
        ("Dominik Livakovic", "GK", "Girona", 31, 5.0),
        ("Josko Gvardiol", "DEF", "Man City", 24, 8.0),
        ("Josip Stanisic", "DEF", "Bayern Munich", 26, 5.5),
        ("Borna Sosa", "DEF", "Ajax", 28, 5.0),
        ("Josip Sutalo", "DEF", "Ajax", 26, 5.5),
        ("Luka Modric", "MID", "AC Milan", 40, 7.5),
        ("Mateo Kovacic", "MID", "Man City", 32, 7.0),
        ("Luka Sucic", "MID", "Real Sociedad", 23, 6.0),
        ("Mario Pasalic", "MID", "Atalanta", 31, 6.0),
        ("Andrej Kramaric", "FWD", "Hoffenheim", 35, 6.5),
        ("Ante Budimir", "FWD", "Osasuna", 34, 6.5),
    ],
    "Ghana": [
        ("Lawrence Ati-Zigi", "GK", "St. Gallen", 29, 4.5),
        ("Alexander Djiku", "DEF", "Fenerbahce", 31, 5.0),
        ("Mohammed Salisu", "DEF", "Monaco", 26, 5.5),
        ("Gideon Mensah", "DEF", "Auxerre", 27, 4.5),
        ("Alidu Seidu", "DEF", "Rennes", 25, 5.0),
        ("Thomas Partey", "MID", "Villarreal", 32, 7.0),
        ("Mohammed Kudus", "MID", "Tottenham", 25, 9.0),
        ("Elisha Owusu", "MID", "Auxerre", 28, 5.0),
        ("Antoine Semenyo", "FWD", "Bournemouth", 26, 8.0),
        ("Jordan Ayew", "FWD", "Leicester", 34, 6.0),
        ("Inaki Williams", "FWD", "Athletic Bilbao", 31, 7.0),
    ],
    "Panama": [
        ("Orlando Mosquera", "GK", "Sporting San Miguelito", 31, 4.5),
        ("Andres Andrade", "DEF", "Colon", 33, 4.5),
        ("Edgardo Fariña", "DEF", "Plaza Amador", 26, 4.5),
        ("Cesar Blackman", "DEF", "Cracovia", 27, 4.5),
        ("Fidel Escobar", "DEF", "AEK Larnaca", 30, 4.5),
        ("Adalberto Carrasquilla", "MID", "Houston Dynamo", 27, 6.0),
        ("Aníbal Godoy", "MID", "San Jose Earthquakes", 36, 5.0),
        ("Cristian Martinez", "MID", "Aris", 28, 5.0),
        ("Jose Fajardo", "FWD", "Independiente", 30, 5.5),
        ("Ismael Diaz", "FWD", "Leon", 28, 6.0),
        ("Cecilio Waterman", "FWD", "Coquimbo Unido", 34, 5.0),
    ],
}

FIRST_NAMES = {
    "default": ["Alex", "Daniel", "Leo", "Marco", "Tomas", "Andre", "Luca",
                "Diego", "Nikola", "Stefan", "Pablo", "Ivan", "Adam", "Felix",
                "Mateo", "Hugo", "Samuel", "Victor", "Marcus", "Oscar"],
}

LAST_NAMES = {
    "default": ["Silva", "Kovac", "Novak", "Muller", "Garcia", "Rossi", "Petrov",
                "Hansen", "Berg", "Costa", "Vargas", "Horvat", "Nowak", "Santos",
                "Lopez", "Schmidt", "Ferreira", "Ivanov", "Andersson", "Tanaka"],
}

CLUBS_DEFAULT = ["Local FC", "City United", "Athletic Club", "Sporting",
                 "Rovers", "FC Domestic", "Olympic", "United SC", "Nacional"]


def _price_for(position):
    lo, hi = PRICE_BANDS[position]
    return round(random.uniform(lo, hi), 1)


def _gen_name(nation, used):
    firsts = FIRST_NAMES.get(nation, FIRST_NAMES["default"])
    lasts = LAST_NAMES.get(nation, LAST_NAMES["default"])
    for _ in range(80):
        name = f"{random.choice(firsts)} {random.choice(lasts)}"
        if name not in used:
            used.add(name)
            return name
    name = f"{random.choice(firsts)} {random.choice(lasts)} {len(used)}"
    used.add(name)
    return name


def _build_squad(nation):
    curated = CURATED.get(nation, [])
    players = []
    used = set()
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}

    for name, pos, club, age, price in curated:
        if name in used:          # guard against accidental dupes in curation
            continue
        if counts[pos] >= SQUAD_SHAPE[pos]:
            continue
        players.append({"name": name, "position": pos, "club": club,
                        "age": age, "price": price})
        used.add(name)
        counts[pos] += 1

    for pos, target in SQUAD_SHAPE.items():
        while counts[pos] < target:
            name = _gen_name(nation, used)
            players.append({"name": name, "position": pos,
                            "club": random.choice(CLUBS_DEFAULT),
                            "age": random.randint(20, 33),
                            "price": _price_for(pos)})
            counts[pos] += 1

    return players


SQUADS = []
for group, nations in GROUPS.items():
    for nation in nations:
        SQUADS.append({"nation": nation, "group": group,
                       "players": _build_squad(nation)})


def _build_fixtures():
    fixtures = []
    base_day = 11
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
                "home_team": home, "away_team": away,
                "match_date": f"2026-06-{day:02d}", "stage": "group",
            })
            match_no += 1
    return fixtures


FIXTURES = _build_fixtures()
