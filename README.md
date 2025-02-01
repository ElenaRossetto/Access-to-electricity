# Access to electricity Analysis (1960-2022)

## Overview  
This project explores global **access to electricity** from **1960 to 2022**, focusing on key aspects such as:  
- **Disparities in electricity access** between rural and urban areas.  
- **The relationship between electricity access and GDP per capita.**  
- **The relationship between electricity access and energy imports.**  

Using interactive visualizations and data-driven analysis, the project aims to provide valuable insights into **global electrification progress and its influencing factors**.
### ***Use of DARK MODE in Streamlit is extremely suggested***
---

## Data Sources  
The dataset includes access to electricity data, energy sources, GDP per capita, energy imports, sourced from **The World Bank Open Data** (https://databank.worldbank.org/source/world-development-indicators/)


---

## Preprocessing
1. **Handling Missing Values** 
   - Null values (`"null", "NA", "NaN", "", ".."`) are replaced with `None`.  
2. **Reshaping the Data** 
   - The dataset is unpivoted (long format) to make each year a separate row.  
   - It is then pivoted back to a wide format where each indicator becomes a column.  
3. **Renaming Columns for Clarity** 
   - Variables are renamed, to make the code more clear.
4. **Mapping Countries to Continents**
   - Countries are mapped to continents using the `pycountry` and `pycountry_convert` libraries.  
   - Special cases (e.g., Kosovo, Timor-Leste) are manually assigned to the correct continent.  
   - Asia & Oceania are grouped into a single "Asia/Oceania" category for better analysis.  


---

## Key Research Questions  
This project investigates:
1. **How has access to electricity evolved globally from 1960 to 2022?**  
2. **What are the disparities between rural and urban electricity access?**  
3. **Is there a relationship between access to electricity and GDP per capita?**  
4. **Is there a relationship between access to electricity and energy imports?**  

