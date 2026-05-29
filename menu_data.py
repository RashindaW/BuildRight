"""Menu data for the Cut_Dry ordering app.

This file is the single source of truth for the menu; the backend seed
(backend/app/seed/seed.py) loads it into the database.

Per-item schema:
  id, name, category, description, price (float USD), dietary_tags, keywords
  + optional: allergens, calories, spice_level (0-3), featured, image_url, options

Controlled vocabularies
  dietary_tags : vegan, vegetarian, gluten-free, dairy-free, contains-nuts
  allergens    : gluten, dairy, egg, soy, tree-nuts, peanuts, shellfish, fish, sesame
  categories   : salad, sandwich, pasta, drink, dessert, starter, pizza, main, side, kids

NOTE: The original 15 items keep their exact id / name / category / price /
dietary_tags / keywords so the golden test suite stays valid. New items and the
optional fields (allergens, calories, modifiers) extend the menu.
"""

MENU_DATA = [
    # ============================================================
    # Salads
    # ============================================================
    {
        "id": "caesar-salad",
        "name": "Classic Caesar Salad",
        "category": "salad",
        "description": "Crisp romaine, shaved parmesan, garlic croutons, and house Caesar dressing with anchovy.",
        "price": 11.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["caesar", "romaine", "parmesan"],
        "allergens": ["gluten", "dairy", "egg", "fish"],
        "calories": 480,
        "spice_level": 0,
        "featured": True,
    },
    {
        "id": "vegan-buddha-bowl",
        "name": "Vegan Buddha Bowl",
        "category": "salad",
        "description": "Quinoa, roasted chickpeas, kale, avocado, and tahini-lemon dressing.",
        "price": 13.95,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["bowl", "quinoa", "chickpea", "avocado", "healthy"],
        "allergens": ["sesame"],
        "calories": 540,
        "spice_level": 0,
        "featured": True,
    },
    {
        "id": "chicken-cobb-salad",
        "name": "Grilled Chicken Cobb Salad",
        "category": "salad",
        "description": "Grilled chicken breast, bacon, hard-boiled egg, avocado, and blue cheese over mixed greens.",
        "price": 14.50,
        "dietary_tags": ["gluten-free"],
        "keywords": ["chicken", "cobb", "bacon", "egg", "avocado"],
        "allergens": ["dairy", "egg"],
        "calories": 620,
        "spice_level": 0,
    },
    # ============================================================
    # Sandwiches / Wraps
    # ============================================================
    {
        "id": "turkey-club",
        "name": "Turkey Club Sandwich",
        "category": "sandwich",
        "description": "Sliced turkey, crispy bacon, lettuce, tomato, and mayo on toasted sourdough.",
        "price": 12.75,
        "dietary_tags": [],
        "keywords": ["turkey", "bacon", "lettuce", "tomato", "club"],
        "allergens": ["gluten", "egg"],
        "calories": 700,
        "spice_level": 0,
    },
    {
        "id": "vegan-avocado-wrap",
        "name": "Vegan Avocado Wrap",
        "category": "sandwich",
        "description": "Mashed avocado, hummus, spinach, cucumber, and pickled onion in a whole-wheat tortilla.",
        "price": 11.95,
        "dietary_tags": ["vegan", "dairy-free"],
        "keywords": ["wrap", "avocado", "hummus", "spinach", "tortilla"],
        "allergens": ["gluten", "sesame"],
        "calories": 520,
        "spice_level": 0,
    },
    {
        "id": "gf-veggie-panini",
        "name": "Gluten-Free Grilled Veggie Panini",
        "category": "sandwich",
        "description": "Zucchini, bell pepper, eggplant, and mozzarella pressed on gluten-free bread with pesto.",
        "price": 13.25,
        "dietary_tags": ["vegetarian", "gluten-free"],
        "keywords": ["panini", "veggie", "vegetable", "grilled", "zucchini"],
        "allergens": ["dairy", "tree-nuts"],
        "calories": 560,
        "spice_level": 0,
    },
    # ============================================================
    # Pasta
    # ============================================================
    {
        "id": "margherita-pasta",
        "name": "Margherita Pasta",
        "category": "pasta",
        "description": "Penne tossed with San Marzano tomato sauce, fresh basil, and mozzarella pearls.",
        "price": 13.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["pasta", "tomato", "basil", "mozzarella", "pomodoro", "penne"],
        "allergens": ["gluten", "dairy"],
        "calories": 650,
        "spice_level": 0,
    },
    {
        "id": "shrimp-linguine",
        "name": "Shrimp Linguine",
        "category": "pasta",
        "description": "Linguine with sauteed shrimp, garlic, white wine, and chili flakes.",
        "price": 17.95,
        "dietary_tags": ["dairy-free"],
        "keywords": ["pasta", "shrimp", "seafood", "linguine", "garlic"],
        "allergens": ["gluten", "shellfish"],
        "calories": 680,
        "spice_level": 1,
    },
    # ============================================================
    # Drinks
    # ============================================================
    {
        "id": "classic-latte",
        "name": "Classic Latte",
        "category": "drink",
        "description": "Double espresso topped with steamed milk and a thin layer of foam.",
        "price": 4.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["latte", "coffee", "espresso", "milk", "hot"],
        "allergens": ["dairy"],
        "calories": 150,
        "spice_level": 0,
        "options": [
            {"name": "Size", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "Small", "price_delta": 0, "is_default": True},
                {"name": "Large", "price_delta": 1.00},
            ]},
            {"name": "Milk", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "Whole milk", "price_delta": 0, "is_default": True},
                {"name": "Oat milk", "price_delta": 0.75},
                {"name": "Almond milk", "price_delta": 0.75},
            ]},
        ],
    },
    {
        "id": "iced-oat-latte",
        "name": "Iced Oat Milk Latte",
        "category": "drink",
        "description": "Double espresso shaken with cold oat milk over ice.",
        "price": 5.25,
        "dietary_tags": ["vegan", "dairy-free"],
        "keywords": ["iced", "coffee", "oat", "cold", "espresso"],
        "allergens": [],
        "calories": 120,
        "spice_level": 0,
    },
    {
        "id": "fresh-lemonade",
        "name": "Fresh Lemonade",
        "category": "drink",
        "description": "Hand-squeezed lemons, cane sugar, and sparkling water over ice.",
        "price": 3.75,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["lemonade", "lemon", "cold", "refreshing", "sweet"],
        "allergens": [],
        "calories": 140,
        "spice_level": 0,
    },
    {
        "id": "mango-smoothie",
        "name": "Mango Smoothie",
        "category": "drink",
        "description": "Frozen mango blended with vanilla yogurt and a hint of lime.",
        "price": 5.95,
        "dietary_tags": ["vegetarian", "gluten-free"],
        "keywords": ["smoothie", "mango", "yogurt", "cold", "fruit", "sweet"],
        "allergens": ["dairy"],
        "calories": 240,
        "spice_level": 0,
    },
    # ============================================================
    # Desserts
    # ============================================================
    {
        "id": "chocolate-lava-cake",
        "name": "Chocolate Lava Cake",
        "category": "dessert",
        "description": "Warm chocolate cake with a molten chocolate center, served with vanilla ice cream.",
        "price": 7.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["chocolate", "cake", "lava", "dessert", "sweet", "warm"],
        "allergens": ["gluten", "dairy", "egg"],
        "calories": 590,
        "spice_level": 0,
        "featured": True,
    },
    {
        "id": "almond-croissant",
        "name": "Almond Croissant",
        "category": "dessert",
        "description": "Flaky butter croissant filled with almond cream and topped with sliced almonds.",
        "price": 4.25,
        "dietary_tags": ["vegetarian", "contains-nuts"],
        "keywords": ["pastry", "almond", "croissant", "breakfast", "sweet"],
        "allergens": ["gluten", "dairy", "egg", "tree-nuts"],
        "calories": 410,
        "spice_level": 0,
    },
    {
        "id": "flourless-chocolate-torte",
        "name": "Flourless Chocolate Torte",
        "category": "dessert",
        "description": "Dense, rich chocolate torte with a dusting of cocoa powder.",
        "price": 6.75,
        "dietary_tags": ["vegetarian", "gluten-free"],
        "keywords": ["chocolate", "torte", "flourless", "cake", "dessert", "sweet"],
        "allergens": ["dairy", "egg"],
        "calories": 520,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Starters
    # ============================================================
    {
        "id": "tomato-bruschetta",
        "name": "Tomato Bruschetta",
        "category": "starter",
        "description": "Toasted ciabatta topped with marinated tomatoes, garlic, and fresh basil.",
        "price": 7.25,
        "dietary_tags": ["vegan", "dairy-free"],
        "keywords": ["bruschetta", "tomato", "bread", "starter", "appetizer", "basil"],
        "allergens": ["gluten"],
        "calories": 320,
        "spice_level": 0,
    },
    {
        "id": "soup-of-the-day",
        "name": "Soup of the Day",
        "category": "starter",
        "description": "A rotating bowl of seasonal vegetable soup served with a gluten-free cracker.",
        "price": 6.50,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["soup", "starter", "warm", "vegetable", "seasonal"],
        "allergens": [],
        "calories": 210,
        "spice_level": 0,
    },
    {
        "id": "crispy-calamari",
        "name": "Crispy Calamari",
        "category": "starter",
        "description": "Lightly battered calamari rings with lemon aioli and marinara.",
        "price": 10.95,
        "dietary_tags": [],
        "keywords": ["calamari", "squid", "fried", "seafood", "starter"],
        "allergens": ["gluten", "egg", "shellfish"],
        "calories": 480,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Pizza
    # ============================================================
    {
        "id": "margherita-pizza",
        "name": "Margherita Pizza",
        "category": "pizza",
        "description": "Wood-fired pizza with San Marzano tomato, fresh mozzarella, and basil.",
        "price": 13.95,
        "dietary_tags": ["vegetarian"],
        "keywords": ["pizza", "margherita", "mozzarella", "tomato", "basil"],
        "allergens": ["gluten", "dairy"],
        "calories": 760,
        "spice_level": 0,
        "featured": True,
        "options": [
            {"name": "Size", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "10\"", "price_delta": 0, "is_default": True},
                {"name": "14\"", "price_delta": 4.00},
            ]},
        ],
    },
    {
        "id": "pepperoni-pizza",
        "name": "Pepperoni Pizza",
        "category": "pizza",
        "description": "Wood-fired pizza with tomato, mozzarella, and spicy pepperoni.",
        "price": 15.50,
        "dietary_tags": [],
        "keywords": ["pizza", "pepperoni", "cheese", "meat"],
        "allergens": ["gluten", "dairy"],
        "calories": 900,
        "spice_level": 1,
        "options": [
            {"name": "Size", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "10\"", "price_delta": 0, "is_default": True},
                {"name": "14\"", "price_delta": 4.00},
            ]},
        ],
    },
    {
        "id": "vegan-garden-pizza",
        "name": "Vegan Garden Pizza",
        "category": "pizza",
        "description": "Tomato base with vegan mozzarella, peppers, mushrooms, red onion, and arugula.",
        "price": 14.95,
        "dietary_tags": ["vegan", "dairy-free"],
        "keywords": ["pizza", "vegan", "vegetable", "garden", "mushroom"],
        "allergens": ["gluten", "soy"],
        "calories": 700,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Mains
    # ============================================================
    {
        "id": "grilled-salmon",
        "name": "Grilled Atlantic Salmon",
        "category": "main",
        "description": "Grilled salmon fillet with lemon-herb butter, served over roasted vegetables.",
        "price": 21.50,
        "dietary_tags": ["gluten-free"],
        "keywords": ["salmon", "fish", "grilled", "main", "seafood"],
        "allergens": ["fish", "dairy"],
        "calories": 640,
        "spice_level": 0,
        "featured": True,
    },
    {
        "id": "ribeye-steak",
        "name": "Ribeye Steak",
        "category": "main",
        "description": "10oz char-grilled ribeye with peppercorn jus and hand-cut fries.",
        "price": 27.95,
        "dietary_tags": [],
        "keywords": ["steak", "ribeye", "beef", "main", "grilled"],
        "allergens": [],
        "calories": 980,
        "spice_level": 0,
        "options": [
            {"name": "Doneness", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "Medium-rare", "price_delta": 0, "is_default": True},
                {"name": "Medium", "price_delta": 0},
                {"name": "Well-done", "price_delta": 0},
            ]},
        ],
    },
    {
        "id": "mushroom-risotto",
        "name": "Wild Mushroom Risotto",
        "category": "main",
        "description": "Creamy arborio rice with wild mushrooms, white wine, and parmesan.",
        "price": 16.75,
        "dietary_tags": ["vegetarian", "gluten-free"],
        "keywords": ["risotto", "mushroom", "rice", "main", "creamy"],
        "allergens": ["dairy"],
        "calories": 620,
        "spice_level": 0,
    },
    {
        "id": "eggplant-parmesan",
        "name": "Eggplant Parmesan",
        "category": "main",
        "description": "Breaded eggplant baked with marinara and melted mozzarella.",
        "price": 15.25,
        "dietary_tags": ["vegetarian"],
        "keywords": ["eggplant", "parmesan", "main", "baked", "italian"],
        "allergens": ["gluten", "dairy", "egg"],
        "calories": 710,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Sides
    # ============================================================
    {
        "id": "sweet-potato-fries",
        "name": "Sweet Potato Fries",
        "category": "side",
        "description": "Crispy sweet potato fries with a smoky paprika dusting.",
        "price": 4.95,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["fries", "sweet potato", "side", "crispy"],
        "allergens": [],
        "calories": 380,
        "spice_level": 1,
    },
    {
        "id": "garlic-bread",
        "name": "Garlic Bread",
        "category": "side",
        "description": "Toasted baguette with garlic butter and parsley.",
        "price": 4.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["garlic", "bread", "side", "toasted"],
        "allergens": ["gluten", "dairy"],
        "calories": 330,
        "spice_level": 0,
    },
    {
        "id": "house-side-salad",
        "name": "House Side Salad",
        "category": "side",
        "description": "Mixed greens, cherry tomatoes, cucumber, and a light vinaigrette.",
        "price": 4.25,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["salad", "side", "greens", "fresh", "light"],
        "allergens": [],
        "calories": 120,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Kids
    # ============================================================
    {
        "id": "kids-mac-and-cheese",
        "name": "Kids Mac & Cheese",
        "category": "kids",
        "description": "Creamy macaroni and cheese — a kid-sized portion.",
        "price": 6.50,
        "dietary_tags": ["vegetarian"],
        "keywords": ["kids", "mac", "cheese", "macaroni", "pasta"],
        "allergens": ["gluten", "dairy"],
        "calories": 450,
        "spice_level": 0,
    },
    {
        "id": "kids-chicken-tenders",
        "name": "Kids Chicken Tenders",
        "category": "kids",
        "description": "Breaded chicken tenders with a side of fries and ketchup.",
        "price": 7.25,
        "dietary_tags": [],
        "keywords": ["kids", "chicken", "tenders", "fries"],
        "allergens": ["gluten", "egg"],
        "calories": 560,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Drinks
    # ============================================================
    {
        "id": "cappuccino",
        "name": "Cappuccino",
        "category": "drink",
        "description": "Equal parts espresso, steamed milk, and silky milk foam.",
        "price": 4.25,
        "dietary_tags": ["vegetarian"],
        "keywords": ["cappuccino", "coffee", "espresso", "milk", "hot"],
        "allergens": ["dairy"],
        "calories": 120,
        "spice_level": 0,
    },
    {
        "id": "green-tea",
        "name": "Green Tea",
        "category": "drink",
        "description": "Hot steeped Japanese sencha green tea.",
        "price": 3.25,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["tea", "green", "hot", "sencha"],
        "allergens": [],
        "calories": 0,
        "spice_level": 0,
    },
    {
        "id": "orange-juice",
        "name": "Fresh Orange Juice",
        "category": "drink",
        "description": "Freshly squeezed orange juice, served chilled.",
        "price": 4.00,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["orange", "juice", "cold", "fresh", "sweet"],
        "allergens": [],
        "calories": 160,
        "spice_level": 0,
    },

    # ============================================================
    # NEW — Desserts
    # ============================================================
    {
        "id": "new-york-cheesecake",
        "name": "New York Cheesecake",
        "category": "dessert",
        "description": "Rich baked cheesecake on a graham cracker crust with berry compote.",
        "price": 7.25,
        "dietary_tags": ["vegetarian"],
        "keywords": ["cheesecake", "dessert", "sweet", "berry", "creamy"],
        "allergens": ["gluten", "dairy", "egg"],
        "calories": 560,
        "spice_level": 0,
    },
    {
        "id": "vegan-chocolate-mousse",
        "name": "Vegan Chocolate Mousse",
        "category": "dessert",
        "description": "Silky avocado-based dark chocolate mousse topped with raspberries.",
        "price": 6.95,
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "keywords": ["chocolate", "mousse", "vegan", "dessert", "sweet"],
        "allergens": [],
        "calories": 340,
        "spice_level": 0,
    },
]
