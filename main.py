from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict
import logging
from datetime import datetime
import traceback

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("powerplant-api")

app = FastAPI(title="PowerPlant Production API")

# Constants
CO2_GAS_EMISSION_FACTOR = 0.3  # CO2 emission factor for gas-fired power plants
ROUNDING_PRECISION = 1  # Precision for power rounding (0.1 MW)

# Data models
class Fuels(BaseModel):
    """Model representing fuel prices and wind availability"""
    gas: float = Field(..., description="Gas price in euros/MWh")
    kerosine: float = Field(..., description="Kerosene price in euros/MWh")
    co2: float = Field(..., description="CO2 emissions price in euros/ton")
    wind: float = Field(..., ge=0, le=100, description="Available wind percentage")

class PowerPlant(BaseModel):
    """Model representing a power plant's specifications"""
    name: str
    type: str
    efficiency: float
    pmin: float
    pmax: float
    cost: float = 0.0  # Cost will be calculated dynamically

class Payload(BaseModel):
    """Model representing the API request payload"""
    load: float
    fuels: Dict[str, float]
    powerplants: List[PowerPlant]

class ResponseItem(BaseModel):
    """Model representing the response for each power plant"""
    name: str
    p: float

# Helpers
def calculate_plant_cost(plant: PowerPlant, fuels: Fuels) -> float:
    """Calculate production cost for a specific plant"""
    logger.debug(f"Calculating cost for {plant.name} - Type: {plant.type} - Efficiency: {plant.efficiency}")

    if plant.efficiency == 0:
        logger.error(f"Error: Efficiency of {plant.name} is 0, cannot divide by zero!")
        return float('inf')  # Avoid division by zero

    if plant.type == "gasfired":
        emission_factor = CO2_GAS_EMISSION_FACTOR * (1 - plant.efficiency * 0.05)
        return (fuels.gas / plant.efficiency) + (fuels.co2 * emission_factor)
    elif plant.type == "turbojet":
        return fuels.kerosine / plant.efficiency
    elif plant.type == "windturbine":
        return 0  # Wind energy has zero cost
    else:
        logger.warning(f"Unknown plant type: {plant.type}")
        return float('inf')  # Avoid using unknown types

# Dependency to validate load
def validate_load(payload: dict) -> float:
    """Validate the load value in the request payload"""
    load = payload.get("load")
    if not load or load <= 0:
        raise HTTPException(status_code=400, detail="Load must be a positive value")
    return load

@app.post("/productionplan", response_model=List[ResponseItem])
def production_plan(payload: dict, load: float = Depends(validate_load)):
    """
    Calculate the optimal production plan based on the merit order principle.
    """
    start_time = datetime.now()
    logger.info(f"Starting calculation for load: {load} MW")
    
    try:
        # Extract and standardize fuel names
        fuel_keys = {
            "gas(euro/MWh)": "gas",
            "kerosine(euro/MWh)": "kerosine",
            "co2(euro/ton)": "co2",
            "wind(%)": "wind"
        }
        
        raw_fuels = payload.get("fuels", {})
        fuels_dict = {}
        for source_key, target_key in fuel_keys.items():
            value = raw_fuels.get(source_key, raw_fuels.get(source_key.split('(')[0], None))
            if value is None:
                logger.error(f"Missing required fuel value: {source_key}")
                raise HTTPException(status_code=400, detail=f"Missing fuel value: {source_key}")
            fuels_dict[target_key] = value

        fuels_obj = Fuels(**fuels_dict)

        # Process power plants
        powerplants = [PowerPlant(**pp) for pp in payload.get("powerplants", [])]
        
        for plant in powerplants:
            plant.cost = calculate_plant_cost(plant, fuels_obj)

        # Sort power plants by cost (cheapest first)
        powerplants.sort(key=lambda x: x.cost)

        result = []
        remaining_load = load

        # Assign generation based on merit order
        for plant in powerplants:
            if plant.type == "windturbine":
                production = plant.pmax * (fuels_obj.wind / 100)
            else:
                if remaining_load < plant.pmin:
                    production = 0
                else:
                    production = min(plant.pmax, remaining_load)
                    if production > 0 and production < plant.pmin:
                        production = plant.pmin

            # Round production value
            production = round(production, ROUNDING_PRECISION)
            logger.debug(f"Assigning {production} MW to {plant.name}. Remaining load: {remaining_load} MW")
            remaining_load -= production

            # Store assigned production
            result.append({"name": plant.name, "p": production})

            # Stop if the load has been covered
            if remaining_load <= 0:
                break

        # Final adjustment: Distribute any remaining load among all available plants
        if remaining_load > 0:
            logger.warning(f"Could not fully cover the load. Trying last adjustments for missing {remaining_load:.1f} MW")

            adjustable_plants = [entry for entry in result if entry["p"] > 0]

            while remaining_load > 0.1 and adjustable_plants:
                adjustment_per_plant = remaining_load / len(adjustable_plants)

                for entry in adjustable_plants:
                    plant = next((p for p in powerplants if p.name == entry["name"]), None)
                    if plant:
                        max_adjustment = plant.pmax - entry["p"]
                        actual_adjustment = min(adjustment_per_plant, max_adjustment)

                        entry["p"] += actual_adjustment
                        remaining_load -= actual_adjustment

                        if remaining_load <= 0.1:
                            break  # Stop if enough has been assigned

                # Update the list of plants that can still receive extra load
                adjustable_plants = [entry for entry in adjustable_plants if entry["p"] < next((p.pmax for p in powerplants if p.name == entry["name"]), 0)]

        # If there's still unmet load, raise an error
        if remaining_load > 0.1:
            logger.error(f"Could not cover the load. Missing: {remaining_load} MW")
            raise HTTPException(
                status_code=400, 
                detail=f"Unable to meet load demand with available plants. Missing: {remaining_load:.1f} MW"
            )

        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Production plan calculated in {process_time:.3f} seconds")

        return result

    except Exception as e:
        logger.error(f"Error in plan calculation:\n{traceback.format_exc()}")        
        raise HTTPException(status_code=500, detail="Internal server error while calculating production plan")

# Entry point for local debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)
