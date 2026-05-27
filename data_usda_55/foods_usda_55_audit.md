# USDA 55 Candidate Food Dataset

This is a parallel candidate dataset built from locally downloaded USDA FoodData Central CSV files.
It does not overwrite `data_v2/foods_extended.csv`.

## Scope

- 55 foods selected to preserve the experimental coverage of sodium, potassium, phosphorus, carbohydrate, fiber, added sugar, and processed-food cases.
- Source candidates are selected automatically and must be manually reviewed before manuscript-level claims.
- GI is not a USDA FDC field. GI values are carried as proxies with explicit status labels and should not be treated as USDA-sourced measurements.

## Summary

- Food rows: 55
- USDA source rows: 55
- Rows with imputed added sugar: 55
- Rows with GI proxies: 55

## Selected Candidates

| Food ID | Name | FDC ID | Dataset | USDA description | Imputed fields | GI status |
|---|---|---:|---|---|---|---|
| U001 | Brown rice | 169704 | sr_legacy | Rice, brown, long-grain, cooked (Includes foods for USDA's Food Distribution Program) | added_sugar_g | estimated_from_legacy_table |
| U002 | Oatmeal | 173905 | sr_legacy | Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt | added_sugar_g | estimated_from_legacy_table |
| U003 | Whole wheat bread | 172688 | sr_legacy | Bread, whole-wheat, commercially prepared | added_sugar_g | estimated_from_legacy_table |
| U004 | White rice | 168882 | sr_legacy | Rice, white, short-grain, enriched, cooked | fiber_g;added_sugar_g | estimated_from_legacy_table |
| U005 | Broccoli | 169967 | sr_legacy | Broccoli, cooked, boiled, drained, without salt | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U006 | Spinach | 168463 | sr_legacy | Spinach, cooked, boiled, drained, without salt | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U007 | Tomato | 170457 | sr_legacy | Tomatoes, red, ripe, raw, year round average | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U008 | Banana | 173944 | sr_legacy | Bananas, raw | added_sugar_g | estimated_from_legacy_table |
| U009 | Apple | 171688 | sr_legacy | Apples, raw, with skin (Includes foods for USDA's Food Distribution Program) | added_sugar_g | estimated_from_legacy_table |
| U010 | Chicken breast | 171140 | sr_legacy | Chicken, broiler or fryers, breast, skinless, boneless, meat only, cooked, braised | added_sugar_g | non_carbohydrate_food_proxy |
| U011 | Salmon | 172000 | sr_legacy | Fish, salmon, chum, cooked, dry heat | added_sugar_g | non_carbohydrate_food_proxy |
| U012 | Tofu | 172461 | sr_legacy | MORI-NU, Tofu, silken, firm | added_sugar_g | category_proxy_legume_soy |
| U013 | Lentils cooked | 175254 | sr_legacy | Lentils, mature seeds, cooked, boiled, with salt | added_sugar_g | estimated_from_legacy_table |
| U014 | Canned soup | 2707127 | survey | Soup, beef, canned | added_sugar_g | category_proxy_composite_processed |
| U015 | Low-fat yogurt | 170886 | sr_legacy | Yogurt, plain, low fat | added_sugar_g | estimated_from_legacy_table |
| U016 | Quinoa cooked | 168917 | sr_legacy | Quinoa, cooked | added_sugar_g | estimated_from_legacy_table |
| U017 | Whole wheat pasta | 168916 | sr_legacy | Pasta, whole grain, 51% whole wheat, remaining unenriched semolina, cooked | added_sugar_g | estimated_from_legacy_table |
| U018 | Corn | 168540 | sr_legacy | Corn, sweet, white, cooked, boiled, drained, with salt | added_sugar_g | estimated_from_legacy_table |
| U019 | Potato baked | 170112 | sr_legacy | Potatoes, baked, flesh, with salt | added_sugar_g | estimated_from_legacy_table |
| U020 | Sweet potato baked | 168483 | sr_legacy | Sweet potato, cooked, baked in skin, flesh, without salt | added_sugar_g | estimated_from_legacy_table |
| U021 | Kale | 169355 | sr_legacy | Kale, cooked, boiled, drained, with salt | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U022 | Carrot | 170393 | sr_legacy | Carrots, raw | added_sugar_g | estimated_from_legacy_table |
| U023 | Cucumber | 169225 | sr_legacy | Cucumber, peeled, raw | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U024 | Mushroom | 169251 | sr_legacy | Mushrooms, white, raw | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U025 | Romaine lettuce | 169247 | sr_legacy | Lettuce, cos or romaine, raw | added_sugar_g | category_proxy_nonstarchy_vegetable |
| U026 | Orange | 169918 | sr_legacy | Oranges, raw, Florida | added_sugar_g | estimated_from_legacy_table |
| U027 | Grapes | 2709237 | survey | Grapes, raw | added_sugar_g | estimated_from_legacy_table |
| U028 | Strawberries | 167762 | sr_legacy | Strawberries, raw | added_sugar_g | estimated_from_legacy_table |
| U029 | Avocado | 171707 | sr_legacy | Avocados, raw, Florida | added_sugar_g | category_proxy_low_carb_fruit |
| U030 | Orange juice | 169098 | sr_legacy | Orange juice, raw (Includes foods for USDA's Food Distribution Program) | added_sugar_g | estimated_from_legacy_table |
| U031 | Egg | 173423 | sr_legacy | Egg, whole, cooked, fried | added_sugar_g | non_carbohydrate_food_proxy |
| U032 | Turkey breast | 171496 | sr_legacy | Turkey, whole, breast, meat only, cooked, roasted | added_sugar_g | non_carbohydrate_food_proxy |
| U033 | Lean beef | 173114 | sr_legacy | Beef, ground, 97% lean meat / 3% fat, loaf, cooked, baked | added_sugar_g | non_carbohydrate_food_proxy |
| U034 | Pork tenderloin | 168250 | sr_legacy | Pork, fresh, loin, tenderloin, separable lean only, cooked, roasted | added_sugar_g | non_carbohydrate_food_proxy |
| U035 | Shrimp | 175180 | sr_legacy | Crustaceans, shrimp, cooked | fiber_g;added_sugar_g | non_carbohydrate_food_proxy |
| U036 | Sardines canned | 175139 | sr_legacy | Fish, sardine, Atlantic, canned in oil, drained solids with bone | added_sugar_g | non_carbohydrate_food_proxy |
| U037 | Milk low-fat | 170872 | sr_legacy | Milk, lowfat, fluid, 1% milkfat, with added vitamin A and vitamin D | added_sugar_g | estimated_from_legacy_table |
| U038 | Cheddar cheese | 170899 | sr_legacy | Cheese, cheddar, sharp, sliced | added_sugar_g | non_carbohydrate_food_proxy |
| U039 | Cottage cheese | 172182 | sr_legacy | Cheese, cottage, lowfat, 2% milkfat | added_sugar_g | category_proxy_dairy_low_carb |
| U040 | Chickpeas cooked | 173799 | sr_legacy | Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, with salt | added_sugar_g | estimated_from_legacy_table |
| U041 | Black beans cooked | 175237 | sr_legacy | Beans, black, mature seeds, cooked, boiled, with salt | added_sugar_g | estimated_from_legacy_table |
| U042 | Almonds | 2346393 | foundation | Nuts, almonds, whole, raw | energy_kcal;added_sugar_g | category_proxy_nut |
| U043 | Peanut butter | 169869 | sr_legacy | Peanut butter, reduced sodium | added_sugar_g | estimated_from_legacy_table |
| U044 | Ham | 2705878 | survey | Ham | added_sugar_g | non_carbohydrate_food_proxy |
| U045 | Ramen noodles | 2709153 | survey | Ramen bowl, NFS | added_sugar_g | estimated_from_legacy_table |
| U046 | Pepperoni pizza | 2708642 | survey | Pizza with pepperoni, stuffed crust | added_sugar_g | category_proxy_composite_processed |
| U047 | Salted crackers | 2708167 | survey | Crackers, saltine | added_sugar_g | estimated_from_legacy_table |
| U048 | Potato chips | 2709421 | survey | Potato chips, NFS | added_sugar_g | estimated_from_legacy_table |
| U049 | Soda | 173199 | sr_legacy | Carbonated beverage, cream soda | added_sugar_g | estimated_from_legacy_table |
| U050 | Cookies | 2707899 | survey | Cookie, NFS | added_sugar_g | category_proxy_sweet_baked_food |
| U051 | Chocolate cake | 2707868 | survey | Cake or cupcake, chocolate, no icing | added_sugar_g | category_proxy_sweet_baked_food |
| U052 | Sweetened cereal | 173927 | sr_legacy | Cereals ready-to-eat, MOM'S BEST, Sweetened WHEAT-FULS | added_sugar_g | category_proxy_sweetened_cereal |
| U053 | Bagel | 174899 | sr_legacy | Bagels, plain, enriched, with calcium propionate (includes onion, poppy, sesame) | added_sugar_g | estimated_from_legacy_table |
| U054 | Tuna canned in water | 175158 | sr_legacy | Fish, tuna, white, canned in water, drained solids | added_sugar_g | non_carbohydrate_food_proxy |
| U055 | Edamame | 2707436 | survey | Edamame, cooked | added_sugar_g | estimated_from_legacy_table |

## Manual Review Flags

| Food ID | Name | Note |
|---|---|---|
| U049 | Soda | Selected soda entry is cream soda. It is acceptable as sugar-sweetened soda, but not specifically cola. |
| U052 | Sweetened cereal | Selected sweetened cereal is a specific branded ready-to-eat cereal. This is acceptable for a high-sugar cereal case but should be described as a USDA candidate entry. |

## Next Checks

1. Manually inspect candidate descriptions in `food_candidate_review_usda_55.csv`.
2. Decide whether GI should remain a non-core proxy field or be supplemented from a dedicated GI source.
3. Generate a separate USDA scenario file and rerun deterministic experiments before touching manuscript tables.
