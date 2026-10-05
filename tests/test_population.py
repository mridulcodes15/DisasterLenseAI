from shapely.geometry import box

from src.context.population import estimate_population_exposed


# Simulated affected/change area
change_geometry = box(1, 1, 4, 4)

# Estimate exposed population
result = estimate_population_exposed(
    change_geometry,
    "data/demo/flood/population.tif",
)

print("Population exposed:", result)