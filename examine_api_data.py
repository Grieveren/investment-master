import json
import os
from utils.config import config

def main():
    """Examine the API data structure to identify unused fields."""
    api_data_file = config["output"]["raw_data_file"]
    
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
        print(f"Loaded API data from {api_data_file}")
    except Exception as e:
        print(f"Error loading API data: {e}")
        return
    
    # Look at the first company
    first_company_name = list(api_data.keys())[0]
    first_company = api_data[first_company_name]
    print(f"\nExamining data for: {first_company_name}")
    
    # Extract company object
    if 'data' in first_company and 'companyByExchangeAndTickerSymbol' in first_company['data']:
        company = first_company['data']['companyByExchangeAndTickerSymbol']
        
        # Print company fields
        print(f"\nCompany object fields: {list(company.keys())}")
        
        # Look at statements
        statements = company.get('statements', [])
        print(f"\nTotal statements: {len(statements)}")
        
        if statements:
            # Print fields in a statement
            print(f"Fields in a statement: {list(statements[0].keys())}")
            
            # Collect unique areas and names
            areas = set()
            names = set()
            
            for stmt in statements:
                areas.add(stmt.get('area'))
                names.add(stmt.get('name'))
            
            print(f"\nUnique statement areas ({len(areas)}):")
            for area in sorted(areas):
                print(f"  - {area}")
            
            print(f"\nSample statement names (first 20 of {len(names)}):")
            for name in sorted(list(names))[:20]:
                print(f"  - {name}")
            
            # Count statements by area
            area_counts = {}
            for stmt in statements:
                area = stmt.get('area', 'Unknown')
                area_counts[area] = area_counts.get(area, 0) + 1
            
            print("\nStatement counts by area:")
            for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {area}: {count} statements")
            
            # Print a few sample statements from each area
            print("\nSample statements by area:")
            samples_per_area = 2
            for area in sorted(areas):
                print(f"\n  Area: {area}")
                count = 0
                for stmt in statements:
                    if stmt.get('area') == area and count < samples_per_area:
                        name = stmt.get('name', 'Unknown')
                        desc = stmt.get('description', 'No description')
                        value = stmt.get('value', 'No value')
                        print(f"    - {name}: {value}")
                        print(f"      {desc[:100]}..." if len(desc) > 100 else f"      {desc}")
                        count += 1

if __name__ == "__main__":
    main() 