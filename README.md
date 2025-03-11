# Power Plant Production Plan API

A lightweight **FastAPI-based** REST API for calculating **optimal power generation plans** based on merit order principles.

## Overview
This API solves the power plant production problem by implementing a merit order algorithm to determine the most cost-effective way to meet energy demands while considering various operational constraints.

## Features
- **Merit Order Logic**: Allocates production based on lowest marginal cost first
- **Multi-Fuel Support**: Handles various fuel types and their associated costs
- **Plant Constraints**: Respects technical limitations (`pmin`, `pmax`, efficiency)
- **Renewable Integration**: Special handling for wind turbines based on availability percentage
- **CO2 Emission Costs**: Accounts for carbon costs in the merit calculation
- **Production Rounding**: Outputs values rounded to 0.1 MW precision
- **Load Balancing**: Ensures total production precisely matches demand
- **Complete Reporting**: Includes all plants in response with their assigned output

## Installation

### Prerequisites
- Python 3.8+
- Docker (optional)

### Local Setup
1. Clone this repository
```bash
git clone https://github.com/abrokate/power-plant-api.git
cd power-plant-api
```

2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Start the server
```bash
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

The API will be available at http://localhost:8888 with automatic reload on code changes.

## Usage

### API Endpoint
- **URL**: `/productionplan`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Format
The API accepts a JSON payload with three main components:
- `load`: Total power demand in MW
- `fuels`: Current prices for different fuel types
- `powerplants`: List of available power generation units

Example request:
```json
{
  "load": 910,
  "fuels": {
    "gas(euro/MWh)": 13.4,
    "kerosine(euro/MWh)": 50.8,
    "co2(euro/ton)": 20,
    "wind(%)": 60
  },
  "powerplants": [
    { "name": "gasfiredbig1", "type": "gasfired", "efficiency": 0.53, "pmin": 100, "pmax": 460 },
    { "name": "gasfiredbig2", "type": "gasfired", "efficiency": 0.53, "pmin": 100, "pmax": 460 },
    { "name": "gasfiredsomewhatsmaller", "type": "gasfired", "efficiency": 0.37, "pmin": 40, "pmax": 210 },
    { "name": "tj1", "type": "turbojet", "efficiency": 0.3, "pmin": 0, "pmax": 16 },
    { "name": "windpark1", "type": "windturbine", "efficiency": 1, "pmin": 0, "pmax": 150 },
    { "name": "windpark2", "type": "windturbine", "efficiency": 1, "pmin": 0, "pmax": 36 }
  ]
}
```

### Response
The API returns a JSON array with the calculated production plan:

```json
[
  {"name": "windpark1", "p": 90.0},
  {"name": "windpark2", "p": 21.6},
  {"name": "gasfiredbig1", "p": 460.0},
  {"name": "gasfiredbig2", "p": 338.4},
  {"name": "gasfiredsomewhatsmaller", "p": 0.0},
  {"name": "tj1", "p": 0.0}
]
```

### Making Requests

Using cURL:
```bash
curl -X POST "http://localhost:8888/productionplan" \
     -H "Content-Type: application/json" \
     -d @example-payload.json
```

Using Python requests:
```python
import requests
import json

with open('example-payload.json') as f:
    payload = json.load(f)

response = requests.post('http://localhost:8888/productionplan', json=payload)
print(response.json())
```

## Technical Notes

### Plant Types Supported
- `gasfired`: Natural gas power plants with CO2 emission costs
- `turbojet`: Kerosine-powered turbines for peak demand
- `windturbine`: Renewable generation dependent on wind conditions

### Cost Calculation
- Gas plants: `(gas_price / efficiency) + (co2_price * emission_factor)`
- Turbojets: `kerosine_price / efficiency`
- Wind turbines: Assumed to be zero marginal cost

### Algorithm Logic
1. Calculate marginal cost for each plant
2. Sort plants by ascending cost (merit order)
3. Allocate production starting with cheapest plants
4. Handle minimum output constraints (pmin)
5. Adjust for wind availability percentage
6. Verify total production matches demand exactly

## Docker Deployment

Build the image:
```bash
docker build -t power-plant-api .
```

Run a container:
```bash
docker run -p 8888:8888 power-plant-api
```

Check it's running:
```bash
docker ps
```

For production, consider using Docker Compose for easier management:
```yaml
# docker-compose.yml
version: '3'
services:
  api:
    build: .
    ports:
      - "8888:8888"
    restart: unless-stopped
```

## Error Handling

| HTTP Status | Description | Possible Solution |
|-------------|-------------|-------------------|
| `400 Bad Request` | Invalid input format or constraints | Check payload format and values |
| `400 Bad Request` | Insufficient capacity to meet load | Reduce load or add more plants |
| `500 Internal Server Error` | Server-side processing error | Contact administrator |

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss the proposed changes.

## Notes
- This implementation is optimized for clarity rather than maximum performance
- For production use, consider adding authentication and rate limiting
- The error margin for load matching is 0.1 MW

## License
MIT License - See LICENSE file for details
