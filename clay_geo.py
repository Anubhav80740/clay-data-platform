"""
Per-country geography vocabulary for the partition planner.

size & revenue bands are GLOBAL (identical worldwide) and live in clay_lib.
Only geography is country-specific, so it lives here as a HIERARCHY:

  GEO[country] = {
    "states": { state: [cities] },   # cities are scoped to their state
    "postal": { city:  [zips]   },   # OPTIONAL, only for cities that can exceed
                                     #   5,000 in one industry (SF, NYC, ...)
  }

Why the hierarchy: when the planner splits a state it only checks *that state's*
cities (not the whole global list), and only a city's own ZIPs are checked. This
turns a state x city x postal cross-product into a scoped tree -> far fewer free
count-calls, and adding a city only costs calls when its state is actually split.

To add a country: add an entry with its admin-1 divisions (states) each mapped to
its major cities. Postal is optional. States with no cities -> `[]` (fine; they
fall through to size/revenue, which is what small states need anyway).
Countries with no entry fall back to size/revenue-only (lower coverage).
"""

US_STATES = {
    "California": [
            "San Francisco", "Los Angeles", "San Jose", "San Diego", "Palo Alto", "Mountain View", "Sunnyvale", "Santa Clara", "Irvine", "San Mateo", "Oakland", "Sacramento", "Berkeley", "Fremont", "Menlo Park", "Redwood City", "Santa Monica", "Pasadena", "Culver City", "El Segundo", "Cupertino", "Milpitas", "Campbell", "Foster City", "Emeryville", "San Rafael", "Carlsbad", "Long Beach", "Anaheim", "Santa Ana", "Fresno", "Walnut Creek", "Burlingame", "Costa Mesa", "Torrance", "Glendale", "Santa Barbara", "South San Francisco", "San Bruno", "Daly City", "San Carlos", "Belmont", "Los Gatos", "Los Altos", "Saratoga", "Santa Rosa", "Petaluma", "Novato", "San Ramon", "Pleasanton", "Dublin", "Livermore", "Hayward", "San Leandro", "Alameda", "Richmond", "Concord", "Beverly Hills", "West Hollywood", "Burbank", "Woodland Hills", "Thousand Oaks", "Ventura", "Encinitas", "La Jolla", "Chula Vista", "Escondido", "Oceanside", "Riverside", "Bakersfield", "Modesto", "Stockton", "Roseville", "Folsom", "Davis",
            "Santa Clarita", "El Cajon", "San Bernardino", "Northridge", "Garden Grove", "Simi Valley", "Upland", "Santa Cruz", "La Mesa", "Arcadia", "Gardena", "Palm Desert", "San Marcos", "San Pedro", "Tustin", "Fountain Valley", "Laguna Hills", "Calabasas", "Palm Springs", "Redondo Beach", "Westlake Village", "Camarillo", "Chatsworth", "Brentwood", "Danville", "West Covina", "San Luis Obispo", "Glendora", "San Clemente", "Covina", "Hemet", "Monterey", "Manhattan Beach", "San Gabriel", "Brea", "Auburn", "Marina del Rey", "Laguna Niguel", "Monterey Park", "Lodi", "Carmichael", "Yuba City", "Rocklin", "Lake Forest", "Grass Valley", "National City", "Yorba Linda", "Cerritos", "Mill Valley", "Poway", "Laguna Beach", "Diamond Bar", "San Fernando", "Santee", "Montebello", "Gilroy", "Apple Valley", "Norwalk", "Rancho Cordova", "Rosemead", "Fontana", "Moreno Valley", "Huntington Beach", "Oxnard", "Rancho Cucamonga", "Ontario", "Elk Grove", "Corona", "Lancaster", "Palmdale", "Salinas", "Pomona", "Orange", "Fullerton", "Visalia", "Victorville", "Vallejo", "Fairfield", "Murrieta", "Temecula", "Antioch", "Downey", "Inglewood", "Santa Maria", "El Monte", "Redding", "Chico", "Clovis", "Jurupa Valley", "Compton", "Mission Viejo", "Vista", "South Gate", "Vacaville", "Carson", "Hesperia", "Westminster", "Redlands", "Chino", "Newport Beach", "Whittier", "Hawthorne", "Citrus Heights", "Alhambra", "Tracy", "Indio", "Buena Park", "Lakewood", "Merced", "Napa", "Bellflower", "Turlock",
        ],
    "New York": [
            "New York", "Brooklyn", "Bronx", "Staten Island", "Queens", "Flushing", "Jamaica", "Astoria", "New Hyde Park", "Great Neck", "Forest Hills", "Westbury", "Smithtown", "Elmhurst", "Huntington", "Bay Shore", "East Meadow", "Jackson Heights", "Plainview", "Ridgewood", "Hicksville", "Floral Park", "Rockville Centre", "Long Island City", "Williamsville", "Manhasset", "Woodside", "Massapequa", "New City", "Bayside", "Farmingdale", "Huntington Station", "Syosset", "Commack", "Queens Village", "Corona", "Middle Village", "South Richmond Hill", "Merrick", "Lynbrook", "Fresh Meadows", "West Islip", "Deer Park", "Hauppauge", "Mineola", "Maspeth", "Rego Park", "Glen Cove", "Lindenhurst", "Wantagh", "Ronkonkoma", "East Elmhurst", "Dix Hills", "Ozone Park", "Whitestone", "Woodmere", "Richmond Hill", "West Hempstead", "Clifton Park", "Melville", "Brewster", "Spring Valley", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany", "New Rochelle", "Mount Vernon", "Schenectady", "Utica", "White Plains", "Hempstead", "Troy", "Niagara Falls", "Binghamton", "Freeport", "Valley Stream", "Long Beach", "Rome", "Ithaca", "Poughkeepsie", "Levittown", "Elmira", "Jamestown", "Garden City", "Scarsdale", "Rye", "Port Chester", "Middletown", "Newburgh", "Saratoga Springs", "Kingston", "Watertown", "Glens Falls", "Oneonta", "Plattsburgh",
        ],
    "Texas": [
            "Houston", "Dallas", "Austin", "San Antonio", "Fort Worth", "El Paso", "Arlington", "Corpus Christi", "Laredo", "Lubbock", "Garland", "Irving", "Amarillo", "Grand Prairie", "Brownsville", "McKinney", "Pasadena", "Killeen", "McAllen", "Waco", "Carrollton", "Midland", "Denton", "Abilene", "Beaumont", "Odessa", "Round Rock", "Richardson", "Tyler", "Lewisville", "College Station", "Pearland", "San Angelo", "Allen", "League City", "Sugar Land", "Longview", "Bryan", "Baytown", "Missouri City", "Flower Mound", "New Braunfels", "Conroe", "Temple", "Cedar Park", "Mansfield", "Georgetown", "Rowlett", "Port Arthur", "DeSoto", "Galveston", "Grapevine", "Bedford", "Wichita Falls", "San Marcos", "Pflugerville", "Harlingen", "Victoria", "Leander", "Spring", "Katy", "Mesquite", "Mission", "Humble", "Edinburg", "Richmond", "Cypress", "Tomball", "The Woodlands", "Hurst", "Burleson", "Pharr", "Rockwall", "Magnolia", "Weslaco", "Duncanville", "Lufkin", "Weatherford", "Keller", "Sherman", "Nacogdoches", "Addison", "Kerrville", "North Richland Hills", "Friendswood", "Granbury", "Webster", "Waxahachie", "Stafford", "Texarkana", "Orange", "Cedar Hill", "Southlake", "Boerne", "Alvin", "Bellaire", "La Porte", "Wylie", "Lake Jackson", "Montgomery", "Seguin", "Texas City", "Coppell", "Paris", "Cleburne", "Kyle", "Greenville", "Midlothian", "Dickinson", "Forney", "Haltom City", "Colleyville", "The Colony", "Angleton", "Eagle Pass", "Bastrop",
        ],
    "Washington": [
            "Seattle", "Bellevue", "Spokane", "Tacoma", "Vancouver", "Everett", "Olympia", "Kirkland", "Yakima", "Bellingham", "Renton", "Kent", "Federal Way", "Lynnwood", "Kennewick", "Puyallup", "Richland", "Auburn", "Redmond", "Issaquah", "Shoreline", "Spokane Valley", "Bothell", "Lakewood", "Edmonds", "Gig Harbor", "Bremerton", "Burien", "Mount Vernon", "Lacey", "Longview", "Wenatchee", "Pasco", "Silverdale", "Port Angeles", "Walla Walla", "Poulsbo", "Centralia", "Woodinville", "Arlington", "Marysville", "Des Moines", "Sammamish", "Mercer Island", "Tukwila", "Aberdeen", "Oak Harbor", "Port Townsend", "Mill Creek", "Mukilteo", "Camas", "Tumwater", "Pullman", "Ellensburg", "University Place", "Snohomish", "Maple Valley", "Mountlake Terrace", "Clarkston", "Moses Lake", "Port Orchard",
        ],
    "Massachusetts": [
            "Boston", "Cambridge", "Worcester", "Brookline", "Springfield", "Brockton", "Fall River", "Pittsfield", "Lowell", "Framingham", "Quincy", "Somerville", "Salem", "Waltham", "New Bedford", "Lynn", "Needham", "Concord", "Northampton", "Plymouth", "Wellesley", "Peabody", "Medford", "North Andover", "Woburn", "Lexington", "Beverly", "Hyannis", "Leominster", "Newtonville", "Holyoke", "Malden", "Newton", "Lawrence", "Taunton", "Braintree", "Chestnut Hill", "Natick", "Norwood", "Danvers", "Randolph", "Haverhill", "Methuen", "Dedham", "Arlington", "Attleboro", "Andover", "Westborough", "Winchester", "Weymouth", "Watertown", "West Springfield", "Melrose", "Marlborough", "Milton", "Belmont", "Amherst", "Chelmsford", "Wakefield", "Burlington", "Revere", "Newton Centre",
        ],
    "Illinois": [
            "Chicago", "Aurora", "Naperville", "Joliet", "Rockford", "Springfield", "Elgin", "Peoria", "Champaign", "Waukegan", "Cicero", "Bloomington", "Arlington Heights", "Evanston", "Decatur", "Schaumburg", "Bolingbrook", "Palatine", "Skokie", "Des Plaines", "Orland Park", "Tinley Park", "Oak Lawn", "Berwyn", "Mount Prospect", "Normal", "Wheaton", "Hoffman Estates", "Oak Park", "Downers Grove", "Elmhurst", "Glenview", "Lombard", "Buffalo Grove", "Moline",
        ],
    "Florida": [
            "Miami", "Tampa", "Orlando", "Fort Lauderdale", "Boca Raton", "Jacksonville", "St Petersburg", "Tallahassee", "Winter Park", "Miami Beach", "Miami Lakes", "Saint Petersburg", "Homestead", "Stuart", "Palm Beach Gardens", "North Miami Beach", "Vero Beach", "Fort Pierce", "Brandon", "South Miami", "Palm Harbor", "Panama City", "New Port Richey", "Port Saint Lucie", "Venice", "Lake Worth", "Orange Park", "Spring Hill", "Lake Mary", "Port St Lucie", "Sebring", "Ormond Beach", "Cutler Bay", "Clermont", "Port Charlotte", "Leesburg", "Oviedo", "Maitland", "Palm Coast", "St Augustine", "Hallandale Beach", "Lake Worth Beach", "Brooksville", "Oakland Park", "Lutz", "Fort Walton Beach", "Rockledge", "Lauderhill", "Lake City", "Pinellas Park", "Plant City", "Lauderdale Lakes", "Wesley Chapel", "Ocoee", "Winter Garden", "Palm Springs", "Key West", "Greenacres", "Cooper City", "Merritt Island", "Lehigh Acres", "Dunedin", "Hudson", "The Villages", "Valrico", "Hialeah", "Port St. Lucie", "Cape Coral", "Pembroke Pines", "Hollywood", "Gainesville", "Miramar", "Coral Springs", "Palm Bay", "West Palm Beach", "Clearwater", "Lakeland", "Pompano Beach", "Miami Gardens", "Davie", "Sunrise", "Deltona", "Plantation", "Largo", "Melbourne", "Boynton Beach", "Kissimmee", "Deerfield Beach", "Naples", "Sarasota", "Bradenton", "Ocala", "Fort Myers", "Delray Beach", "Daytona Beach", "Doral", "Coconut Creek", "Sanford", "Wellington", "North Miami", "Jupiter", "Port Orange", "Margate", "Weston", "Pensacola", "Tamarac", "Coral Gables", "Apopka", "Bonita Springs", "Titusville", "Winter Haven", "Altamonte Springs", "Aventura",
        ],
    "Colorado": ["Denver", "Boulder"],
    "Georgia": [
            "Augusta", "Columbus", "Macon", "Savannah", "Athens", "Sandy Springs", "Roswell", "Johns Creek", "Albany", "Warner Robins", "Alpharetta", "Marietta", "Valdosta", "Smyrna", "Dunwoody", "Rome", "East Point", "Milton", "Gainesville", "Peachtree City", "Newnan", "Douglasville", "Kennesaw", "LaGrange", "Statesboro", "Lawrenceville", "Duluth", "Stockbridge", "Carrollton", "Woodstock", "Canton", "Griffin", "Decatur", "Tucker", "Norcross","Atlanta"],
    "Arizona": ["Phoenix", "Chandler", "Scottsdale"],
    "Oregon": ["Portland"],
    "Pennsylvania": [
            "Mechanicsburg", "Bala-Cynwyd", "Langhorne", "Camp Hill", "Bryn Mawr", "Wynnewood", "Malvern", "Newtown", "Exton", "Chambersburg", "Wayne", "Huntingdon Valley", "Plymouth Meeting", "Jenkintown", "Yardley", "Hershey", "Danville", "Wexford", "Lansdale", "Havertown", "Elkins Park", "Uniontown", "Paoli", "North Wales", "Hanover", "Kingston", "Phoenixville", "Du Bois", "Upper Darby", "Meadville", "Newtown Square", "Collegeville", "Southampton", "Sewickley", "Kennett Square", "Downingtown", "Ambler", "Canonsburg", "East Stroudsburg", "Middleburg", "Willow Grove", "Springfield", "Levittown", "Blue Bell", "Conshohocken", "Abington", "Hermitage", "Coraopolis", "Horsham", "McKeesport", "Beaver", "Fort Washington", "Gibsonia", "Bethel Park", "Ephrata", "Broomall", "Cranberry Township", "Irwin", "Quakertown", "Allentown", "Erie", "Reading", "Scranton", "Bethlehem", "Lancaster", "Harrisburg", "York", "Altoona", "Wilkes-Barre", "Chester", "Williamsport", "Easton", "Lebanon", "Hazleton", "New Castle", "Johnstown", "Norristown", "Bensalem", "King of Prussia", "West Chester", "Doylestown", "Media", "Pottstown", "Carlisle", "State College", "Bloomsburg", "Indiana", "Butler", "Washington", "Greensburg", "Monroeville", "Bristol", "Pittsburgh", "Philadelphia",
        ],
    "North Carolina": [
            "Greensboro", "Winston-Salem", "Fayetteville", "Cary", "Wilmington", "High Point", "Concord", "Asheville", "Greenville", "Gastonia", "Jacksonville", "Chapel Hill", "Rocky Mount", "Burlington", "Huntersville", "Wilson", "Kannapolis", "Apex", "Hickory", "Wake Forest", "Indian Trail", "Mooresville", "Goldsboro", "Monroe", "Salisbury", "Matthews", "New Bern", "Sanford", "Cornelius", "Garner", "Statesville", "Thomasville","Charlotte", "Raleigh", "Durham"],
    "Tennessee": ["Nashville"],
    "Utah": ["Salt Lake City", "Provo"],
    "Minnesota": ["Minneapolis"],
    "Ohio": [
            "Beachwood", "Westlake", "West Chester", "Willoughby", "Chillicothe", "Berea", "Worthington", "Shaker Heights", "Portsmouth", "Mason", "Zanesville", "Perrysburg", "Lancaster", "Centerville", "Solon", "Sandusky", "Marietta", "Medina", "Hilliard", "Gahanna", "Massillon", "Athens", "Blue Ash", "Walnut Hills", "Chagrin Falls", "Powell", "Boardman", "Troy", "Miamisburg", "North Olmsted", "North Canton", "Ashland", "Canal Winchester", "Pickerington", "Maumee", "Kent", "Canfield", "Steubenville", "Garfield Heights", "Milford", "Ashtabula", "Marysville", "Wooster", "Springboro", "Warrensville Heights", "Xenia", "Maple Heights", "Defiance", "Mayfield Heights", "Rocky River", "East Liverpool", "Ironton", "Painesville", "Oregon", "New Albany", "Gallipolis", "University Heights", "Mount Vernon", "Ravenna", "Brecksville", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton", "Parma", "Canton", "Youngstown", "Lorain", "Hamilton", "Springfield", "Kettering", "Elyria", "Lakewood", "Cuyahoga Falls", "Middletown", "Euclid", "Newark", "Mansfield", "Mentor", "Beavercreek", "Cleveland Heights", "Strongsville", "Dublin", "Fairfield", "Findlay", "Warren", "Lima", "Huber Heights", "Westerville", "Marion", "Grove City", "Reynoldsburg", "Delaware", "Stow", "Brunswick", "Columbus",
        ],
    "Michigan": [
            "Grand Rapids", "Warren", "Sterling Heights", "Lansing", "Flint", "Dearborn", "Livonia", "Troy", "Westland", "Farmington Hills", "Kalamazoo", "Wyoming", "Southfield", "Rochester Hills", "Taylor", "Saint Clair Shores", "Pontiac", "Dearborn Heights", "Royal Oak", "Novi", "Battle Creek", "Saginaw", "Kentwood", "East Lansing", "Roseville", "Portage", "Midland", "Muskegon", "Lincoln Park", "Bay City", "Jackson", "Holland","Detroit", "Ann Arbor"],
    "New Jersey": [
            "Englewood", "Freehold", "Teaneck", "West Orange", "Voorhees", "Wayne", "Red Bank", "Somerset", "Paramus", "Livingston", "Marlton", "Ridgewood", "Union", "Manalapan", "Bloomfield", "Lawrenceville", "Mount Laurel", "Old Bridge", "North Bergen", "North Brunswick", "Piscataway", "Tinton Falls", "Somerville", "Westfield", "Moorestown", "Holmdel", "Metuchen", "Flemington", "Denville", "Bridgewater", "Belleville", "Woodbury", "Neptune", "Nutley", "Englewood Cliffs", "Sewell", "Morganville", "Sparta", "Florham Park", "Maplewood", "Clark", "Edgewater", "Medford", "Hillsborough", "Hamilton Square", "Long Branch", "Springfield", "Westwood", "Rutherford", "Rahway", "South Plainfield", "Hackettstown", "Summit", "Avenel", "Saddle Brook", "Cranford", "Secaucus", "Newton", "Somers Point", "Jackson", "Newark", "Paterson", "Elizabeth", "Edison", "Woodbridge", "Lakewood", "Toms River", "Hamilton", "Trenton", "Clifton", "Camden", "Brick", "Cherry Hill", "Passaic", "Union City", "Bayonne", "East Orange", "Vineland", "New Brunswick", "Hoboken", "Perth Amboy", "West New York", "Plainfield", "Hackensack", "Sayreville", "Kearny", "Linden", "Atlantic City", "Fort Lee", "Fair Lawn", "Princeton", "Morristown", "Parsippany", "Montclair", "Jersey City",
        ],
    "Virginia": [
            "Richmond", "Virginia Beach", "Alexandria", "Fairfax", "Norfolk", "Falls Church", "Chesapeake", "Woodbridge", "Fredericksburg", "Vienna", "Charlottesville", "Roanoke", "Newport News", "Hampton", "Manassas", "Portsmouth", "Lynchburg", "Springfield", "Annandale", "Leesburg", "Midlothian", "Winchester", "Williamsburg", "Suffolk", "Sterling", "McLean", "Glen Allen", "Herndon", "Ashburn", "Chantilly", "Mc Lean", "Danville", "Burke", "Centreville", "Harrisonburg", "Mechanicsville", "Gainesville", "Chester", "Martinsville", "Petersburg", "Abingdon", "Lorton", "Stafford", "Henrico", "Salem", "Colonial Heights", "Christiansburg", "Warrenton", "Chesterfield", "North Chesterfield", "Staunton", "Blacksburg", "Yorktown", "Great Falls", "Dumfries", "Fort Belvoir", "Waynesboro", "Farmville", "Richlands", "Forest", "Reston", "Arlington",
        ],
    "New Mexico": ["Santa Fe"],
    "Idaho": ["Boise"],
    "District of Columbia": ["Washington"],
    # remaining states (no city list needed -- small enough to split by size)
    "Maryland": [
            "Baltimore", "Columbia", "Germantown", "Silver Spring", "Waldorf", "Glen Burnie", "Ellicott City", "Frederick", "Dundalk", "Rockville", "Bethesda", "Gaithersburg", "Towson", "Bowie", "Aspen Hill", "Wheaton", "Bel Air", "Potomac", "Severn", "North Bethesda", "Catonsville", "Hagerstown", "Annapolis", "Odenton", "Severna Park", "Salisbury", "Laurel", "College Park", "Greenbelt", "Chevy Chase", "Owings Mills", "Pikesville", "Clarksburg", "Elkridge", "Crofton",], "Wisconsin": [], "Connecticut": [], "Nevada": [],
    "South Carolina": [], "Alabama": [], "Kentucky": [], "Louisiana": [],
    "Oklahoma": [], "Iowa": [], "Kansas": [], "Arkansas": [], "Mississippi": [],
    "Nebraska": [], "Indiana": [], "Missouri": [], "Hawaii": [],
    "New Hampshire": [], "Maine": [], "Rhode Island": [], "Montana": [],
    "Delaware": [], "South Dakota": [], "North Dakota": [], "Alaska": [],
    "Vermont": [], "Wyoming": [], "West Virginia": [],
}

# ZIP lists only for cities that can exceed 5,000 companies in a single industry.
US_POSTAL = {
    "San Francisco": [
        "94102", "94103", "94104", "94105", "94107", "94108", "94109", "94110",
        "94111", "94112", "94114", "94115", "94116", "94117", "94118", "94121",
        "94122", "94123", "94124", "94127", "94129", "94130", "94131", "94132",
        "94133", "94134", "94158",
    ],
    "New York": [
        "10001", "10002", "10003", "10004", "10005", "10006", "10007", "10009",
        "10010", "10011", "10012", "10013", "10014", "10016", "10017", "10018",
        "10019", "10020", "10021", "10022", "10023", "10024", "10025", "10026",
        "10027", "10028", "10029", "10036", "10038", "10065", "10128", "10280",
    ],
    "Los Angeles": [
        "90001", "90012", "90013", "90014", "90015", "90017", "90024", "90025",
        "90028", "90034", "90036", "90045", "90048", "90049", "90064", "90066",
        "90067", "90071", "90210", "90211", "90212", "90232", "90245", "90291",
        "90401", "90404", "90405", "91316", "91367", "91406", "91411", "91436",
    ],
}

CA_PROVINCES = {
    "Ontario": [
        "Toronto", "Ottawa", "Mississauga", "Brampton", "Markham", "Vaughan",
        "Richmond Hill", "Oakville", "Burlington", "Hamilton", "Waterloo",
        "Kitchener", "Cambridge", "Guelph", "London", "Windsor", "Kingston",
        "Barrie", "Oshawa", "Whitby", "Ajax", "Pickering", "Milton", "Newmarket",
        "Aurora", "North York", "Scarborough", "Etobicoke", "Thornhill",
        "Woodbridge", "Concord", "Stouffville", "Kanata",
    ],
    "British Columbia": [
        "Vancouver", "Victoria", "Burnaby", "Richmond", "Surrey", "Coquitlam",
        "Langley", "North Vancouver", "West Vancouver", "New Westminster",
        "Delta", "Kelowna", "Nanaimo", "Kamloops", "Abbotsford",
        "Port Coquitlam", "Maple Ridge",
    ],
    "Quebec": [
        "Montreal", "Quebec City", "Laval", "Gatineau", "Longueuil", "Sherbrooke",
        "Brossard", "Saint-Laurent", "Dollard-des-Ormeaux", "Trois-Rivieres",
    ],
    "Alberta": ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "Airdrie"],
    "Manitoba": ["Winnipeg"],
    "Saskatchewan": ["Saskatoon", "Regina"],
    "Nova Scotia": ["Halifax", "Dartmouth"],
    "New Brunswick": ["Fredericton", "Moncton", "Saint John"],
    "Newfoundland and Labrador": ["St. John's"],
    "Prince Edward Island": ["Charlottetown"],
    # territories -- tiny, split by size
    "Yukon": [], "Northwest Territories": [], "Nunavut": [],
}

# Canadian postal = first 3 chars (FSA). Only for metros that may exceed 5,000.
CA_POSTAL = {
    "Toronto": [
        "M5V", "M5H", "M5J", "M5X", "M5K", "M5L", "M4W", "M5A", "M5B", "M5C",
        "M5E", "M5G", "M5S", "M5T", "M5R", "M4Y", "M6J", "M6K", "M6G", "M6H",
        "M6P", "M4S", "M4P", "M2N", "M2J", "M1P", "M9W", "M8X", "M4L", "M6R",
    ],
    "Vancouver": [
        "V6B", "V6C", "V6E", "V6G", "V6A", "V6Z", "V5K", "V5L", "V5T", "V5Y",
        "V5Z", "V6H", "V6J", "V6K", "V6P", "V6R", "V6S", "V7X", "V7Y", "V6M",
    ],
    "Montreal": [
        "H2Y", "H3A", "H3B", "H3C", "H2Z", "H3G", "H2L", "H2X", "H3H", "H4C",
        "H2W", "H3J", "H4B", "H3K", "H2K", "H1Y", "H2J", "H3S", "H3T", "H4A",
    ],
}

# France: admin-1 = the 13 metropolitan REGIONS (LinkedIn-style names, accented).
FR_REGIONS = {
    "Île-de-France": [
        "Paris", "Boulogne-Billancourt", "Saint-Denis", "Nanterre", "Courbevoie",
        "Issy-les-Moulineaux", "Levallois-Perret", "Montreuil", "Versailles",
        "Neuilly-sur-Seine", "Créteil", "Rueil-Malmaison", "Vincennes", "Clichy",
        "Puteaux", "Suresnes", "Antony", "Cergy", "Massy", "Saint-Cloud",
        "Ivry-sur-Seine", "Gennevilliers", "Aubervilliers", "La Défense",
        # more IdF suburbs (poor size data -> keep the "rest" cell under the cap)
        "Saint-Ouen", "Pantin", "Montrouge", "Bagneux", "Malakoff", "Vanves",
        "Châtillon", "Clamart", "Meudon", "Fontenay-sous-Bois", "Charenton-le-Pont",
        "Saint-Germain-en-Laye", "Poissy", "Sartrouville", "Colombes",
        "Asnières-sur-Seine", "Argenteuil", "Vélizy-Villacoublay", "Vitry-sur-Seine",
        "Champigny-sur-Marne", "Villejuif", "Le Kremlin-Bicêtre", "Cachan",
        "Noisy-le-Grand", "Bobigny", "Bagnolet", "Sèvres", "Chaville", "Guyancourt",
        "Saint-Maur-des-Fossés", "Maisons-Alfort", "Alfortville", "Bezons",
    ],
    "Auvergne-Rhône-Alpes": [
        "Lyon", "Grenoble", "Villeurbanne", "Clermont-Ferrand", "Saint-Étienne",
        "Annecy", "Chambéry",
    ],
    "Provence-Alpes-Côte d'Azur": [
        "Marseille", "Nice", "Aix-en-Provence", "Toulon", "Sophia Antipolis",
        "Cannes", "Antibes",
    ],
    "Occitanie": ["Toulouse", "Montpellier", "Nîmes", "Perpignan"],
    "Nouvelle-Aquitaine": ["Bordeaux", "Pau", "Limoges", "Poitiers"],
    "Hauts-de-France": ["Lille", "Amiens", "Roubaix", "Villeneuve-d'Ascq"],
    "Grand Est": ["Strasbourg", "Nancy", "Metz", "Reims"],
    "Pays de la Loire": ["Nantes", "Angers", "Le Mans"],
    "Bretagne": ["Rennes", "Brest", "Lorient", "Vannes"],
    "Normandie": ["Rouen", "Caen", "Le Havre"],
    "Bourgogne-Franche-Comté": ["Dijon", "Besançon"],
    "Centre-Val de Loire": ["Tours", "Orléans"],
    "Corse": ["Ajaccio", "Bastia"],
}

# Paris arrondissement postal codes -- Paris is dense enough to need them.
FR_POSTAL = {
    "Paris": [
        "75001", "75002", "75003", "75004", "75005", "75006", "75007", "75008",
        "75009", "75010", "75011", "75012", "75013", "75014", "75015", "75016",
        "75017", "75018", "75019", "75020",
    ],
}

# REGION-level postal: splits the Île-de-France city-exclude remainder (the dense
# suburb long tail) by 5-digit postal codes. Full 5-digit codes work in Clay;
# these cover the inner-ring departments (92/93/94) + key tech hubs (78/91/95).
FR_STATE_POSTAL = {
    "Île-de-France": [
        # 92 Hauts-de-Seine
        "92100", "92110", "92120", "92130", "92140", "92150", "92160", "92170",
        "92190", "92200", "92210", "92220", "92230", "92240", "92250", "92260",
        "92270", "92290", "92300", "92310", "92320", "92330", "92340", "92350",
        "92400", "92500", "92600", "92700", "92800",
        # 93 Seine-Saint-Denis
        "93000", "93100", "93110", "93170", "93200", "93210", "93250", "93260",
        "93300", "93310", "93400", "93500", "93600", "93700", "93800",
        # 94 Val-de-Marne
        "94000", "94100", "94110", "94120", "94130", "94140", "94160", "94200",
        "94210", "94220", "94230", "94240", "94270", "94300", "94320", "94340",
        "94400", "94430", "94450", "94500", "94600", "94700", "94800",
        # 78 Yvelines / 91 Essonne / 95 Val-d'Oise (tech hubs)
        "78000", "78100", "78140", "78150", "78180", "78280", "78350", "78430",
        "91000", "91120", "91190", "91300", "91400", "91940",
        "95000", "95100", "95800", "95870",
    ],
}

# Netherlands: admin-1 = the 12 provinces. Clay uses ENGLISH names for the
# translated ones (North/South Holland, North Brabant); the rest are unchanged.
NL_PROVINCES = {
    "North Holland": [
        "Amsterdam", "Haarlem", "Amstelveen", "Hilversum", "Zaandam", "Alkmaar",
        "Hoofddorp", "Purmerend", "Bussum", "Diemen", "Velsen", "Beverwijk",
    ],
    "South Holland": [
        "Rotterdam", "The Hague", "Den Haag", "Leiden", "Delft", "Dordrecht",
        "Zoetermeer", "Gouda", "Schiedam", "Rijswijk", "Capelle aan den IJssel",
        "Alphen aan den Rijn", "Vlaardingen", "Spijkenisse",
    ],
    "Utrecht": ["Utrecht", "Amersfoort", "Nieuwegein", "Zeist", "Veenendaal",
                "Houten", "Woerden"],
    "North Brabant": ["Eindhoven", "Tilburg", "Breda", "'s-Hertogenbosch",
                      "Helmond", "Oss", "Roosendaal", "Veldhoven"],
    "Gelderland": ["Nijmegen", "Arnhem", "Apeldoorn", "Ede", "Wageningen",
                   "Doetinchem", "Zutphen"],
    "Overijssel": ["Enschede", "Zwolle", "Deventer", "Hengelo", "Almelo"],
    "Limburg": ["Maastricht", "Venlo", "Heerlen", "Sittard", "Roermond"],
    "Friesland": ["Leeuwarden", "Drachten", "Sneek"],
    "Groningen": ["Groningen"],
    "Drenthe": ["Assen", "Emmen", "Hoogeveen"],
    "Flevoland": ["Almere", "Lelystad"],
    "Zeeland": ["Middelburg", "Vlissingen", "Goes"],
}

# India: admin-1 = states/UTs (English names). Cities use LinkedIn's spelling
# (Bengaluru not Bangalore, Gurugram not Gurgaon, New Delhi not Delhi).
IN_STATES = {
    "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubli"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Navi Mumbai"],
    "Telangana": ["Hyderabad", "Secunderabad", "Warangal"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
    "Delhi": ["New Delhi"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat"],
    "Uttar Pradesh": ["Noida", "Greater Noida", "Ghaziabad", "Lucknow", "Kanpur"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode", "Ernakulam"],
    "West Bengal": ["Kolkata", "Howrah"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Gandhinagar"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur"],
    "Madhya Pradesh": ["Indore", "Bhopal"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada"],
    "Punjab": ["Mohali", "Ludhiana", "Amritsar", "Jalandhar"],
    "Chandigarh": ["Chandigarh"],
    "Bihar": ["Patna"], "Odisha": ["Bhubaneswar"], "Assam": ["Guwahati"],
    "Jharkhand": ["Ranchi"], "Uttarakhand": ["Dehradun"],
    "Chhattisgarh": ["Raipur"], "Goa": ["Panaji"],
    # remaining (small -> split by size)
    "Himachal Pradesh": [], "Jammu and Kashmir": [], "Puducherry": [],
    "Tripura": [], "Meghalaya": [], "Manipur": [], "Nagaland": [],
    "Mizoram": [], "Arunachal Pradesh": [], "Sikkim": [],
}

IN_POSTAL = {
    "Bengaluru": [
        "560001", "560002", "560003", "560004", "560005", "560008", "560009",
        "560010", "560011", "560017", "560018", "560020", "560022", "560025",
        "560027", "560029", "560030", "560032", "560033", "560034", "560035",
        "560037", "560038", "560040", "560041", "560042", "560043", "560045",
        "560046", "560047", "560048", "560050", "560051", "560052", "560053",
        "560054", "560055", "560058", "560059", "560061", "560064", "560066",
        "560068", "560070", "560071", "560072", "560076", "560078", "560085",
        "560087", "560092", "560093", "560095", "560097", "560098", "560099",
        "560100", "560102", "560103",
    ],
    "New Delhi": [
        "110001", "110002", "110003", "110005", "110006", "110008", "110009",
        "110015", "110016", "110017", "110018", "110019", "110020", "110021",
        "110023", "110024", "110025", "110027", "110028", "110029", "110030",
        "110034", "110037", "110044", "110048", "110049", "110051", "110052",
        "110055", "110057", "110058", "110059", "110060", "110062", "110063",
        "110064", "110065", "110066", "110067", "110070", "110075", "110076",
        "110077", "110078", "110085", "110091", "110092", "110096",
    ],
    "Hyderabad": [
        "500001", "500003", "500004", "500008", "500016", "500018", "500028",
        "500029", "500032", "500033", "500034", "500035", "500038", "500039",
        "500044", "500048", "500049", "500050", "500055", "500060", "500061",
        "500062", "500063", "500072", "500073", "500081", "500082", "500084",
        "500085", "500086", "500087", "500089", "500090",
    ],
    "Pune": [
        "411001", "411004", "411005", "411006", "411007", "411013", "411014",
        "411016", "411017", "411018", "411019", "411021", "411027", "411028",
        "411030", "411033", "411036", "411037", "411038", "411040", "411041",
        "411044", "411045", "411046", "411048", "411052", "411057", "411058",
        "411061", "411062",
    ],
    "Mumbai": [
        "400001", "400002", "400005", "400008", "400011", "400013", "400018",
        "400020", "400021", "400025", "400028", "400030", "400051", "400053",
        "400059", "400063", "400064", "400069", "400070", "400072", "400076",
        "400078", "400079", "400080", "400086", "400093", "400096", "400097",
        "400099", "400101", "400102", "400103", "400104",
    ],
    "Chennai": [
        "600001", "600002", "600004", "600006", "600008", "600010", "600014",
        "600017", "600018", "600020", "600024", "600028", "600031", "600032",
        "600034", "600035", "600040", "600041", "600042", "600045", "600053",
        "600083", "600085", "600086", "600088", "600089", "600090", "600091",
        "600095", "600096", "600097", "600100", "600113", "600116", "600119",
    ],
    "Noida": [
        "201301", "201303", "201304", "201305", "201306", "201307", "201308",
        "201309", "201310", "201313", "201314", "201318",
    ],
}

# United Kingdom: admin-1 = the 4 nations (Clay uses these, not regions). England
# holds ~91%, so it needs many cities. Postcodes do NOT work in Clay for the UK,
# and ~32% have blank size -> revenue-first fallback.
UK_NATIONS = {
    "England": [
            "Hove", "Royal Sutton Coldfield", "Stanmore", "Borehamwood", "Eastleigh", "Leigh-on-Sea", "Woodford Green", "Rickmansworth", "Pinner", "Southall", "Wickford", "Royal Leamington Spa", "Hornchurch", "Cannock", "Grays", "Potters Bar", "Loughton", "Bromsgrove", "Hoddesdon", "Shepperton", "Wilmslow", "Waltham Cross", "Lytham St Anne's", "Beckenham", "Cheadle", "Wirral", "Greenford", "Stourbridge", "Bishop's Stortford", "Rochester", "Northwich", "Mitcham", "Waterlooville", "Smethwick", "Billericay", "Ruislip", "Westcliff-on-Sea", "Witney", "King's Lynn", "Northwood", "Bicester", "Halesowen", "Leighton Buzzard", "Newcastle-Under-Lyme", "Ashton-Under-Lyne", "Gerrards Cross", "Sittingbourne", "Droitwich Spa", "Great Yarmouth", "Ware", "Lowestoft", "St Ives", "Warminster", "Beaconsfield", "Royston", "Havant", "Maldon", "New Malden", "Dorking", "Abingdon-on-Thames", "Ormskirk", "Letchworth", "East Grinstead", "Newport", "Brierley Hill", "North Shields", "Benfleet", "Oldbury", "Ascot", "Hailsham", "South Croydon", "Lutterworth", "Shipley", "Southsea", "Saffron Walden", "Chesham", "Staines-upon-Thames", "Evesham", "Congleton", "Hampton", "Lewes", "Swadlincote", "Morden", "Isleworth", "Rayleigh", "Wimborne Minster", "Leigh", "Harpenden", "Caterham", "Amersham", "Clitheroe", "Bexhill-on-Sea", "Hyde", "Epping", "Wallington", "Gosport", "Melton Mowbray", "Hook", "Daventry", "Buckingham", "Wednesbury", "Gainsborough", "Dorchester", "Knutsford", "Swanley", "Woodbridge", "Rugeley", "Batley", "Bushey", "Nelson", "West Drayton", "Brentford", "Morecambe", "Cleethorpes", "Marlow", "Wetherby", "Retford", "High Peak", "Willenhall", "Bilston", "Erith", "Nantwich", "Barrow-In-Furness", "West Malling", "Kendal", "Bootle", "Thornton Heath", "Carshalton", "Ellesmere Port", "Uckfield", "Northolt", "Coulsdon", "Malvern", "Henley-on-Thames", "Waltham Abbey", "Purley", "Rossendale", "Lymington", "Horley", "Towcester", "Witham", "Kenilworth", "Alfreton", "Dover", "Kingswinford", "Ringwood", "Leyland", "Holmfirth", "Washington", "Glossop", "Goole", "Pudsey", "St Leonards-on-Sea", "Newmarket", "Ilkley", "Wallasey", "Didcot", "Wells", "Crowborough", "Ashby-De-La-Zouch", "Oswestry", "Berkhamsted", "Teddington", "Stalybridge", "Esher", "Oxted", "New Milton", "Rainham", "Sutton In Ashfield", "Rochford", "Buxton", "Cleckheaton", "Oakham", "Worksop", "Aylesford", "Cockermouth", "Dereham", "Skipton", "Bexleyheath", "Addlestone", "Skelmersdale", "Shoreham-By-Sea", "Matlock", "Morpeth", "Mitcheldean", "Tipton", "Billingham", "Stowmarket", "Belper", "Consett", "St Austell", "Darwen", "Bridgnorth", "Sawbridgeworth", "Tewkesbury", "Kidlington", "Sandbach", "Bishop Auckland", "Edenbridge", "West Byfleet", "Newport Pagnell", "Canvey Island", "Chester-Le-Street", "Halstead", "Radstock", "Westerham", "Uttoxeter", "Stourport-on-Severn", "Ashbourne", "Thames Ditton", "Selby", "Thornton-Cleveleys", "Thatcham", "Brighouse", "Bingley", "Penrith", "Southam", "Chigwell", "Prescot", "Brackley", "Diss", "Polegate", "Stonehouse", "Tarporley", "Carnforth", "Tring", "Iver", "Faversham", "Wantage", "Stone", "Sleaford", "Northallerton", "Heywood", "Tadworth", "Upminster", "Mexborough", "Radlett", "Ryde", "Poulton-Le-Fylde", "Buntingford", "Buckhurst Hill", "Broxbourne", "Hassocks", "Market Rasen", "Otley", "Ripon", "Princes Risborough", "Biggleswade", "Wallingford", "Thame", "Chipping Norton", "Chislehurst", "Broadstairs", "Louth", "Sandwich", "Helston", "Leek", "Workington", "Hessle", "Chessington", "Wigston", "Hexham", "Hayes", "Worcester Park", "Bedworth", "Swanage", "Houghton-Le-Spring", "Cradley Heath", "Middleton", "Brough", "Dronfield", "Hungerford", "Welling", "Whitchurch", "Heathfield", "Banstead", "Ferndown", "Brigg", "March", "Bideford", "Tetbury", "Wallsend", "Billingshurst", "Pershore", "Driffield", "Bourne", "Ripley", "Burntwood", "South Ockendon", "West Wickham", "Tilbury", "Colne", "Westbury", "Bamber Bridge", "Skegness", "Newark-on-Trent", "Cranbrook", "Marlborough", "Market Drayton", "Lancing", "Winsford", "Hockley", "Ashington", "Crediton", "Mirfield", "Fleetwood", "Bagshot", "Ossett", "Melksham", "Stanford-Le-Hope", "Tenterden", "Ulverston", "Alcester", "Pulborough", "Glastonbury", "Malmesbury", "Elland", "Knaresborough", "Crowthorne", "Yarm", "Kings Langley", "Sandy", "Brixham", "Lydney", "Bridport", "Stanley", "Burnham-on-Sea", "Hythe", "Hebden Bridge", "Newton-Le-Willows", "Alnwick", "East Molesey", "Littleborough", "Liphook", "Bodmin", "Martock", "Ludlow", "Kingsbridge", "Great Blakenham", "Guisborough", "Bourne End", "Blandford Forum", "Jarrow", "Sowerby Bridge", "Forest Row", "Sherborne", "Rye", "Newton Aycliffe", "Wymondham", "Atherstone", "Bakewell", "Sunbury-on-Thames", "Wellington", "Alderley Edge", "Welwyn", "Greenhithe", "Normanton", "Shepton Mallet", "Ingatestone", "Calne", "Sidmouth", "Windermere", "Longfield", "Lymm", "Beccles", "Battle", "Malton", "Dunmow", "Netherhampton", "Honiton", "Saltburn-By-The-Sea", "Whitehaven", "Broadstone", "Tavistock", "Wadebridge", "Fordingbridge", "Great Missenden", "Ashtead", "Sheerness", "Penryn", "Berwick-upon-Tweed", "Arundel", "Saltash", "Teignmouth", "Peterlee", "Rowley Regis", "Henfield", "Totnes", "Shifnal", "Belvedere", "Harwich", "Bordon", "Faringdon", "Seaford", "Moreton-In-Marsh", "Bewdley", "Sandown", "Baldock", "Ongar", "Emsworth", "Launceston", "Neston", "Middlewich", "Blaydon", "Cowes", "Burnham-on-Crouch", "Shaftesbury", "Whitby", "West Molesey", "Wigton", "Steyning", "Heckmondwike", "Liskeard", "Dukinfield", "Henley-In-Arden", "Leominster", "Horncastle", "Crewkerne", "Ross-on-Wye", "Hayling Island", "New Romney", "Chatteris", "Spennymoor", "Barnoldswick", "Thirsk", "Stansted Mountfitchet", "Okehampton", "Barnard Castle", "Axminster", "Bacup", "Sandhurst", "South Molton", "Lightwater", "Liss", "Newhaven", "Ventnor", "Hebburn", "Lingfield", "Great Dunmow", "Wotton-Under-Edge", "Cottingham", "Immingham", "Heanor", "Hindhead", "Fakenham", "Purfleet-on-Thames", "Wareham", "Bude", "Seaham", "Minehead", "Corsham", "Downham Market", "Todmorden", "Chard", "North Walsham", "Peacehaven", "Holt", "Coleford", "Alresford", "Tadley", "East Cowes", "North Ferriby", "Robertsbridge", "Dursley", "Swaffham", "Olney", "East Boldon", "Cullompton", "Cheddar", "Dawlish", "Hope Valley", "Shefford", "Brandon", "Knottingley", "Shanklin", "Looe", "Chinnor", "Halesworth", "Hayle", "Attleborough", "Somerton", "Yateley", "Watlington", "Wadhurst", "Tadcaster", "Barton-upon-Humber", "Frodsham", "Seaton", "Ilfracombe", "Brockenhurst", "Highbridge", "Winscombe", "Ledbury", "Crook", "Sturminster Newton", "Bedlington", "Warlingham", "Badbury", "Ivybridge", "Verwood", "Virginia Water", "Tenbury Wells", "Keswick", "Keston", "Pickering", "Southwell", "Kenley", "Cromer", "Portland Port", "Petworth", "Catterick Garrison", "Gatwick", "Bromyard", "Ferryhill", "Grange-Over-Sands", "Ambleside", "Cinderford", "Dalton-In-Furness", "Wincanton", "Blackwater", "Torpoint", "Richmond upon Thames", "Abbots Langley", "Liversedge", "Street", "Ryton", "Studley", "Carterton", "Prudhoe", "Axbridge", "Market Deeping", "Aldermaston", "Pewsey", "Maryport", "Chalfont St Giles", "Stockbridge", "Saxmundham", "Craven Arms", "Chipping Campden", "Leyburn", "Frinton-on-Sea", "Eccleston", "Horsforth", "Knebworth", "Eye", "Lyndhurst", "Edgware Bury", "Pevensey", "Newent", "Church Stretton", "Ilminster", "Seascale", "Manningtree", "Wisborough Green", "City of Westminster", "Hunstanton", "Mere", "Swanscombe", "Burford", "Brampton", "Whyteleafe", "Castle Cary", "Birchington", "Langport", "Woodstock", "Braunton", "Midhurst", "Harleston", "Boldon Colliery", "Ibstock", "Hadleigh", "Colyton", "Bedale", "Rowlands Castle", "Lee-on-The-Solent", "Choppington", "Westgate-on-Sea", "Romney Marsh", "Great Malvern", "St Bees", "Snodland", "Woodhall Spa", "Broadway", "Bembridge", "Perranporth", "Malpas", "Godstone", "Budleigh Salterton", "Lyme Regis", "City of London", "Kirkby Stephen", "Shipston-on-Stour", "Aldeburgh", "Betchworth", "Yelverton", "Ellesmere", "Sheringham", "West Bridgford", "Broseley", "Padiham", "Markfield", "Barrow upon Humber", "Writtle", "Caversham", "Wedmore", "Wimborne", "Filey", "Holsworthy", "Uffcott", "Leiston", "Morley", "Shildon", "Buckfastleigh", "Kington", "Southminster", "Bishop's Castle", "Rowlands Gill", "Bampton", "Rotherfield Greys", "Royal Tunbridge Wells", "Wythenshawe", "Trafford Park", "Lostwithiel", "Ottery St Mary", "Saint Leonards", "Bungay", "Mablethorpe", "Bury St. Edmunds", "Berkeley", "Hawes", "Millom", "Henlow", "Etchingham", "Sutton Weaver", "Milnthorpe", "Staverton", "Tidworth", "Windlesham", "Spilsby", "Dartmouth", "Banwell", "Callington", "Egremont", "Mayfield", "Par", "Walton-on-The-Naze", "Enderby", "Little Hulton", "Fowey", "Wells-Next-The-Sea", "Settle", "Salcombe", "Royal Wootton Bassett", "Thornton", "Ponteland", "Southwick", "Haslingden", "Padstow", "Beaminster", "St Agnes", "St Columb Major", "Pinchbeck", "England", "Denmead", "Hope", "Cheadle Hulme", "St Just", "Stamford Hill", "Ulceby", "Freshwater", "Southwold", "Eccles", "Frizington", "Hare Street", "Great Torrington", "Horwich", "Queenborough", "Droitwich", "Radcliffe", "Thornaby-on-Tees", "Bradley Stoke", "Cheshunt", "Worsley", "Micheldever", "Isles of Scilly", "Dodworth", "Wingate", "Woodbury", "Watchet", "Midsomer Norton", "Tyldesley", "Salt", "Baildon", "Hornsea", "Paulerspury", "Irlam", "Lechlade-on-Thames", "Hartfield", "Chadderton", "Badminton", "Much Hadham", "Wooburn Green", "Hangersley", "Stow-On-The-Wold", "Chandler's Ford", "Withernsea", "Drybrook", "Whiteley", "Stoke Sub Hamdon", "Plympton", "Wylam", "Woolacombe", "Heald Green", "Stokesley", "Melbourne", "Much Wenlock", "South Woodham Ferrers", "Stratfield Saye", "Cleator Moor", "Askam In Furness", "Aston Sandford", "Swinton", "Fairford", "Arlesey", "Avonmouth", "Camelford", "Atherton", "Upper Heyford", "Rumwell", "Whaley Bridge", "Brookwood", "Chobham", "Longhope", "Chipping Ongar", "Yarmouth", "Alsager", "Burscough", "Ham", "St. Neots", "South Brent", "Paddock Wood", "Tottenham", "Castle Donington", "Histon", "Sherburn In Elmet", "Twyford", "Golborne", "Clayton-Le-Moors", "Wrotham", "Hagley", "Great Glen", "Royton", "East Malling", "Ardleigh", "Hambrook", "Roche", "Stapleford", "Sywell", "Cold Higham", "Upper Minety", "Ashton-In-Makerfield", "Haltwhistle", "Longtown", "Beaworthy", "Westby", "North Benfleet", "Lynton", "Greater Manchester", "Garforth", "Great Chesterford", "Stow-on-The-Wold", "Charlbury", "Swallowfield", "West Hill", "Prestwich", "Birtley", "Flax Bourton", "Chalford", "Wooler", "Bletchley", "Totton", "Altham", "Lechlade", "Pusey", "Beaulieu", "Harberton", "Langham", "Bentley", "Horam", "Knowsley", "Yeadon", "Cornhill on Tweed", "Carlton", "Chalgrove", "Appleby-In-Westmorland", "Quedgeley", "Brading", "Corston", "Barnetby Le Wold", "Corbridge", "Markyate", "Melton", "Houghton Le Spring", "Trimdon", "Datchet", "Templecombe", "Hucknall", "Denton", "Westbury-on-Severn", "Ramsbottom", "Ashburton", "Waterbeach", "Daresbury", "Ellistown", "Sedgefield", "Stalbridge", "Winkleigh", "Thurstonfield", "Higham", "Woodley", "Woburn Sands", "Urmston", "Seahouses", "Bishops Frome", "Stoke-on-trent", "Finchley", "St. Ives", "Dymock", "West Horndon", "Penkridge", "Stoke On Trent", "Milton", "Marksbury", "Ribchester", "Whiteparish", "Thorne", "Syston", "Teston", "Chorleywood", "Dersingham", "Charing", "Walton Highway", "Kirkby-In-Ashfield", "Scorrier", "Warsash", "Yoxall", "Kirkby-In-Furness", "Shepshed", "Oakington", "Upper Rissington", "Newnham", "Cleobury Mortimer", "Kirkby", "St. Austell", "Ewyas Harold", "Droylsden", "Blakeney", "Pitstone", "Smallfield", "Alford", "Bray", "Stoke Prior", "Almondsbury", "Runcton", "Odiham", "Benenden", "Coniston", "Kingsley", "Kingswood", "Watton", "Titchfield", "Lifton", "Stocksfield", "South Petherton", "Rothwell", "Fawkham Green", "Bethersden", "Totland", "Fulwood", "Broughton", "Cleator", "Corfe Mullen", "Colnbrook", "Blaydon-On-Tyne", "Dulverton", "Stallingborough", "Salford Priors", "Tolleshunt Major", "Denham", "Broughton In Furness", "Burton-On-Trent", "Chilworth", "Hockworthy", "Swavesey", "Loddington", "Brownhills", "Eccleshall", "Norton", "Amble", "Barton", "Pelsall", "Lancs", "Magdalen Laver", "Theale", "Tarleton", "Storrington", "Staveley", "Hemyock", "Lurgashall", "North Hykeham", "Stretford", "Bowness-on-Windermere", "Westdean", "Baginton", "Kimbolton", "Blaby", "Boroughbridge", "North Petherton", "Trolliloes", "Denston", "West Wittering", "Whitefield", "Whittlesey", "Mildenhall", "London Colney", "Garstang", "Seaview", "Bovey Tracey", "Parbold", "Brockworth", "Wath upon Dearne", "Maghull", "South Cerney", "Kirkhamgate", "Linthwaite", "Harlestone", "Brierfield", "Dunkeswell", "Framfield", "Kislingbury", "Barwell", "Toddington", "Bredbury", "Beamsley", "Middx", "Finchampstead", "Ampthill", "Howden", "Hartley Wintney", "Horbury", "Ingleton", "Hilton", "Alveley", "Shirebrook", "Bream", "Shepley", "Yiewsley", "Cricklade", "Tisbury", "Edale", "Sandiacre", "Dorrington", "Handcross", "Chatburn", "Crowlas", "Chiswick", "St Clement", "Reepham", "Knowle", "Middleton-In-Teesdale", "Earls Colne", "Newcastle Under Lyme", "Spellbrook", "Eamont Bridge", "Wendover", "Sible Hedingham", "Pinxton", "Maltby", "Ash", "Stotfold", "North Duffield", "Hoyland", "Aldridge", "Edlesborough", "Frimley", "Bradwell", "Beckermet", "Kingsland", "Blythe Bridge", "Penwortham", "Chafford Hundred", "Irthlingborough", "Stapleford Abbotts", "Bitton", "Guiseley", "Groombridge", "Umberleigh", "South Milton", "Sawston", "Claverley", "Formby", "Durley", "Topsham", "Wanborough", "Ombersley", "Elstead", "Fornham All Saints", "Waddington", "Fordham", "High Bentham", "Abridge", "Yaxley", "Featherstone", "Summercourt", "Alston", "Barrowford", "Woodstone Village", "Chudleigh", "Houghton Regis", "Port Isaac", "Newbiggin-By-The-Sea", "Holmrook", "Westhoughton", "Minety", "Harewood", "South Killingholme", "Morton", "Kirkby Lonsdale", "Grove", "Whickham", "Bruton", "Farrington Gurney", "Wingrave", "Chipping Sodbury", "Godmanchester", "Skipwith", "Ruckinge", "Wendlebury", "South Kirkby", "Oundle", "Shipston-On-Stour", "South Bank", "Hurn", "Buckland", "Hobson", "Merstham", "Barlborough", "Rawtenstall", "Brightlingsea", "Hill Brow", "Polstead", "Charlcombe", "Oaksey", "Brasted", "Elsenham", "Norton Fitzwarren", "Barkway", "Colerne", "Whittington", "Iverley", "Barkisland", "Tingrith", "Nursling", "Brisley", "Bobbing", "Hampton Lucy", "Boyton", "St Helen Auckland", "Brockhampton", "Trerulefoot", "Skelton on Ure", "Worton", "Marsh Gibbon", "Broad Campden", "North Chailey", "Weston Hills", "Ravenshead", "Coggeshall", "Bibury", "Curdworth", "Inkberrow", "Droxford", "Somercotes", "Penn Street", "Chesterton", "Buscot Wick", "Grimley", "Market Bosworth", "Crondall", "Shawbury", "Clipston", "Shefford Woodlands", "Sibson", "Rawreth", "Pocklington", "Munsley", "Brandsby", "Eckington", "Compton", "Broadbridge Heath", "Thornbury", "Denshaw", "Willersey", "Brighton and Hove", "Lund", "Wiveliscombe", "Islip", "Wheathampstead", "Wichenford", "Brockham", "Walton", "Westham", "Brixworth", "Hethersett", "Helmsley", "Tutbury", "Bosham", "Norbury", "Bovingdon", "Grimethorpe", "Great Holland", "Cuckfield", "Sampford Courtenay", "Mitford", "Great Abington", "Coln St Aldwyns", "Walberton", "Moreton Valence", "Pitchcombe", "Romiley", "Clay Cross", "Ermington", "Copgrove", "Trudoxhill", "Weston", "Melbourn", "Newland", "Anstey", "Painswick", "Balsall Common", "Skeffington", "Rocester", "Leverington", "Hixon", "Winnersh", "Bradford-on-Avon", "Brent Knoll", "Nottingham City", "Horsley", "Allerthorpe", "Adwick Le Street", "Belford", "West Kirby", "Abingdon", "Elvington", "Healing", "Ashwater", "Warninglid", "Whitehill", "Bishops Lydeard", "Armthorpe", "Trent", "Brill", "Moulton Chapel", "East Wittering", "Pool-In-Wharfedale", "Marple Bridge", "Aston Tirrold", "Gretton", "Gilberdyke", "Long Sutton", "Britwell Salome", "Uffculme", "Dinnington", "Hartland", "Blofield", "Menston", "Kingsdown", "Burgh Heath", "Witham Friary", "Arborfield", "Kilcot", "Great Cubley", "Thorp Arch", "Langtree", "Mytholmroyd", "Moulton", "Cleveleys", "Hazel Grove", "Billinghay", "Piddington", "Rufford", "Charlwood", "Glasshouses", "Chagford", "Beckford", "Bishop's Waltham", "Torcross", "Shenington", "Old Stratford", "Takeley", "Tarrant Hinton", "Culgaith", "Upper Langford", "Kingerby", "Rushock", "Ogbourne St George", "Carrington", "Irthington", "Berry Pomeroy", "Euxton", "Longridge", "Cartmel", "Offenham", "Appleby Magna", "Bursledon", "Hampton Lovett", "Arnesby", "Tanfield Lea", "Central Lydbrook", "Hook Norton", "Flitwick", "Barley", "Stow Cum Quy", "Stanwell", "Steeple Morden", "Pulham Market", "Moor Row", "Lanivet", "Scamblesby", "Wellesbourne", "Thurmaston", "Harkstead", "New Mills", "Mawdesley", "Melton Constable", "Dalton", "Great Harwood", "Great Bentley", "Danbury", "Chathill", "Wilstead", "Great Bedwyn", "Byfleet", "Leyton", "Eaton Ford", "North Cadbury", "Richards Castle", "Wick", "Churchtown", "Great Hallingbury", "Thorpe", "Baynards Green", "North Mymms", "Stoke Lacy", "Nutley", "Winston", "Handforth", "Marsham", "Winslow", "Coleshill", "Cresswell", "Aiskew", "Tynemouth", "Bawtry", "Eynsham", "Herriard", "Winscales", "Lydbury North", "Chapel Brampton", "Botley", "Tackley", "Pangbourne", "Crowle", "Copthorne", "Heckington", "Shorne", "Eastington", "Desford", "Witherslack", "Groby", "Meriden", "Sticklepath", "Ruardean", "Horsted Keynes", "Hawkhurst", "Lyminge", "Upton", "Withypool", "Heytesbury", "Ockley", "Distington", "Bucklebury", "Allet", "Halfway House", "Whitecroft", "Matching Green", "Bourton-on-The-Water", "Ullenhall", "Alrewas", "Weeting", "Felton", "Cranage", "Heskin Green", "The Sands", "New Alresford", "New Ollerton", "Marazion", "Elstree", "Crosby-on-Eden", "Bamburgh", "Calverton", "Horndean", "Dorridge", "West Grinstead", "Tockwith", "Bingham", "Saxilby", "Headley Down", "Long Crendon", "Wolvey", "Kennford", "St. Helens", "Rowland", "Henley-On-Thames", "Chelmondiston", "Chingford", "Mursley", "Carleton", "Hatfield Peverel", "Bromham", "Bishop Monkton", "Newbridge", "Milnrow", "Backworth", "Burton Joyce", "Pilsley", "Althorne", "Hullbridge", "Winster", "Pannal", "Stretton", "Hales", "Dibden Purlieu", "Hale", "Shardlow", "Cookham", "Southend", "Woburn", "Over Peover", "Gunthorpe", "Fernhill Heath", "Bere Alston", "Seal", "Astbury", "East Prawle", "Maunby", "Spreyton", "Old Basing", "Sand", "Market Lavington", "Hatherton", "Dodford", "Moresby Parks", "Downham", "Bournheath", "Ardeley", "Alconbury", "Riding Mill", "Melmerby", "Westgate", "Littletown", "Conyer", "Widdington", "Burwell", "Loddon", "Kidsgrove", "South Stoke", "Needham Market", "St Mawes", "Whalley", "Arnold", "Farningham", "Astley", "Funtington", "Shelton", "Allostock", "Ridgewell", "Willingham", "Oxshott", "Old Sarum", "Walton on The Hill", "Bardsey", "Chacombe", "Fulbourn", "Telscombe Cliffs", "Lapford", "Stanbridge", "Hathern", "Chideock", "Hampton In Arden", "Silverstone", "West Mersea", "Levens", "Meopham", "Paulton", "Milford on Sea", "Fradley", "Sandford", "Biggin Hill", "Hadfield", "Somersham", "Highnam", "Berinsfield", "Abbots Leigh", "Whitworth", "Tideswell", "Easingwold", "Sedbergh", "Hurstpierpoint", "Highworth", "Thirlby", "Send", "Whetstone", "Bishopsteignton", "Northfleet", "Washfield", "Lower Sticker", "Ashwicken", "West Horsley", "Chalfont St Peter", "Blue Anchor", "Blockley", "Litlington", "Coate", "Garford", "Niton", "Ewen", "Grindleford", "Peatling Magna", "Sturton By Stow", "Kingskerswell", "Swan Valley", "Hallow", "Berkeley Heath", "Hopton", "Hedge End", "Yatton", "Benthall", "Waterlip", "Pateley Bridge", "Plumpton Green", "Middleton Stoney", "North Tawton", "Field Broughton", "Delabole", "Hunston", "Cross Houses", "Hatfield Broad Oak", "Bradley", "Lacey Green", "Pool", "Bracebridge Heath", "Hallen", "Mells", "Seaton Burn", "South Cave", "Larkfield", "Wonersh", "Kettleshulme", "Tuxford", "Calverley", "Audenshaw", "Barkston", "Northowram", "Westcott", "Graveley", "Myddle", "Thaxted", "Belton", "West Coker", "Pagham", "Ninebanks", "Robin Hood", "Beenham", "Gnosall", "Crooklands", "Chester Le Street", "West Hanningfield", "Corley", "Warwick Bridge", "Portway", "Great Gonerby", "Barton-Le-Clay", "Upper Wield", "Burstow", "Princethorpe", "Askern", "Bagstone", "Marston", "Killamarsh", "Wem", "Thrussington", "Deeside", "Whaddon", "Fobbing", "Over Wallop", "Barnetby", "Queniborough", "Calstock", "Ticehurst",
            "Newcastle", "Hull", "Birkenhead", "Brentwood", "Bury St Edmunds", "Camberley", "Camden", "Chatham", "Chelsea", "Cirencester", "Clapham", "Corby", "Dunstable", "Grimsby", "Hatfield", "Hertford", "Hitchin", "Kidderminster", "Leatherhead", "Lewisham", "Lichfield", "Reigate", "Richmond", "Scunthorpe", "Stratford-upon-Avon", "Sutton Coldfield", "Tamworth", "Wellingborough", "Welwyn Garden City", "Weybridge",
            "Ilford", "Romford", "Sidcup", "Barnet", "Edgware", "Bromley", "Wembley", "Dagenham", "Orpington", "Harlow", "Barking", "Bexley", "Surbiton", "Feltham", "Twickenham", "Ealing", "Greenwich", "Tower Hamlets", "Battersea", "Hackney", "Kensington", "Southwark", "Fulham", "Stratford", "Walthamstow", "Brent", "Hammersmith", "Havering", "Islington", "Newham", "Wandsworth",
        "London", "Manchester", "Birmingham", "Leeds", "Bristol", "Liverpool",
        "Sheffield", "Nottingham", "Newcastle upon Tyne", "Cambridge", "Reading",
        "Oxford", "Brighton", "Milton Keynes", "Coventry", "Leicester",
        "Southampton", "Portsmouth", "Bournemouth", "Norwich", "Exeter", "Bath",
        "Slough", "Watford", "Croydon", "Guildford", "Basingstoke", "Swindon",
        "Cheltenham", "Derby", "Wolverhampton", "Stoke-on-Trent", "Preston",
        "Kingston upon Hull", "Middlesbrough", "Sunderland", "Bradford",
        "Ipswich", "Peterborough", "Luton", "Northampton", "Maidenhead", "Woking",
        "Bracknell", "Farnborough", "St Albans", "Chelmsford", "Colchester",
        "Uxbridge", "Solihull", "Warrington", "Bolton", "Wakefield", "York",
        # broader England coverage to shrink the "rest" remainder
        "Stockport", "Salford", "Rochdale", "Oldham", "Wigan", "Blackburn",
        "Blackpool", "Huddersfield", "Halifax", "Doncaster", "Rotherham",
        "Barnsley", "Chesterfield", "Mansfield", "Lincoln", "Telford",
        "Shrewsbury", "Worcester", "Gloucester", "Hereford", "Aylesbury",
        "High Wycombe", "Basildon", "Southend-on-Sea", "Stevenage",
        "Hemel Hempstead", "Bedford", "Kettering", "Rugby", "Nuneaton",
        "Walsall", "West Bromwich", "Dudley", "Redditch", "Leamington Spa",
        "Warwick", "Banbury", "Newbury", "Wokingham", "Windsor", "Aldershot",
        "Winchester", "Fareham", "Chichester", "Worthing", "Crawley", "Horsham",
        "Eastbourne", "Hastings", "Tunbridge Wells", "Maidstone", "Ashford",
        "Canterbury", "Gillingham", "Gravesend", "Dartford", "Sutton",
        "Kingston upon Thames", "Epsom", "Redhill", "Godalming", "Farnham",
        "Staines", "Hounslow", "Harrow", "Enfield", "Wolverhampton",
        "Plymouth", "Torquay", "Taunton", "Yeovil", "Poole", "Weymouth",
        "Salisbury", "Bath", "Weston-super-Mare", "Stroud", "Carlisle",
        "Lancaster", "Chester", "Crewe", "Macclesfield", "Stafford", "Burton upon Trent",
        # deeper England long tail
        "Southport", "St Helens", "Widnes", "Runcorn", "Altrincham", "Sale",
        "Bury", "Chorley", "Preston", "Blackburn", "Accrington", "Burnley",
        "Harrogate", "Scarborough", "Keighley", "Dewsbury", "Castleford",
        "Pontefract", "Beverley", "Bridlington", "Redcar", "Stockton-on-Tees",
        "Darlington", "Hartlepool", "Gateshead", "South Shields", "Whitley Bay",
        "Blyth", "Cramlington", "Durham", "Loughborough", "Hinckley",
        "Market Harborough", "Coalville", "Ilkeston", "Long Eaton", "Beeston",
        "Newark", "Grantham", "Boston", "Spalding", "Stamford", "Rushden",
        "Thetford", "Wisbech", "Huntingdon", "St Neots", "Ely", "Haverhill",
        "Sudbury", "Braintree", "Clacton-on-Sea", "Felixstowe", "Chippenham",
        "Trowbridge", "Devizes", "Frome", "Bridgwater", "Clevedon", "Portishead",
        "Nailsea", "Yate", "Keynsham", "Paignton", "Newton Abbot", "Exmouth",
        "Barnstaple", "Tiverton", "Truro", "Falmouth", "Penzance", "Newquay",
        "Camborne", "Redruth", "Fleet", "Alton", "Petersfield", "Romsey",
        "Christchurch", "Haslemere", "Cranleigh", "Chertsey", "Walton-on-Thames",
        "Cobham", "Egham", "Sunbury", "Andover", "Bognor Regis", "Littlehampton",
        "Burgess Hill", "Haywards Heath", "Sevenoaks", "Tonbridge", "Folkestone",
        "Margate", "Ramsgate", "Deal", "Whitstable", "Herne Bay",
    ],
    "Scotland": [
            "Ayr", "Dumfries", "Dunfermline", "Falkirk", "Glenrothes", "Greenock", "Hamilton", "Inverness", "Kilmarnock", "Kirkcaldy", "Motherwell", "Perth","Edinburgh", "Glasgow", "Aberdeen", "Dundee", "Stirling",
                 "Paisley", "Livingston", "East Kilbride"],
    "Wales": [
            "Bangor", "Barry", "Bridgend", "Caerphilly", "Cwmbran", "Llanelli", "Merthyr Tydfil", "Neath", "Pontypridd", "Port Talbot","Cardiff", "Swansea", "Newport", "Wrexham"],
    "Northern Ireland": [
            "Ballymena", "Coleraine", "Craigavon", "Lisburn", "Newry", "Newtownabbey","Belfast", "Londonderry"],
}

# Australia: 8 states/territories (Clay uses full English names). NSW (Sydney) and
# Victoria (Melbourne) hold the bulk; Sydney & Melbourne each exceed 5,000 in the
# big industries, so they get metro postcode lists (AU postal filtering works in
# Clay, unlike the UK). Everything else fits under the cap at city level.
AU_STATES = {
    "New South Wales": ["Sydney", "Newcastle", "Wollongong", "Central Coast",
                        "Parramatta", "Penrith", "Gosford", "Maitland"],
    "Victoria": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Frankston",
                 "Melton", "Shepparton"],
    "Queensland": ["Brisbane", "Gold Coast", "Sunshine Coast", "Cairns",
                   "Townsville", "Toowoomba", "Mackay", "Rockhampton", "Ipswich"],
    "Western Australia": ["Perth", "Fremantle", "Mandurah", "Bunbury"],
    "South Australia": ["Adelaide", "Mount Gambier"],
    "Australian Capital Territory": ["Canberra"],
    "Tasmania": ["Hobart", "Launceston"],
    "Northern Territory": ["Darwin", "Alice Springs"],
}
# Metro postcodes for the only two cities that exceed the export cap. The planner
# bin-packs these into <5,000 slices and the postal-exclude remainder sweeps up any
# unlisted postcode + blank-postal rows, so coverage is complete either way.
AU_POSTAL = {
    "Sydney": [str(z) for z in (
        2000, 2007, 2008, 2009, 2010, 2011, 2015, 2016, 2017, 2018, 2020, 2021,
        2022, 2026, 2027, 2028, 2029, 2031, 2034, 2037, 2038, 2039, 2040, 2041,
        2042, 2043, 2044, 2045, 2046, 2048, 2049, 2050, 2060, 2061, 2062, 2063,
        2064, 2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072, 2073, 2074, 2075,
        2076, 2077, 2085, 2086, 2088, 2089, 2090, 2093, 2095, 2099, 2100, 2101,
        2110, 2112, 2113, 2114, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2126,
        2127, 2128, 2130, 2131, 2132, 2134, 2135, 2137, 2138, 2140, 2141, 2142,
        2143, 2144, 2145, 2146, 2147, 2148, 2150, 2151, 2153, 2154, 2155, 2160,
        2161, 2162, 2163, 2164, 2165, 2166, 2170, 2200, 2204, 2205, 2206, 2207,
        2208, 2210, 2216, 2217, 2218, 2219, 2220, 2226, 2227, 2229, 2232, 2234)],
    "Melbourne": [str(z) for z in (
        3000, 3002, 3003, 3004, 3006, 3008, 3011, 3012, 3013, 3015, 3016, 3018,
        3019, 3020, 3021, 3022, 3023, 3025, 3028, 3029, 3030, 3031, 3032, 3033,
        3034, 3036, 3037, 3038, 3039, 3040, 3041, 3042, 3043, 3044, 3046, 3047,
        3048, 3049, 3051, 3052, 3053, 3054, 3055, 3056, 3057, 3058, 3060, 3061,
        3064, 3065, 3066, 3067, 3068, 3070, 3071, 3072, 3073, 3074, 3075, 3076,
        3081, 3082, 3083, 3084, 3085, 3087, 3088, 3089, 3093, 3095, 3101, 3103,
        3104, 3105, 3106, 3107, 3108, 3109, 3111, 3121, 3122, 3123, 3124, 3125,
        3126, 3127, 3128, 3129, 3130, 3131, 3132, 3133, 3134, 3135, 3136, 3137,
        3138, 3140, 3141, 3142, 3143, 3144, 3145, 3146, 3147, 3148, 3149, 3150,
        3151, 3152, 3153, 3155, 3156, 3161, 3162, 3163, 3165, 3166, 3168, 3169,
        3170, 3171, 3172, 3173, 3174, 3175, 3178, 3179, 3180, 3181, 3182, 3183,
        3184, 3185, 3186, 3187, 3188, 3189, 3190, 3191, 3192, 3193, 3194, 3195,
        3196, 3199, 3204, 3205, 3206, 3207)],
}

UK_COUNTIES = [
    "Kent", "Surrey", "Essex", "Hampshire",
    "Yorkshire", "Lancashire", "Greater London", "West Midlands",
    "Berkshire", "Buckinghamshire", "Hertfordshire", "Oxfordshire",
    "Cambridgeshire", "Cheshire", "Devon", "Dorset",
    "Durham", "Gloucestershire", "Leicestershire", "Lincolnshire",
    "Norfolk", "Northamptonshire", "Nottinghamshire", "Somerset",
    "Staffordshire", "Suffolk", "Sussex", "Warwickshire",
    "Wiltshire", "Worcestershire", "Derbyshire", "Cornwall",
    "Cumbria", "Merseyside", "Tyne and Wear", "South Yorkshire",
    "West Yorkshire", "Bedfordshire", "Shropshire", "Herefordshire",
    "Northumberland", "Rutland", "Wirral", "Middlesex",
    "Avon", "Clwyd", "Gwynedd", "Powys",
]

DE_STATES = {
    "North Rhine-Westphalia": [
        "Cologne", "Düsseldorf", "Dortmund", "Essen", "Duisburg", "Bochum",
        "Wuppertal", "Bielefeld", "Bonn", "Münster", "Gelsenkirchen",
        "Mönchengladbach", "Aachen", "Krefeld", "Oberhausen", "Hagen", "Hamm",
        "Mülheim an der Ruhr", "Leverkusen", "Solingen", "Herne", "Neuss",
        "Paderborn", "Recklinghausen", "Bottrop"
    ],
    "Bavaria": [
        "Munich", "Nuremberg", "Augsburg", "Regensburg", "Würzburg",
        "Ingolstadt", "Fürth", "Erlangen", "Bamberg"
    ],
    "Baden-Württemberg": [
        "Stuttgart", "Mannheim", "Karlsruhe", "Freiburg im Breisgau",
        "Heidelberg", "Heilbronn", "Ulm", "Pforzheim", "Reutlingen", "Esslingen"
    ],
    "Lower Saxony": [
        "Hanover", "Braunschweig", "Oldenburg", "Osnabrück", "Wolfsburg",
        "Göttingen", "Hildesheim", "Salzgitter"
    ],
    "Hesse": [
        "Frankfurt", "Wiesbaden", "Kassel", "Darmstadt", "Offenbach",
        "Hanau", "Marburg", "Giessen"
    ],
    "Saxony": ["Leipzig", "Dresden", "Chemnitz", "Zwickau"],
    "Berlin": ["Berlin"],
    "Hamburg": ["Hamburg"],
    "Rhineland-Palatinate": ["Mainz", "Ludwigshafen", "Koblenz", "Trier", "Kaiserslautern", "Worms"],
    "Schleswig-Holstein": ["Kiel", "Lübeck", "Flensburg"],
    "Brandenburg": ["Potsdam", "Cottbus", "Brandenburg an der Havel", "Frankfurt (Oder)"],
    "Saxony-Anhalt": ["Magdeburg", "Halle", "Dessau-Roßlau"],
    "Thuringia": ["Erfurt", "Jena", "Gera", "Weimar"],
    "Mecklenburg-Vorpommern": ["Rostock", "Schwerin", "Neubrandenburg"],
    "Saarland": ["Saarbrücken"],
    "Bremen": ["Bremen", "Bremerhaven"],
}

# China: admin-1 = provinces / municipalities / autonomous regions / SARs.
# Cities mapped to their province using standard English/Pinyin names accepted by LinkedIn/Clay.
CN_PROVINCES = {
    "Guangdong": ["Shenzhen", "Guangzhou", "Dongguan", "Foshan", "Zhongshan", "Huizhou", "Jiangmen", "Zhuhai", "Shantou", "Zhanjiang", "Baoan District", "Luohu District", "Longgang"],
    "Zhejiang": ["Hangzhou", "Ningbo", "Wenzhou", "Jinhua", "Shaoxing", "Taizhou", "Jiaxing", "Huzhou", "Yiwu"],
    "Jiangsu": ["Suzhou", "Nanjing", "Wuxi", "Changzhou", "Nantong", "Xuzhou", "Yangzhou", "Yancheng", "Taizhou", "Zhenjiang", "Lianyungang", "Kunshan", "Jiangyin"],
    "Shanghai": ["Shanghai", "Pudong", "Minhang", "Baoshan", "Jiading", "Songjiang", "Qingpu", "Fengxian"],
    "Beijing": ["Beijing", "Haidian", "Chaoyang", "Daxing", "Tongzhou", "Changping", "Fengtai"],
    "Shandong": ["Qingdao", "Jinan", "Yantai", "Weifang", "Zibo", "Weihai", "Linyi", "Jining", "Heze"],
    "Fujian": ["Xiamen", "Fuzhou", "Quanzhou", "Zhangzhou", "Putian"],
    "Sichuan": ["Chengdu", "Mianyang", "Deyang", "Yibin", "Luzhou", "Qingbaijiang District"],
    "Hubei": ["Wuhan", "Yichang", "Xiangyang", "Jingzhou", "Huangshi"],
    "Hunan": ["Changsha", "Zhuzhou", "Xiangtan", "Yueyang", "Hengyang"],
    "Henan": ["Zhengzhou", "Luoyang", "Xinxiang", "Nanyang", "Kaifeng"],
    "Hebei": ["Shijiazhuang", "Tangshan", "Baoding", "Langfang", "Cangzhou", "Handan"],
    "Tianjin": ["Tianjin", "Binhai"],
    "Chongqing": ["Chongqing", "Yubei", "Jiulongpo", "Jiangbei"],
    "Shaanxi": ["Xi'an", "Baoji", "Xianyang"],
    "Liaoning": ["Dalian", "Shenyang", "Anshan"],
    "Anhui": ["Hefei", "Wuhu", "Bengbu", "Chuzhou"],
    "Jiangxi": ["Nanchang", "Ganzhou", "Jiujiang"],
    "Guangxi": ["Nanning", "Guilin", "Liuzhou", "Chongzuo"],
    "Yunnan": ["Kunming", "Qujing"],
    "Heilongjiang": ["Harbin", "Daqing", "Heihe"],
    "Jilin": ["Changchun", "Jilin"],
    "Shanxi": ["Taiyuan", "Datong"],
    "Guizhou": ["Guiyang", "Zunyi"],
    "Inner Mongolia": ["Hohhot", "Baotou", "Ordos", "Xilingol League"],
    "Xinjiang": ["Urumqi"],
    "Gansu": ["Lanzhou"],
    "Hainan": ["Haikou", "Sanya"],
    "Ningxia": ["Yinchuan"],
    "Qinghai": ["Xining"],
    "Tibet": ["Lhasa"],
    "Hong Kong": ["Hong Kong", "Kowloon", "Central"],
    "Macau": ["Macau"],
    "Taiwan": ["Taipei", "New Taipei", "Taichung", "Kaohsiung", "Hsinchu", "Taoyuan", "Tainan"],
}

# Japan: admin-1 = 47 prefectures and major commercial cities.
JP_PREFECTURES = {
    "Tokyo": ["Tokyo", "Chiyoda", "Minato", "Shinjuku", "Shibuya", "Chuo", "Shinagawa", "Meguro", "Toshima", "Koto", "Ota", "Setagaya", "Nakano", "Suginami", "Bunkyo", "Taito", "Edogawa", "Katsushika", "Itabashi", "Nerima", "Hachioji", "Tachikawa", "Musashino", "Machida", "Fuchu"],
    "Kanagawa": ["Yokohama", "Kawasaki", "Sagamihara", "Fujisawa", "Kamakura", "Yokosuka", "Hiratsuka", "Chigasaki", "Atsugi", "Yamato"],
    "Osaka": ["Osaka", "Sakai", "Higashiosaka", "Toyonaka", "Suita", "Takatsuki", "Ibaraki", "Yao", "Neyagawa", "Kishiwada"],
    "Aichi": ["Nagoya", "Toyota", "Okazaki", "Ichinomiya", "Toyohashi", "Kasugai", "Anjo", "Komaki", "Kariya"],
    "Fukuoka": ["Fukuoka", "Kitakyushu", "Kurume", "Iizuka", "Omuta", "Kasuga"],
    "Saitama": ["Saitama", "Kawaguchi", "Kawagoe", "Tokorozawa", "Koshigaya", "Soka", "Kasukabe", "Ageo"],
    "Chiba": ["Chiba", "Funabashi", "Matsudo", "Ichikawa", "Kashiwa", "Narita", "Ichihara", "Yachiyo"],
    "Hyogo": ["Kobe", "Himeji", "Nishinomiya", "Amagasaki", "Akashi", "Kakogawa", "Takarazuka", "Itami"],
    "Hokkaido": ["Sapporo", "Asahikawa", "Hakodate", "Kushiro", "Tomakomai", "Obihiro", "Otaru"],
    "Kyoto": ["Kyoto", "Uji", "Kameoka", "Maizuru", "Joyo", "Nagaokakyo"],
    "Shizuoka": ["Shizuoka", "Hamamatsu", "Fuji", "Numazu", "Iwata", "Yaizu"],
    "Hiroshima": ["Hiroshima", "Fukuyama", "Kure", "Higashihiroshima", "Onomichi"],
    "Miyagi": ["Sendai", "Ishinomaki", "Osaki", "Tome", "Natori"],
    "Ibaraki": ["Mito", "Tsukuba", "Hitachi", "Hitachinaka", "Tsuchiura", "Koga"],
    "Tochigi": ["Utsunomiya", "Oyama", "Tochigi", "Ashikaga", "Sano"],
    "Gunma": ["Maebashi", "Takasaki", "Ota", "Isesaki", "Kiryu"],
    "Nagano": ["Nagano", "Matsumoto", "Ueda", "Iida", "Saku"],
    "Niigata": ["Niigata", "Nagaoka", "Joetsu", "Sanjo", "Shibata"],
    "Okayama": ["Okayama", "Kurashiki", "Tsuyama", "Soja"],
    "Kumamoto": ["Kumamoto", "Yatsushiro", "Amakusa", "Tamana"],
    "Kagoshima": ["Kagoshima", "Kirishima", "Kanoya", "Satsumasendai"],
    "Okinawa": ["Naha", "Okinawa", "Uruma", "Urasoe"],
    "Shiga": ["Otsu", "Kusatsu", "Nagahama", "Hikone"],
    "Gifu": ["Gifu", "Ogaki", "Kakamigahara", "Tajimi"],
    "Mie": ["Tsu", "Yokkaichi", "Suzuka", "Matsusaka"],
    "Ishikawa": ["Kanazawa", "Hakusan", "Komatsu"],
    "Nara": ["Nara", "Kashihara", "Ikoma", "Yamatokoriyama"],
    "Nagasaki": ["Nagasaki", "Sasebo", "Isahaya", "Omura"],
    "Iwate": ["Morioka", "Oshu", "Ichinoseki", "Hanamaki"],
    "Ehime": ["Matsuyama", "Imabari", "Niihama", "Saijo"],
    "Fukushima": ["Fukushima", "Koriyama", "Iwaki", "Aizuwakamatsu"],
    "Yamagata": ["Yamagata", "Tsuruoka", "Sakata"],
    "Akita": ["Akita", "Yokote", "Daisen"],
    "Aomori": ["Aomori", "Hachinohe", "Hirosaki"],
    "Fukui": ["Fukui", "Sakai", "Echizen"],
    "Yamanashi": ["Kofu", "Kai", "Fuefuki"],
    "Toyama": ["Toyama", "Takaoka", "Imizu"],
    "Wakayama": ["Wakayama", "Tanabe", "Hashimoto"],
    "Tottori": ["Tottori", "Yonago", "Kurayoshi"],
    "Shimane": ["Matsue", "Izumo", "Hamada"],
    "Yamaguchi": ["Shimonoseki", "Yamaguchi", "Ube", "Shunan", "Iwakuni"],
    "Tokushima": ["Tokushima", "Anan", "Naruto"],
    "Kagawa": ["Takamatsu", "Marugame", "Mitoyo"],
    "Kochi": ["Kochi", "Nankoku", "Tosa"],
    "Saga": ["Saga", "Karatsu", "Tosu"],
    "Oita": ["Oita", "Beppu", "Nakatsu"],
    "Miyazaki": ["Miyazaki", "Miyakonojo", "Nobeoka"],
}

# Austria: 9 Federal States & Major Cities
AT_STATES = {
    "Vienna": ["Vienna"],
    "Lower Austria": ["Sankt Pölten", "Wiener Neustadt", "Krems", "Baden", "Mödling", "Amstetten", "Klosterneuburg"],
    "Upper Austria": ["Linz", "Wels", "Steyr", "Leonding", "Traun", "Vöcklabruck"],
    "Styria": ["Graz", "Leoben", "Kapfenberg", "Bruck an der Mur", "Feldbach"],
    "Tyrol": ["Innsbruck", "Kufstein", "Telfs", "Schwaz", "Hall in Tirol"],
    "Carinthia": ["Klagenfurt", "Villach", "Wolfsberg", "Spittal an der Drau"],
    "Salzburg": ["Salzburg", "Hallein", "Saalfelden", "Sankt Johann im Pongau"],
    "Vorarlberg": ["Dornbirn", "Feldkirch", "Bregenz", "Lustenau", "Bludenz"],
    "Burgenland": ["Eisenstadt", "Oberwart", "Mattersburg", "Neusiedl am See"],
}

# Italy: 20 Regions & Key Commercial Metros
IT_REGIONS = {
    "Lombardy": ["Milan", "Brescia", "Monza", "Bergamo", "Como", "Varese", "Pavia", "Cremona", "Lecco", "Mantua", "Lodi"],
    "Lazio": ["Rome", "Latina", "Frosinone", "Viterbo", "Rieti"],
    "Veneto": ["Venice", "Verona", "Padua", "Vicenza", "Treviso", "Rovigo", "Belluno"],
    "Emilia-Romagna": ["Bologna", "Modena", "Parma", "Reggio Emilia", "Ravenna", "Rimini", "Ferrara", "Forli", "Piacenza", "Cesena"],
    "Piedmont": ["Turin", "Novara", "Alessandria", "Asti", "Cuneo", "Vercelli", "Biella"],
    "Tuscany": ["Florence", "Prato", "Livorno", "Pisa", "Arezzo", "Lucca", "Pistoia", "Siena", "Grosseto"],
    "Campania": ["Naples", "Salerno", "Giugliano in Campania", "Caserta", "Torre del Greco", "Pozzuoli", "Avellino", "Benevento"],
    "Sicily": ["Palermo", "Catania", "Messina", "Syracuse", "Marsala", "Gela", "Ragusa", "Trapani"],
    "Puglia": ["Bari", "Taranto", "Foggia", "Andria", "Lecce", "Barletta", "Brindisi"],
    "Liguria": ["Genoa", "La Spezia", "Savona", "Sanremo", "Imperia"],
    "Friuli Venezia Giulia": ["Trieste", "Udine", "Pordenone", "Gorizia"],
    "Marche": ["Ancona", "Pesaro", "Fano", "Ascoli Piceno", "San Benedetto del Tronto"],
    "Trentino-Alto Adige": ["Trento", "Bolzano", "Merano", "Rovereto"],
    "Umbria": ["Perugia", "Terni", "Foligno", "Citta di Castello"],
    "Abruzzo": ["Pescara", "L'Aquila", "Chieti", "Teramo", "Montesilvano"],
    "Sardinia": ["Cagliari", "Sassari", "Quartu Sant'Elena", "Olbia"],
    "Calabria": ["Reggio Calabria", "Catanzaro", "Corigliano-Rossano", "Lamezia Terme", "Cosenza"],
}

# Brazil: Major Federative Units
BR_STATES = {
    "São Paulo": ["São Paulo", "Campinas", "Guarulhos", "São Bernardo do Campo", "Santo André", "Osasco", "São José dos Campos", "Ribeirão Preto", "Sorocaba", "Santos"],
    "Rio de Janeiro": ["Rio de Janeiro", "São Gonçalo", "Duque de Caxias", "Nova Iguaçu", "Niterói", "Belford Roxo", "Campos dos Goytacazes", "Petrópolis"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora", "Betim", "Montes Claros", "Uberaba"],
    "Rio Grande do Sul": ["Porto Alegre", "Caxias do Sul", "Canoas", "Pelotas", "Santa Maria", "Gravataí"],
    "Paraná": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa", "Cascavel", "São José dos Pinhais", "Foz do Iguaçu"],
    "Santa Catarina": ["Joinville", "Florianópolis", "Blumenau", "São José", "Chapecó", "Itajaí", "Criciúma"],
    "Bahia": ["Salvador", "Feira de Santana", "Vitória da Conquista", "Camaçari", "Itabuna"],
    "Federal District": ["Brasília", "Ceilândia", "Taguatinga", "Samambaia", "Plano Piloto"],
    "Pernambuco": ["Recife", "Jaboatão dos Guararapes", "Olinda", "Caruaru", "Petrolina"],
    "Ceará": ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Maracanaú", "Sobral"],
    "Goiás": ["Goiânia", "Aparecida de Goiânia", "Anápolis", "Rio Verde", "Luziânia"],
    "Espírito Santo": ["Serra", "Vila Velha", "Cariacica", "Vitória", "Cachoeiro de Itapemirim"],
}

# Mexico: Major States & Metros
MX_STATES = {
    "Mexico City": ["Mexico City", "Iztapalapa", "Gustavo A. Madero", "Cuauhtémoc", "Miguel Hidalgo", "Benito Juárez", "Coyoacán", "Álvaro Obregón", "Tlalpan"],
    "Jalisco": ["Guadalajara", "Zapopan", "Tlaquepaque", "Tonalá", "Tlajomulco de Zúñiga", "Puerto Vallarta"],
    "Nuevo León": ["Monterrey", "Guadalupe", "San Nicolás de los Garza", "Apodaca", "General Escobedo", "Santa Catarina", "San Pedro Garza García"],
    "State of Mexico": ["Ecatepec", "Nezahualcóyotl", "Naucalpan", "Toluca", "Tlalnepantla", "Chimalhuacán", "Cuautitlán Izcalli"],
    "Guanajuato": ["León", "Irapuato", "Celaya", "Salamanca", "Silao", "Guanajuato", "San Miguel de Allende"],
    "Puebla": ["Puebla", "Tehuacán", "San Martín Texmelucan", "San Andrés Cholula", "Atlixco"],
    "Baja California": ["Tijuana", "Mexicali", "Ensenada", "Playas de Rosarito", "Tecate"],
    "Querétaro": ["Querétaro", "San Juan del Río", "El Marqués", "Corregidora"],
    "Yucatán": ["Mérida", "Kanasín", "Valladolid"],
    "Coahuila": ["Saltillo", "Torreón", "Monclova", "Piedras Negras"],
    "Sonora": ["Hermosillo", "Ciudad Obregón", "Nogales", "San Luis Río Colorado"],
    "Quintana Roo": ["Cancún", "Playa del Carmen", "Chetumal", "Cozumel"],
}

# Poland: 16 Voivodeships
PL_VOIVODESHIPS = {
    "Masovian": ["Warsaw", "Radom", "Płock", "Siedlce", "Pruszków", "Legionowo", "Ostrołęka", "Piaseczno"],
    "Silesian": ["Katowice", "Częstochowa", "Sosnowiec", "Gliwice", "Zabrze", "Bielsko-Biała", "Bytom", "Ruda Śląska", "Rybnik", "Tychy", "Dąbrowa Górnicza", "Chorzów"],
    "Greater Poland": ["Poznań", "Kalisz", "Konin", "Piła", "Ostrów Wielkopolski", "Gniezno", "Leszno"],
    "Lower Silesian": ["Wrocław", "Wałbrzych", "Legnica", "Jelenia Góra", "Lubin", "Głogów", "Świdnica"],
    "Lesser Poland": ["Kraków", "Tarnów", "Nowy Sącz", "Oświęcim", "Chrzanów", "Olkusz", "Nowy Targ"],
    "Pomeranian": ["Gdańsk", "Gdynia", "Słupsk", "Tczew", "Wejherowo", "Starogard Gdański", "Sopot"],
    "Łódź": ["Łódź", "Piotrków Trybunalski", "Pabianice", "Tomaszów Mazowiecki", "Bełchatów", "Zgierz"],
    "Kuyavian-Pomeranian": ["Bydgoszcz", "Toruń", "Włocławek", "Grudziądz", "Inowrocław"],
    "West Pomeranian": ["Szczecin", "Koszalin", "Stargard", "Kołobrzeg", "Świnoujście"],
    "Lublin": ["Lublin", "Zamość", "Chełm", "Biała Podlaska", "Puławy"],
    "Podkarpackie": ["Rzeszów", "Przemyśl", "Stalowa Wola", "Mielec", "Tarnobrzeg", "Krosno"],
    "Podlaskie": ["Białystok", "Suwałki", "Łomża", "Augustów"],
}

# Belgium: Regions
BE_REGIONS = {
    "Flanders": ["Antwerp", "Ghent", "Bruges", "Leuven", "Aalst", "Mechelen", "Hasselt", "Kortrijk", "Sint-Niklaas", "Ostend", "Genk", "Roeselare"],
    "Wallonia": ["Charleroi", "Liège", "Namur", "Mons", "La Louvière", "Tournai", "Seraing", "Verviers", "Mouscron"],
    "Brussels-Capital": ["Brussels", "Schaerbeek", "Anderlecht", "Ixelles", "Uccle", "Woluwe-Saint-Lambert", "Etterbeek"],
}

# South Korea: Provinces & Metropolitan Cities
KR_PROVINCES = {
    "Seoul": ["Seoul", "Gangnam", "Seocho", "Songpa", "Yeongdeungpo", "Mapo", "Jung-gu", "Jongno", "Yongsan", "Seongdong", "Guro", "Geumcheon"],
    "Gyeonggi": ["Suwon", "Seongnam", "Yongin", "Goyang", "Bucheon", "Hwaseong", "Ansan", "Anyang", "Pyeongtaek", "Siheung", "Gimpo", "Paju", "Uijeongbu", "Gwangju", "Hanam"],
    "Busan": ["Busan", "Haeundae", "Busanjin", "Sasang", "Saha", "Geumjeong"],
    "Incheon": ["Incheon", "Songdo", "Bupyeong", "Namdong", "Seo-gu", "Yeonsu"],
    "Daegu": ["Daegu", "Suseong", "Dalseo", "Buk-gu", "Dong-gu"],
    "Daejeon": ["Daejeon", "Yuseong", "Seo-gu", "Daedeok"],
    "Gwangju": ["Gwangju", "Buk-gu", "Gwangsan", "Seo-gu"],
    "Ulsan": ["Ulsan", "Nam-gu", "Jung-gu", "Ulju"],
    "South Gyeongsang": ["Changwon", "Gimhae", "Yangsan", "Jinju", "Geoje"],
    "North Gyeongsang": ["Pohang", "Gumi", "Gyeongju", "Gyeongsan", "Andong"],
    "South Chungcheong": ["Cheonan", "Asan", "Seosan", "Dangjin", "Nonsan"],
    "North Chungcheong": ["Cheongju", "Chungju", "Jecheon"],
}

# Portugal: Districts
PT_DISTRICTS = {
    "Lisbon": ["Lisbon", "Sintra", "Cascais", "Loures", "Amadora", "Oeiras", "Odivelas", "Vila Franca de Xira"],
    "Porto": ["Porto", "Vila Nova de Gaia", "Matosinhos", "Gondomar", "Maia", "Póvoa de Varzim", "Santo Tirso"],
    "Braga": ["Braga", "Guimarães", "Vila Nova de Famalicão", "Barcelos"],
    "Setúbal": ["Setúbal", "Almada", "Seixal", "Barreiro", "Moita", "Sesimbra"],
    "Aveiro": ["Aveiro", "Santa Maria da Feira", "Oliveira de Azeméis", "Ovar"],
    "Faro": ["Faro", "Portimão", "Loulé", "Albufeira", "Olhão", "Lagos"],
    "Coimbra": ["Coimbra", "Figueira da Foz", "Cantanhede"],
}

# Finland: Regions
FI_REGIONS = {
    "Uusimaa": ["Helsinki", "Espoo", "Vantaa", "Porvoo", "Lohja", "Hyvinkää", "Järvenpää", "Nurmijärvi", "Kirkkonummi"],
    "Pirkanmaa": ["Tampere", "Nokia", "Ylöjärvi", "Kangasala", "Lempäälä", "Valkeakoski"],
    "Southwest Finland": ["Turku", "Salo", "Kaarina", "Raisio", "Naantali"],
    "North Ostrobothnia": ["Oulu", "Raahe", "Kuusamo", "Ylivieska"],
    "Central Finland": ["Jyväskylä", "Jämsä", "Äänekoski"],
    "Pohjois-Savo": ["Kuopio", "Iisalmi", "Varkaus"],
    "Päijät-Häme": ["Lahti", "Heinola", "Hollola"],
}

# Norway: Counties
NO_COUNTIES = {
    "Oslo": ["Oslo"],
    "Viken": ["Bærum", "Drammen", "Asker", "Lillestrøm", "Fredrikstad", "Sarpsborg", "Lørenskog"],
    "Vestland": ["Bergen", "Øygarden", "Askøy", "Alver"],
    "Rogaland": ["Stavanger", "Sandnes", "Haugesund", "Karmøy", "Sola", "Time"],
    "Trøndelag": ["Trondheim", "Stjørdal", "Steinkjer", "Levanger"],
    "Innlandet": ["Ringsaker", "Gjøvik", "Hamar", "Lillehammer"],
    "Agder": ["Kristiansand", "Arendal", "Grimstad"],
}

# Czech Republic: Regions
CZ_REGIONS = {
    "Prague": ["Prague"],
    "Central Bohemian": ["Kladno", "Mladá Boleslav", "Příbram", "Kolín", "Kutná Hora"],
    "South Moravian": ["Brno", "Znojmo", "Hodonín", "Břeclav"],
    "Moravian-Silesian": ["Ostrava", "Havířov", "Opava", "Frýdek-Místek", "Karviná"],
    "Plzeň": ["Plzeň", "Klatovy", "Rokycany"],
    "Ústí nad Labem": ["Ústí nad Labem", "Most", "Děčín", "Teplice", "Chomutov"],
    "Olomouc": ["Olomouc", "Prostějov", "Přerov", "Šumperk"],
}

# Greece: Regions
GR_REGIONS = {
    "Attica": ["Athens", "Piraeus", "Peristeri", "Kallithea", "Glyfada", "Marousi", "Chalandri", "Nea Smyrni", "Kifisia"],
    "Central Macedonia": ["Thessaloniki", "Kalamaria", "Katerini", "Serres", "Veria", "Giannitsa"],
    "Crete": ["Heraklion", "Chania", "Rethymno", "Agios Nikolaos"],
    "Western Greece": ["Patras", "Agrinio", "Aigio"],
    "Thessaly": ["Larissa", "Volos", "Trikala", "Karditsa"],
}

# Turkey: Major Provinces
TR_PROVINCES = {
    "Istanbul": ["Istanbul", "Kadıköy", "Beşiktaş", "Şişli", "Üsküdar", "Bakırköy", "Beyoğlu", "Maltepe", "Ataşehir", "Pendik", "Ümraniye", "Esenyurt"],
    "Ankara": ["Ankara", "Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan"],
    "Izmir": ["Izmir", "Konak", "Karşıyaka", "Bornova", "Buca", "Bayraklı", "Çiğli"],
    "Bursa": ["Bursa", "Osmangazi", "Nilüfer", "Yıldırım", "İnegöl"],
    "Antalya": ["Antalya", "Muratpaşa", "Kepez", "Konyaaltı", "Alanya", "Manavgat"],
    "Kocaeli": ["Gebze", "İzmit", "Darıca", "Körfez", "Gölcük"],
    "Adana": ["Adana", "Seyhan", "Yüreğir", "Çukurova"],
}

# Israel: Districts
IL_DISTRICTS = {
    "Tel Aviv": ["Tel Aviv", "Holon", "Bnei Brak", "Bat Yam", "Ramat Gan", "Herzliya", "Giv'atayim"],
    "Central": ["Rishon LeZion", "Petah Tikva", "Netanya", "Rehovot", "Kfar Saba", "Ra'anana", "Lod", "Ramla", "Modi'in"],
    "Jerusalem": ["Jerusalem", "Beit Shemesh"],
    "Haifa": ["Haifa", "Hadera", "Kiryat Ata", "Kiryat Motzkin", "Kiryat Bialik"],
    "Southern": ["Be'er Sheva", "Ashdod", "Ashkelon", "Eilat"],
}

# Saudi Arabia: Provinces
SA_PROVINCES = {
    "Riyadh": ["Riyadh", "Al Kharj", "Diriyah"],
    "Makkah": ["Jeddah", "Mecca", "Taif"],
    "Eastern Province": ["Dammam", "Khobar", "Dhahran", "Jubail", "Al Ahsa", "Qatif"],
    "Madinah": ["Medina", "Yanbu"],
}

# South Africa: Provinces
ZA_PROVINCES = {
    "Gauteng": ["Johannesburg", "Pretoria", "Sandton", "Centurion", "Midrand", "Roodepoort", "Randburg", "Kempton Park", "Benoni", "Soweto"],
    "Western Cape": ["Cape Town", "Stellenbosch", "George", "Paarl", "Somerset West", "Bellville"],
    "KwaZulu-Natal": ["Durban", "Pietermaritzburg", "Pinetown", "Umhlanga", "Chatsworth", "Newcastle"],
    "Eastern Cape": ["Port Elizabeth", "Gqeberha", "East London", "Uitenhage"],
}

# Indonesia: Provinces
ID_PROVINCES = {
    "Jakarta": ["Jakarta", "Central Jakarta", "South Jakarta", "West Jakarta", "East Jakarta", "North Jakarta"],
    "West Java": ["Bandung", "Bekasi", "Depok", "Bogor", "Cimahi", "Tasikmalaya", "Cirebon"],
    "East Java": ["Surabaya", "Malang", "Sidoarjo", "Kediri", "Gresik"],
    "Central Java": ["Semarang", "Surakarta", "Solo", "Magelang", "Pekalongan"],
    "Banten": ["Tangerang", "South Tangerang", "Serang", "Cilegon"],
    "Bali": ["Denpasar", "Badung", "Kuta", "Ubud"],
}

# Malaysia: States
MY_STATES = {
    "Kuala Lumpur": ["Kuala Lumpur"],
    "Selangor": ["Petaling Jaya", "Shah Alam", "Subang Jaya", "Klang", "Cyberjaya", "Puchong", "Ampang", "Kajang"],
    "Penang": ["George Town", "Butterworth", "Bayan Lepas", "Bukit Mertajam"],
    "Johor": ["Johor Bahru", "Iskandar Puteri", "Batu Pahat", "Muar", "Kulai"],
    "Perak": ["Ipoh", "Taiping"],
    "Sarawak": ["Kuching", "Miri"],
    "Sabah": ["Kota Kinabalu", "Sandakan"],
}

# Philippines: Regions
PH_REGIONS = {
    "National Capital Region": ["Manila", "Quezon City", "Makati", "Taguig", "Pasig", "Mandaluyong", "Caloocan", "Parañaque", "Pasay", "Muntinlupa", "Las Piñas"],
    "Calabarzon": ["Calamba", "Antipolo", "Dasmariñas", "Bacoor", "Santa Rosa", "Batangas City", "Imus"],
    "Central Visayas": ["Cebu City", "Mandaue", "Lapu-Lapu", "Talay"],
    "Davao Region": ["Davao City", "Tagum"],
}

# Thailand: Provinces
TH_PROVINCES = {
    "Bangkok": ["Bangkok"],
    "Central": ["Nonthaburi", "Pak Kret", "Samut Prakan", "Pathum Thani", "Ayutthaya"],
    "Eastern": ["Chonburi", "Pattaya", "Rayong", "Si Racha"],
    "Northern": ["Chiang Mai", "Chiang Rai", "Phitsanulok", "Nakhon Sawan"],
    "Southern": ["Phuket", "Hat Yai", "Surat Thani", "Koh Samui"],
}

# Vietnam: Provinces & Major Cities
VN_PROVINCES = {
    "Ho Chi Minh City": ["Ho Chi Minh City", "Thu Duc"],
    "Hanoi": ["Hanoi"],
    "Da Nang": ["Da Nang"],
    "Hai Phong": ["Hai Phong"],
    "Can Tho": ["Can Tho"],
    "Binh Duong": ["Thu Dau Mot", "Di An", "Thuan An"],
    "Dong Nai": ["Bien Hoa"],
}

# Argentina: Provinces
AR_PROVINCES = {
    "Buenos Aires": ["Buenos Aires", "La Plata", "Mar del Plata", "Bahía Blanca", "San Isidro", "Vicente López", "Tigre", "Avellaneda", "Quilmes", "Lanús"],
    "Córdoba": ["Córdoba", "Villa María", "Río Cuarto", "Villa Carlos Paz"],
    "Santa Fe": ["Rosario", "Santa Fe", "Rafaela", "Venado Tuerto"],
    "Mendoza": ["Mendoza", "Godoy Cruz", "Guaymallén", "San Rafael"],
}

# Colombia: Departments
CO_DEPARTMENTS = {
    "Bogotá": ["Bogotá"],
    "Antioquia": ["Medellín", "Bello", "Itagüí", "Envigado", "Rionegro"],
    "Valle del Cauca": ["Cali", "Palmira", "Buenaventura", "Tuluá"],
    "Atlántico": ["Barranquilla", "Soledad"],
    "Santander": ["Bucaramanga", "Floridablanca", "Girón"],
    "Bolívar": ["Cartagena"],
}

# Chile: Regions
CL_REGIONS = {
    "Santiago Metropolitan": ["Santiago", "Providencia", "Las Condes", "Vitacura", "Puente Alto", "Maipú", "La Florida", "Ñuñoa"],
    "Valparaíso": ["Viña del Mar", "Valparaíso", "Quilpué", "Villa Alemana"],
    "Biobío": ["Concepción", "Talcahuano", "San Pedro de la Paz", "Los Ángeles"],
    "Antofagasta": ["Antofagasta", "Calama"],
}

# Egypt: Governorates
EG_GOVERNORATES = {
    "Cairo": ["Cairo", "New Cairo", "Nasr City", "Heliopolis", "Maadi", "Zamalek"],
    "Giza": ["Giza", "6th of October City", "Sheikh Zayed", "Dokki", "Mohandessin"],
    "Alexandria": ["Alexandria", "Borg El Arab"],
}

# Nigeria: States
NG_STATES = {
    "Lagos": ["Lagos", "Ikeja", "Lekki", "Victoria Island", "Ikoyi", "Surulere", "Yaba", "Apapa", "Ikorodu"],
    "Abuja": ["Abuja", "Garki", "Wuse", "Maitama", "Asokoro"],
    "Rivers": ["Port Harcourt"],
    "Oyo": ["Ibadan"],
    "Kano": ["Kano"],
}

# Pakistan: Provinces
PK_PROVINCES = {
    "Punjab": ["Lahore", "Faisalabad", "Rawalpindi", "Gujranwala", "Multan", "Sialkot"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur"],
    "Islamabad": ["Islamabad"],
    "Khyber Pakhtunkhwa": ["Peshawar", "Mardan", "Abbottabad"],
}

GEO = {
    "United States": {"states": US_STATES, "postal": US_POSTAL},
    "Canada": {"states": CA_PROVINCES, "postal": CA_POSTAL},
    "Netherlands": {"states": NL_PROVINCES},
    "India": {"states": IN_STATES, "postal": IN_POSTAL},
    "China": {"states": CN_PROVINCES, "fallback": ["size", "revenue"]},
    "Japan": {"states": JP_PREFECTURES, "fallback": ["size", "revenue"]},
    "United Kingdom": {"counties": UK_COUNTIES, "states": UK_NATIONS, "fallback": ["revenue", "size"]},
    "Germany": {"states": DE_STATES, "fallback": ["revenue", "size"]},
    "Singapore": {"cities": ["Singapore"], "fallback": ["size", "revenue"]},
    "Australia": {"states": AU_STATES, "postal": AU_POSTAL},
    "United Arab Emirates": {"cities": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain", "Al Ain"]},
    "Sweden": {"cities": ["Stockholm", "Gothenburg", "Malmö", "Uppsala", "Västerås", "Örebro", "Linköping", "Helsingborg", "Jönköping", "Norrköping", "Lund", "Umeå", "Gävle", "Borås", "Södertälje", "Eskilstuna", "Halmstad", "Växjö", "Karlstad", "Sundsvall", "Solna", "Sollentuna", "Kista", "Nacka", "Lidingö", "Täby", "Kungsbacka", "Karlskrona", "Kalmar", "Luleå"], "fallback": ["size", "revenue"]},
    "France": {"states": FR_REGIONS, "postal": FR_POSTAL, "state_postal": FR_STATE_POSTAL, "fallback": ["revenue", "size"]},
    "Ireland": {"cities": ["Dublin", "Cork", "Galway", "Limerick", "Waterford"], "fallback": ["size", "revenue"]},
    "New Zealand": {"cities": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin"], "fallback": ["size", "revenue"]},
    "Denmark": {"cities": ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg"], "fallback": ["size", "revenue"]},
    "Spain": {"cities": ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Málaga", "Murcia", "Palma", "Bilbao", "Alicante", "Córdoba", "Valladolid", "Vigo", "Gijón", "Hospitalet de Llobregat", "Vitoria-Gasteiz", "A Coruña", "Elche", "Granada", "Badalona", "Oviedo", "Cartagena", "Terrassa", "Jerez de la Frontera", "Sabadell", "Santa Cruz de Tenerife", "Pamplona", "Almería", "Fuenlabrada", "Alcalá de Henares", "Leganés", "San Sebastián", "Getafe", "Burgos"], "fallback": ["size", "revenue"]},
    "Switzerland": {"cities": ["Zurich", "Geneva", "Basel", "Lausanne", "Bern", "Winterthur", "Lucerne", "St. Gallen", "Lugano", "Biel/Bienne"], "fallback": ["size", "revenue"]},
    "Austria": {"states": AT_STATES, "fallback": ["size", "revenue"]},
    "Italy": {"states": IT_REGIONS, "fallback": ["size", "revenue"]},
    "Brazil": {"states": BR_STATES, "fallback": ["size", "revenue"]},
    "Mexico": {"states": MX_STATES, "fallback": ["size", "revenue"]},
    "Poland": {"states": PL_VOIVODESHIPS, "fallback": ["size", "revenue"]},
    "Belgium": {"states": BE_REGIONS, "fallback": ["size", "revenue"]},
    "South Korea": {"states": KR_PROVINCES, "fallback": ["size", "revenue"]},
    "Israel": {"states": IL_DISTRICTS, "fallback": ["size", "revenue"]},
    "Saudi Arabia": {"states": SA_PROVINCES, "fallback": ["size", "revenue"]},
    "South Africa": {"states": ZA_PROVINCES, "fallback": ["size", "revenue"]},
    "Turkey": {"states": TR_PROVINCES, "fallback": ["size", "revenue"]},
    "Indonesia": {"states": ID_PROVINCES, "fallback": ["size", "revenue"]},
    "Malaysia": {"states": MY_STATES, "fallback": ["size", "revenue"]},
    "Philippines": {"states": PH_REGIONS, "fallback": ["size", "revenue"]},
    "Thailand": {"states": TH_PROVINCES, "fallback": ["size", "revenue"]},
    "Vietnam": {"states": VN_PROVINCES, "fallback": ["size", "revenue"]},
    "Norway": {"states": NO_COUNTIES, "fallback": ["size", "revenue"]},
    "Finland": {"states": FI_REGIONS, "fallback": ["size", "revenue"]},
    "Portugal": {"states": PT_DISTRICTS, "fallback": ["size", "revenue"]},
    "Czech Republic": {"states": CZ_REGIONS, "fallback": ["size", "revenue"]},
    "Greece": {"states": GR_REGIONS, "fallback": ["size", "revenue"]},
    "Argentina": {"states": AR_PROVINCES, "fallback": ["size", "revenue"]},
    "Chile": {"states": CL_REGIONS, "fallback": ["size", "revenue"]},
    "Colombia": {"states": CO_DEPARTMENTS, "fallback": ["size", "revenue"]},
    "Egypt": {"states": EG_GOVERNORATES, "fallback": ["size", "revenue"]},
    "Nigeria": {"states": NG_STATES, "fallback": ["size", "revenue"]},
    "Pakistan": {"states": PK_PROVINCES, "fallback": ["size", "revenue"]},
    "Hong Kong": {"cities": ["Hong Kong", "Kowloon", "Central", "Wan Chai", "Tsim Sha Tsui", "Kwun Tong", "Sha Tin", "Tsuen Wan", "Admiralty", "Causeway Bay"], "fallback": ["size", "revenue"]},
    "Taiwan": {"cities": ["Taipei", "New Taipei", "Taichung", "Kaohsiung", "Hsinchu", "Taoyuan", "Tainan"], "fallback": ["size", "revenue"]},
    "Luxembourg": {"cities": ["Luxembourg City", "Esch-sur-Alzette", "Differdange", "Dudelange"], "fallback": ["size", "revenue"]},
    "Iceland": {"cities": ["Reykjavik", "Kopavogur", "Hafnarfjordur"], "fallback": ["size", "revenue"]},
    "Malta": {"cities": ["Valletta", "Birkirkara", "Mosta", "Sliema"], "fallback": ["size", "revenue"]},
    "Cyprus": {"cities": ["Nicosia", "Limassol", "Larnaca", "Paphos"], "fallback": ["size", "revenue"]},
    "Qatar": {"cities": ["Doha", "Al Rayyan", "Al Wakrah", "Lusail"], "fallback": ["size", "revenue"]},
    "Kuwait": {"cities": ["Kuwait City", "Al Ahmadi", "Hawalli", "Salmiya"], "fallback": ["size", "revenue"]},
    "Oman": {"cities": ["Muscat", "Salalah", "Seeb", "Sohar"], "fallback": ["size", "revenue"]},
    "Bahrain": {"cities": ["Manama", "Riffa", "Muharraq"], "fallback": ["size", "revenue"]},
    "Kenya": {"cities": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"], "fallback": ["size", "revenue"]},
    "Ghana": {"cities": ["Accra", "Kumasi", "Tamale", "Sekondi-Takoradi"], "fallback": ["size", "revenue"]},
    "Morocco": {"cities": ["Casablanca", "Rabat", "Fes", "Tangier", "Marrakech", "Agadir"], "fallback": ["size", "revenue"]},
    "Costa Rica": {"cities": ["San José", "Alajuela", "Cartago", "Heredia"], "fallback": ["size", "revenue"]},
    "Panama": {"cities": ["Panama City", "San Miguelito", "David", "Colón"], "fallback": ["size", "revenue"]},
    "Dominican Republic": {"cities": ["Santo Domingo", "Santiago de los Caballeros", "Santo Domingo Este"], "fallback": ["size", "revenue"]},
    "Ecuador": {"cities": ["Guayaquil", "Quito", "Cuenca", "Santo Domingo"], "fallback": ["size", "revenue"]},
    "Uruguay": {"cities": ["Montevideo", "Ciudad de la Costa", "Salto", "Paysandú"], "fallback": ["size", "revenue"]},
    "Hungary": {"cities": ["Budapest", "Debrecen", "Szeged", "Miskolc", "Pécs", "Győr", "Nyíregyháza"], "fallback": ["size", "revenue"]},
    "Romania": {"cities": ["Bucharest", "Cluj-Napoca", "Timișoara", "Iași", "Constanța", "Craiova", "Brașov"], "fallback": ["size", "revenue"]},
    "Peru": {"cities": ["Lima", "Callao", "Arequipa", "Trujillo", "Chiclayo", "Piura", "Cusco"], "fallback": ["size", "revenue"]},
}