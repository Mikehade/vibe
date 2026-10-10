"""Small built-in catalogue for FAKE_SERVICES mode (offline demos, tests, UI work).

Metadata is approximate and written for this project; artwork is generated SVG.
"""

N, P, D, M, H, A = (8, "Netflix"), (9, "Prime Video"), (337, "Disney Plus"), (1899, "Max"), (15, "Hulu"), (350, "Apple TV+")

# (id, type, title, year, genres, runtime, rating, votes, cert, providers, overview)
TITLES = [
    (9001, "movie", "Paddington 2", 2017, [10751, 35, 12], 104, 7.6, 3100, "PG", [P, N], "A kind-hearted bear takes a job to buy a gift and ends up framed for theft."),
    (9002, "movie", "The Grand Budapest Hotel", 2014, [35, 18], 100, 8.0, 15000, "R", [D, H], "A legendary concierge and his lobby boy get tangled up in a stolen painting."),
    (9003, "movie", "Knives Out", 2019, [9648, 35, 80], 130, 7.8, 13000, "PG-13", [P], "A detective untangles a wealthy family's lies after the patriarch's death."),
    (9004, "movie", "Spider-Man: Into the Spider-Verse", 2018, [16, 28, 878], 117, 8.4, 15000, "PG", [N, D], "A teenager discovers he is one of many spider-heroes across dimensions."),
    (9005, "movie", "Mad Max: Fury Road", 2015, [28, 12, 878], 121, 7.6, 22000, "R", [M], "A desert chase for freedom across a scorched wasteland."),
    (9006, "movie", "Arrival", 2016, [18, 878, 9648], 116, 7.6, 17000, "PG-13", [P, N], "A linguist is recruited to talk to visitors whose language bends time."),
    (9007, "movie", "My Neighbor Totoro", 1988, [16, 10751, 14], 86, 8.1, 8000, "G", [M], "Two sisters meet gentle forest spirits in the countryside."),
    (9008, "movie", "Chef", 2014, [35, 18], 115, 7.1, 3300, "R", [N], "A chef quits his job and rediscovers joy running a food truck."),
    (9009, "movie", "The Martian", 2015, [878, 12, 18], 144, 7.7, 20000, "PG-13", [D, H], "An astronaut stranded on Mars works the problem, one day at a time."),
    (9010, "movie", "Hunt for the Wilderpeople", 2016, [12, 35, 18], 101, 7.6, 2600, "PG-13", [H, P], "A foster kid and his grumpy uncle go on the run in the bush."),
    (9011, "movie", "Ocean's Eleven", 2001, [80, 53, 35], 116, 7.4, 12000, "PG-13", [M, N], "A charming crew plans to rob three casinos in one night."),
    (9012, "movie", "Inception", 2010, [28, 878, 12], 148, 8.4, 36000, "PG-13", [N, P], "A thief who steals secrets from dreams takes one last job."),
    (9013, "movie", "Coco", 2017, [16, 10751, 14], 105, 8.2, 19000, "PG", [D], "A boy who dreams of music journeys to the Land of the Dead."),
    (9014, "movie", "Top Gun: Maverick", 2022, [28, 18], 131, 8.2, 9000, "PG-13", [P], "A veteran pilot trains a new generation for an impossible mission."),
    (9015, "movie", "Everything Everywhere All at Once", 2022, [28, 12, 878], 140, 7.8, 7000, "R", [A, P], "A laundromat owner must connect with parallel versions of herself."),
    (9016, "movie", "The Princess Bride", 1987, [12, 10751, 14], 98, 7.7, 5000, "PG", [D], "A grandfather reads a tale of true love, pirates and giants."),
    (9017, "movie", "Get Out", 2017, [9648, 53, 27], 104, 7.6, 17000, "R", [N], "A weekend visit to meet the parents turns deeply unsettling."),
    (9018, "movie", "Wall-E", 2008, [16, 10751, 878], 98, 8.1, 19000, "G", [D], "A lonely robot on an abandoned Earth falls in love."),
    (9019, "movie", "Free Solo", 2018, [99], 100, 7.9, 1500, "PG-13", [D], "A climber attempts El Capitan with no ropes."),
    (9020, "movie", "Palm Springs", 2020, [35, 10749, 14], 90, 7.3, 2600, "R", [H], "Two wedding guests get stuck reliving the same day."),
    (9021, "movie", "Dune", 2021, [878, 12], 155, 7.8, 12000, "PG-13", [M], "A young heir is thrust into a war over a desert planet."),
    (9022, "movie", "Soul", 2020, [16, 10751, 35], 100, 8.0, 9000, "PG", [D], "A music teacher gets a second chance to find his spark."),
    (9023, "movie", "Baby Driver", 2017, [28, 80], 113, 7.5, 14000, "R", [N], "A getaway driver who lives by his playlist wants out."),
    (9024, "movie", "The Secret Life of Walter Mitty", 2013, [12, 35, 18], 114, 7.1, 7000, "PG", [D], "A daydreamer finally sets off on a real adventure."),
    (9101, "tv", "Ted Lasso", 2020, [35, 18], 33, 8.4, 3000, "TV-MA", [A], "An American football coach takes over an English soccer club."),
    (9102, "tv", "Brooklyn Nine-Nine", 2013, [35, 80], 22, 8.2, 4000, "TV-14", [N, H], "Detectives in a Brooklyn precinct solve crimes and crack jokes."),
    (9103, "tv", "Planet Earth II", 2016, [99], 50, 8.9, 1000, "TV-G", [P, D], "Stunning close-ups of wildlife across the planet."),
    (9104, "tv", "Bluey", 2018, [16, 10762, 10751], 8, 8.9, 900, "TV-Y", [D], "A playful puppy family turns everyday life into games."),
    (9105, "tv", "The Great British Bake Off", 2010, [10764], 60, 7.8, 600, "TV-PG", [N], "Amateur bakers compete in a tent in the English countryside."),
    (9106, "tv", "Severance", 2022, [18, 9648, 10765], 50, 8.4, 1500, "TV-MA", [A], "Office workers surgically split their work and home memories."),
    (9107, "tv", "Abbott Elementary", 2021, [35], 22, 8.0, 500, "TV-14", [H], "Teachers at an underfunded school keep showing up anyway."),
    (9108, "tv", "Avatar: The Last Airbender", 2005, [16, 10759, 10765], 24, 8.7, 4000, "TV-Y7", [N, P], "A young monk must master the elements to end a war."),
    (9109, "tv", "The Bear", 2022, [18, 35], 30, 8.2, 1200, "TV-MA", [H, D], "A fine-dining chef returns home to run the family sandwich shop."),
    (9110, "tv", "Only Murders in the Building", 2021, [35, 9648, 80], 32, 8.0, 1600, "TV-MA", [H, D], "Three neighbours start a true-crime podcast about a death next door."),
    (9111, "tv", "Queer Eye", 2018, [10764], 45, 7.6, 500, "TV-14", [N], "Five experts help someone reset their life."),
    (9112, "tv", "Arcane", 2021, [16, 10765, 10759], 40, 8.7, 4000, "TV-14", [N], "Two sisters end up on opposite sides of a city at war."),
]

LOGOS = {8: "/netflix.png", 9: "/prime.png", 337: "/disney.png", 1899: "/max.png", 15: "/hulu.png", 350: "/appletv.png"}
