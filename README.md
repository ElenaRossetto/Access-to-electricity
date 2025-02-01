# Access to electricity Analysis (1960-2022)

## Overview  
This project explores global **electricity access trends** from **1960 to 2022**, focusing on key aspects such as:  
- **Disparities in electricity access** between rural and urban areas.  
- **The relationship between electricity access and GDP per capita.**  
- **The relationship between electricity access and energy imports.**  

Using interactive visualizations and data-driven analysis, the project aims to provide valuable insights into **global electrification progress and its influencing factors**.

---

## Data Sources  
The dataset includes electricity access statistics, GDP per capita, and energy imports, sourced from:
- **The World Bank Open Data** (https://databank.worldbank.org/source/world-development-indicators/)


---

All data has been **cleaned, structured, and processed** for accurate analysis.
### **Preprocessing**
1. **Handling Missing Values** 
   - Null values (`"null", "NA", "NaN", "", ".."`) are replaced with `None` for consistency.  
2. **Reshaping the Data** 🔄  
   - The dataset is **unpivoted** (long format) to make each year a separate row.  
   - It is then **pivoted back** to a wide format where each indicator becomes a column.  
3. **Renaming Columns for Clarity** 
   - Key variables are renamed:
     - `"Access to electricity (% of population)"` → `total_rate`
     - `"Access to electricity, rural (% of rural population)"` → `rural_rate`
     - `"Access to electricity, urban (% of urban population)"` → `urban_rate`
     - `"GDP per capita (constant 2015 US$)"` → `GDP`
     - `"Energy imports, net (% of energy use)"` → `energy_imports`
4. **Year Formatting**
   - The **year column is cleaned** to keep only the first four digits.  
5. **Mapping Countries to Continents**
   - Countries are mapped to continents using the **`pycountry` and `pycountry_convert`** libraries.  
   - **Special cases** (e.g., Kosovo, Timor-Leste) are manually assigned to the correct continent.  
   - **Asia & Oceania** are grouped into a **single "Asia/Oceania" category** for better analysis.  


---

## Key Research Questions  
This project investigates:
1. **How has access to electricity evolved globally from 1960 to 2022?**  
2. **What are the disparities between rural and urban electricity access?**  
3. **Is there a strong correlation between electricity access and GDP per capita?**  
4. **Does reliance on energy imports impact electricity access?**  
5. **Which regions have made the most progress in electrification?**  

---

## Technologies Used  
- **Python**  (Data analysis and visualization)
- **Polars & Pandas**  (Efficient data manipulation)
- **Altair & PyDeck**  (Interactive visualizations)
- **Streamlit** (Web-based data exploration)

---

## Features  
 **Interactive Line Charts**: Track global electricity access trends over time.  
 **Geospatial Maps**: Visualize rural-urban disparities and energy imports.  
 **Scatter Plots**: Analyze correlations between GDP, energy imports, and electricity access.  
 **Customizable Filters**: Explore data by region, year, and economic indicators.  

