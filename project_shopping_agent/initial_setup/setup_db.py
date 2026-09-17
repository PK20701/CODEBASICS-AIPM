import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store.db")


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            description TEXT,
            is_organic INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            rating REAL,
            reviewer_name TEXT,
            review_text TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            ordered_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    products = [
        # --- Honey (8) ---
        (1,  "Organic Raw Honey",            "honey",        14.99, "Pure organic raw honey, unfiltered and cold-pressed",                1),
        (2,  "Wildflower Honey",             "honey",        12.99, "Natural wildflower honey from local beekeepers",                     0),
        (3,  "Organic Manuka Honey",         "honey",        29.99, "Premium organic Manuka honey from New Zealand",                      1),
        (4,  "Clover Honey",                 "honey",         8.99, "Classic clover honey, smooth and sweet",                             0),
        (5,  "Organic Buckwheat Honey",      "honey",        18.99, "Dark and robust organic buckwheat honey, antioxidant-rich",          1),
        (6,  "Orange Blossom Honey",         "honey",        15.99, "Light and floral orange blossom honey",                              0),
        (7,  "Organic Acacia Honey",         "honey",        17.99, "Light and mild organic acacia honey, low glycemic index",            1),
        (8,  "Creamed Honey",                "honey",        11.99, "Smooth creamed honey with spreadable texture",                       0),
        # --- Oils (4) ---
        (9,  "Organic Extra Virgin Olive Oil","oil",         16.99, "Cold-pressed organic EVOO from Mediterranean olives",               1),
        (10, "Coconut Oil",                  "oil",          12.49, "Refined coconut oil, great for high-heat cooking",                   0),
        (11, "Organic Flaxseed Oil",         "oil",          14.99, "Cold-pressed organic flaxseed oil, rich in omega-3",                 1),
        (12, "Avocado Oil",                  "oil",          18.99, "Cold-pressed avocado oil, high smoke point",                         0),
        # --- Nuts & Seeds (4) ---
        (13, "Organic Almonds",              "nuts",         11.99, "Raw organic almonds, unsalted, non-GMO certified",                   1),
        (14, "Roasted Cashews",              "nuts",          9.99, "Lightly salted dry-roasted cashews",                                 0),
        (15, "Organic Chia Seeds",           "seeds",         8.49, "Organic black chia seeds, high in fiber and omega-3",                1),
        (16, "Mixed Nuts",                   "nuts",         13.99, "Premium mix of walnuts, pecans, almonds and Brazil nuts",            0),
        # --- Grains & Cereals (4) ---
        (17, "Organic Quinoa",               "grains",       10.99, "Organic white quinoa, complete protein, gluten-free",                1),
        (18, "Rolled Oats",                  "grains",        5.49, "Whole grain rolled oats, great for porridge and baking",             0),
        (19, "Organic Brown Rice",           "grains",        7.99, "Long-grain organic brown rice, naturally gluten-free",               1),
        (20, "Steel-Cut Oats",               "grains",        6.99, "Traditional steel-cut oats, low GI, hearty texture",                 0),
        # --- Tea & Coffee (4) ---
        (21, "Organic Green Tea",            "tea",          12.99, "Japanese organic sencha green tea, 50 bags",                         1),
        (22, "Chamomile Tea",                "tea",           8.99, "Dried chamomile flowers, caffeine-free, soothing",                   0),
        (23, "Organic Ethiopian Coffee",     "coffee",       16.99, "Single-origin organic Arabica, medium roast whole bean",             1),
        (24, "Dark Roast Espresso Blend",    "coffee",       14.49, "Bold dark roast espresso blend, ground",                             0),
        # --- Snacks (4) ---
        (25, "Organic Granola",              "snacks",        9.99, "Organic oat granola with honey, almonds and dried cranberries",      1),
        (26, "Rice Cakes",                   "snacks",        4.49, "Lightly salted brown rice cakes, low calorie",                       0),
        (27, "Organic Dried Mango",          "snacks",        7.99, "Unsweetened organic dried mango slices, no preservatives",           1),
        (28, "Trail Mix",                    "snacks",        8.49, "Classic trail mix with raisins, M&Ms, peanuts and sunflower seeds",  0),
        # --- Dairy Alternatives (4) ---
        (29, "Organic Almond Milk",          "dairy-alt",     4.99, "Unsweetened organic almond milk, fortified with calcium",            1),
        (30, "Oat Milk",                     "dairy-alt",     4.49, "Barista-style oat milk, great for coffee",                           0),
        (31, "Organic Coconut Milk",         "dairy-alt",     3.99, "Full-fat organic coconut milk, great for curries",                   1),
        (32, "Soy Milk",                     "dairy-alt",     3.49, "Unsweetened soy milk, high protein",                                 0),
    ]
    cursor.executemany("INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?)", products)

    # Avg ratings (for reference):
    # Honey:      1→4.625✓  2→3.833  3→4.833($$)  4→3.5  5→4.625✓  6→4.167  7→4.75✓  8→4.0
    # Oils:       9→4.67   10→3.67  11→4.5        12→4.33
    # Nuts/Seeds: 13→4.75  14→4.0   15→4.5        16→3.75
    # Grains:     17→4.67  18→4.33  19→4.5        20→3.83
    # Tea/Coffee: 21→4.67  22→4.17  23→4.75       24→4.0
    # Snacks:     25→4.5   26→3.83  27→4.67       28→3.67
    # Dairy-alt:  29→4.5   30→4.33  31→4.5        32→3.67
    reviews = [
        # Honey
        (1, 5.0, "Alice",   "Amazing honey! Best I've ever tried."),
        (1, 4.0, "Bob",     "Good quality, will buy again."),
        (1, 5.0, "Carol",   "Excellent raw flavor, very pure."),
        (1, 4.5, "Dave",    "Very good, love that it's unfiltered."),
        (2, 4.0, "Eve",     "Decent honey for the price."),
        (2, 3.5, "Frank",   "Average, nothing special."),
        (2, 4.0, "Grace",   "Good everyday honey."),
        (3, 5.0, "Henry",   "Worth every penny, incredible quality."),
        (3, 4.5, "Iris",    "Excellent antibacterial properties."),
        (3, 5.0, "Jack",    "Best honey I have ever tasted."),
        (4, 3.5, "Kate",    "Okay for cooking, nothing fancy."),
        (4, 3.5, "Leo",     "Nothing special, pretty generic."),
        (4, 3.5, "Mia",     "Average clover honey."),
        (5, 5.0, "Noah",    "Rich bold flavor, great in tea."),
        (5, 4.0, "Olivia",  "Good strong honey, unique taste."),
        (5, 5.0, "Paul",    "Love the dark color and depth."),
        (5, 4.5, "Quinn",   "Great organic option at this price."),
        (6, 4.0, "Rachel",  "Nice floral flavor."),
        (6, 4.5, "Sam",     "Lovely and delicate."),
        (6, 4.0, "Tina",    "Good for baking."),
        (7, 5.0, "Uma",     "Perfect mild flavor, love it!"),
        (7, 4.5, "Victor",  "Excellent light honey."),
        (7, 4.5, "Wendy",   "Great product, very pure taste."),
        (7, 5.0, "Xavier",  "Wonderful, highly recommend."),
        (8, 4.0, "Yvonne",  "Nice spreadable texture."),
        (8, 4.0, "Zack",    "Good on toast."),
        (8, 4.0, "Amy",     "Decent creamed honey."),
        # Oils
        (9,  5.0, "Brian",  "Best olive oil I've used, very fresh."),
        (9,  4.5, "Clara",  "Great flavor, organic certified."),
        (9,  4.5, "Derek",  "Excellent quality, love it."),
        (10, 4.0, "Elena",  "Good for frying, neutral taste."),
        (10, 3.5, "Felix",  "Does the job, nothing exciting."),
        (10, 3.5, "Gina",   "Decent but slightly greasy."),
        (11, 5.0, "Harry",  "Great for smoothies, very fresh."),
        (11, 4.0, "Isla",   "Good omega-3 source, mild flavor."),
        (11, 4.5, "James",  "Love this for salad dressings."),
        (12, 4.5, "Karen",  "Excellent smoke point, tastes great."),
        (12, 4.0, "Liam",   "Good all-purpose oil."),
        (12, 4.5, "Maya",   "Great for cooking and salads."),
        # Nuts & Seeds
        (13, 5.0, "Nate",   "Crunchy and fresh, great snack."),
        (13, 4.5, "Olivia", "Love that they're organic and raw."),
        (13, 4.5, "Peter",  "Perfect size, very fresh."),
        (13, 5.0, "Rita",   "Best almonds I've bought online."),
        (14, 4.0, "Steve",  "Good cashews, nice crunch."),
        (14, 4.0, "Tara",   "Tasty but slightly over-salted."),
        (14, 4.0, "Ursula", "Good value for the quantity."),
        (15, 4.5, "Vince",  "Easy to add to smoothies, love it."),
        (15, 4.5, "Wanda",  "Great fiber source, very fresh."),
        (15, 4.5, "Xena",   "Good quality organic chia seeds."),
        (16, 4.0, "Yuri",   "Good mix, well-balanced variety."),
        (16, 3.5, "Zara",   "A bit too many peanuts for my taste."),
        (16, 4.0, "Alex",   "Nice mix for snacking."),
        (16, 3.5, "Blake",  "Would prefer fewer raisins."),
        # Grains
        (17, 5.0, "Chloe",  "Cooks perfectly, great nutty flavor."),
        (17, 4.5, "Dylan",  "Excellent protein content, love it."),
        (17, 4.5, "Ella",   "Best quinoa I've tried."),
        (18, 4.5, "Finn",   "Great oats, cook quickly and evenly."),
        (18, 4.0, "Gabi",   "Good quality, nice texture."),
        (18, 4.5, "Hugo",   "Reliable everyday oats."),
        (19, 4.5, "Irene",  "Nice chewy texture, great organic choice."),
        (19, 4.5, "Jake",   "Good quality, cooks evenly."),
        (19, 4.5, "Kara",   "Love the organic certification."),
        (20, 4.0, "Lars",   "Great texture, a bit longer to cook."),
        (20, 3.5, "Mona",   "Takes forever to cook but tastes good."),
        (20, 4.0, "Ned",    "Hearty and filling."),
        # Tea & Coffee
        (21, 5.0, "Opal",   "Delicate flavor, very smooth."),
        (21, 4.5, "Phil",   "Best green tea I've had, very fresh."),
        (21, 4.5, "Quinn",  "Great quality, calming and tasty."),
        (22, 4.0, "Rose",   "Very soothing before bed."),
        (22, 4.5, "Seth",   "Lovely floral notes, very relaxing."),
        (22, 4.0, "Tess",   "Good chamomile, nice and mild."),
        (23, 5.0, "Uri",    "Best coffee I've ever brewed at home."),
        (23, 4.5, "Vera",   "Amazing single-origin flavor."),
        (23, 4.5, "Will",   "Very smooth with great aroma."),
        (23, 5.0, "Xara",   "Exceptional quality, worth every penny."),
        (24, 4.0, "Yael",   "Strong and bold, perfect espresso."),
        (24, 4.0, "Zion",   "Good dark roast, consistent grind."),
        (24, 4.0, "Abe",    "Solid everyday espresso blend."),
        # Snacks
        (25, 4.5, "Beth",   "Delicious and not too sweet."),
        (25, 4.5, "Cole",   "Great texture, love the almonds."),
        (25, 4.5, "Dana",   "My go-to breakfast granola."),
        (26, 4.0, "Earl",   "Light and crispy, good for dieting."),
        (26, 3.5, "Faye",   "A bit bland but does the job."),
        (26, 4.0, "Glen",   "Good value, decent snack."),
        (27, 5.0, "Hope",   "So sweet and chewy, love these!"),
        (27, 4.5, "Ivan",   "Great that there's no added sugar."),
        (27, 4.5, "Jade",   "Perfect snack, very natural taste."),
        (28, 4.0, "Kent",   "Good mix, great for hiking."),
        (28, 3.5, "Luna",   "Too many M&Ms, prefer less candy."),
        (28, 3.5, "Marc",   "Decent but not my favorite mix."),
        # Dairy Alternatives
        (29, 4.5, "Nina",   "Great in coffee, smooth texture."),
        (29, 4.5, "Omar",   "Love the organic certification."),
        (29, 4.5, "Pam",    "Tastes great and not too thin."),
        (30, 4.5, "Rex",    "Perfect for lattes, froths well."),
        (30, 4.0, "Sara",   "Good oat milk, slightly sweet."),
        (30, 4.5, "Tom",    "Best barista oat milk I've tried."),
        (31, 4.5, "Una",    "Creamy and rich, great for curries."),
        (31, 4.5, "Vito",   "Full fat and delicious."),
        (31, 4.5, "Wren",   "Perfect coconut milk, great quality."),
        (32, 4.0, "Xio",    "Good protein content, mild flavor."),
        (32, 3.5, "Yosef",  "Slightly thin but good for cereal."),
        (32, 3.5, "Zola",   "Decent soy milk, nothing special."),
    ]
    cursor.execute("DELETE FROM reviews")
    cursor.executemany(
        "INSERT INTO reviews (product_id, rating, reviewer_name, review_text) VALUES (?, ?, ?, ?)",
        reviews,
    )

    conn.commit()
    conn.close()
    print(f"Database created at: {DB_PATH}")


if __name__ == "__main__":
    create_database()
