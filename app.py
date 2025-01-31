import polars as pl
import altair as alt
import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.colorbar as cbar

from matplotlib.colors import Normalize
from matplotlib.colors import TwoSlopeNorm
from matplotlib.cm import ScalarMappable

import pycountry_convert as pc
import pycountry



st.set_page_config(
    page_title="Electricity"
)

### Preprocessing
url='./WDICSV.csv'

@st.cache_data
def get_data(url):
    # Read CSV with specified null values and limit rows
    data = pl.read_csv(
        url,
        null_values=["null", "NA", "NaN", "", ".."]
    ).slice(0, 1962)

    # Unpivot the DataFrame to long format
    data = data.unpivot(
        index=["Country Name", "Country Code", "Series Name", "Series Code"],  
        variable_name="year",         
        value_name="rate"            
    )
    
    # Pivot the DataFrame to wide format
    data = data.pivot(
        index=["Country Name", "Country Code", "year"], 
        on="Series Name",                      
        values="rate"                            
    )

    # Rename columns for clarity
    data = data.rename({
        "Access to electricity (% of population)": "total_rate",
        "Access to electricity, rural (% of rural population)": "rural_rate",
        "Access to electricity, urban (% of urban population)": "urban_rate",
        "Electricity production from oil, gas and coal sources (% of total)": "oil_gas_coal",
        "Electricity production from nuclear sources (% of total)": "nuclear",
        "Electricity production from hydroelectric sources (% of total)": "hydroelectric",
        "Electricity production from renewable sources, excluding hydroelectric (% of total)": "renewable",
        "GDP per capita (constant 2015 US$)" : "GDP",
        "Energy imports, net (% of energy use)": "energy_imports"
    }).with_columns(
        pl.col("year").str.slice(0, 4).alias("year")  
    )

    # Function to create country to continent mapping
    def create_continent_mapping():
        mapping = {}
        for country in pycountry.countries:
            try:
                alpha2 = country.alpha_2
                continent_code = pc.country_alpha2_to_continent_code(alpha2)
                continent_name = pc.convert_continent_code_to_continent_name(continent_code)
                mapping[country.alpha_3] = continent_name
            except:
                mapping[country.alpha_3] = None
        return mapping
        
    # Create the continent mapping
    continent_mapping = create_continent_mapping()

    # Create a DataFrame for mapping continents
    mapping_df = pl.DataFrame({
        "Country Code": list(continent_mapping.keys()),
        "Continent": list(continent_mapping.values())})

    # Join the mapping with the main data
    data = data.join(mapping_df, on="Country Code", how="left")

    # Manually assign continents to specific countries
    data = data.with_columns(
        pl.when(pl.col("Country Name") == "Timor-Leste").then(pl.lit("Asia"))
        .when(pl.col("Country Name") == "Channel Islands").then(pl.lit("Europe"))
        .when(pl.col("Country Name") == "Kosovo").then(pl.lit("Europe"))
        .when(pl.col("Country Name") == "Sint Maarten (Dutch part)").then(pl.lit("North America"))
        .when(pl.col("Country Name") == "World").then(pl.lit("World"))
        .otherwise(pl.col("Continent"))
        .alias("Continent")
    )

    # Combine Asia and Oceania into Asia/Oceania
    data = data.with_columns(
        pl.when(pl.col("Continent").is_in(["Asia", "Oceania"])).then(pl.lit("Asia/Oceania"))
          .otherwise(pl.col("Continent"))
          .alias("Continent")
    )

    return data

data=get_data(url)


# Introduction
variable_descriptions = [
    {"Variable": "Country Name", "Description": "Country Name", "Example": "Kenya"},
    {"Variable": "Country Code", "Description": "Country Code (3 letters)", "Example": "KEN"},
    {"Variable": "year", "Description": "Year (from 1960 to 2023)", "Example": "2000"},
    {"Variable": "total_rate", "Description": "Percentage of population with access to electricity", "Example": "15.2"},
    {"Variable": "rural_rate", "Description": "Percentage of rural population with access to electricity", "Example": "6.6"},
    {"Variable": "urban_rate", "Description": "Percentage of urban population with access to electricity", "Example": "49.9"},
    #{"Variable": "oil_gas_coal", "Description": "Electricity production from oil (refers to crude oil and petroleum products), gas (refers to natural gas but excludes natural gas liquids), coal (refers to all coal and brown coal) Peat is also included in this cathegory  (% of total)", "Example": "12.48"},
    #{"Variable": "nuclear", "Description": "Electricity production from nuclear power (% of total)", "Example": "0"},
    #{"Variable": "renewable", "Description": "Electricity production from renewable sources, excluding hydroelectric, includes geothermal, solar, tides, wind, biomass, and biofuels  (% of total)", "Example": "48.27"},
    #{"Variable": "hydroelectric", "Description": "Electricity production from hydroelectric power plants (% of total)", "Example": "39.24"},
    {"Variable": "energy_imports", "Description": "Net energy imports are estimated as energy use less production, both measured in oil equivalents. A negative value indicates that the country is a net exporter. Energy use refers to use of primary energy before transformation to other end-use fuels, which is equal to indigenous production plus imports and stock changes, minus exports and fuels supplied to ships and aircraft engaged in international transport", "Example":"18.35"},
    {"Variable": "GDP", "Description": "GDP per capita is gross domestic product divided by midyear population. GDP is the sum of gross value added by all resident producers in the economy plus any product taxes and minus any subsidies not included in the value of the products. It is calculated without making deductions for depreciation of fabricated assets or for depletion and degradation of natural resources. Data are in constant 2015 U.S. dollars.", "Example": "1195.41"},
    {"Variable": "Continent", "Description": "Continent the country belongs", "Example": "Africa"}
    ]
variable_table = pd.DataFrame(variable_descriptions)




# Access to electricity
def linechart_world():
    # Slider to select year range
    year_range = st.slider(
        "Select years:",
        min_value=1998,
        max_value=2022,
        value=(1998, 2022)
    )

    # Filter data for World and selected years
    world_data=data.filter(
        (pl.col("Country Code")=="WLD") &
        (pl.col("year").cast(int).is_between(year_range[0], year_range[1]))
    )

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["year"],  # Field to trigger selection
        nearest=True,     # Select nearest point
        on="mouseover",   # Trigger on mouseover
        empty="none"      # No selection by default
    )

    # Line chart for total_rate over years
    line = alt.Chart(world_data).mark_line().encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("total_rate:Q", title="Access to Electricity (%)", scale=alt.Scale(zero=False)),
    )

    # Adding points on the line with tooltips
    points = alt.Chart(world_data).mark_point(size=50, filled=True).encode(
        x=alt.X("year:O"),
        y=alt.Y("total_rate:Q"),
        size=alt.condition(
            highlight,
            alt.value(200),  # size for selected points
            alt.value(50)    # Size for normal points
        ),
        tooltip=[
            alt.Tooltip("year:N", title="Year"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f")  # Arrotonda a 2 decimali
        ]
    ).add_params(
        highlight
    )

    # Combine line and points
    chart = (line + points).properties(
        width=800,
        height=400
    )

    # Display the chart in Streamlit
    st.altair_chart(chart, use_container_width=True)


@st.cache_data
def load_geojson():
    geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    response = requests.get(geojson_url)
    geojson = response.json()
    return geojson

def merge_data_access(data, geojson):
    # Create a dictionary associating Country Code to total_rate 
    data_dict = data.set_index('Country Code')['total_rate'].to_dict()

    # Add 'total_rate' to each GeoJSON feature
    for feature in geojson['features']:
        country_code = feature['id']
        total_rate = data_dict.get(country_code, None)
        if pd.notnull(total_rate):  
            feature["properties"]["total_rate"] = round(float(total_rate), 2) 
        else:
            feature["properties"]["total_rate"] = None
    return geojson

def assign_color(geojson, min_rate, max_rate, colormap_name, variable, missing_color=[105, 105, 105]):
    # Get the colormap from matplotlib
    colormap = matplotlib.colormaps.get_cmap(colormap_name)
    
    # Normalize the rate values
    normalize = mcolors.Normalize(vmin=min_rate, vmax=max_rate)

    # Iterate over each feature in the GeoJSON
    for feature in geojson["features"]:
        rate = feature["properties"].get(variable)
        if rate is None or pd.isnull(rate):  
            feature["properties"]["fill_color"] = missing_color   # Assign missing color
        else:
            # Get the color from the colormap
            color = colormap(normalize(rate))  # [R, G, B, A]
            feature["properties"]["fill_color"] = [int(255 * c) for c in color[:3]]  # Convert to RGB
    return geojson 

def create_legend(colormap_name, min_rate, max_rate, text, missing_color=[105, 105, 105]):
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(0.7, 4))
    fig.subplots_adjust(left=0.5, right=0.8, top=0.9, bottom=0.1)

    # Set transparent background
    fig.patch.set_facecolor('none')  
    ax.set_facecolor('none')       
    # Add descriptive text
    ax.text(0, 110, text, fontsize=10, color='white', va='center')

    # Get the colormap
    colormap = matplotlib.colormaps.get_cmap(colormap_name)

    # Normalize the rate values
    norm = Normalize(vmin=min_rate, vmax=max_rate)

    # Create the colorbar
    cbar_instance = cbar.ColorbarBase(
        ax,
        cmap=colormap,
        norm=norm,
        orientation='vertical'
    )

    # White ticks
    cbar_instance.ax.tick_params(colors='white')   

    # Add legend for missing data
    ax_missing = fig.add_axes([0.5, 0.005, 0.3, 0.05])  
    ax_missing.set_xticks([])
    ax_missing.set_yticks([])
    ax_missing.set_xlim(0, 1)
    ax_missing.set_ylim(0, 1)
    ax_missing.add_patch(plt.Rectangle((0, 0), 1, 1, color=[c / 255 for c in missing_color]))
        
    ax_text = fig.add_axes([0.9, 0.005, 0.3, 0.05])  
    ax_text.set_xticks([])
    ax_text.set_yticks([])
    ax_text.set_xlim(0, 1)
    ax_text.set_ylim(0, 1)
    ax_text.text(0, 0.5, "No Data", fontsize=10, color='white', va='center')
    ax_text.set_facecolor('black') 
    
    return fig

def map_access():
    # Load GeoJSON data
    geojson = load_geojson()

    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2015,
        value=2000,
    )
    
    # Filter data for the selected year 
    filtered_data = (
        data.filter(pl.col("year") == str(selected_year))
            .select(["Country Name", "Country Code", "total_rate"])
            .drop_nulls(["total_rate"])
    )

    # Merge filtered data with GeoJSON data
    merged_geojson = merge_data_access(filtered_data.to_pandas(), geojson)

    min_rate = 0
    max_rate = 100

    # Assign colors
    merged_geojson = assign_color(merged_geojson, min_rate, max_rate, variable="total_rate", colormap_name="Reds")

    # Create a GeoJSON layer for the map
    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=merged_geojson,
        pickable=True,
        filled=True,
        stroked=True,
        get_fill_color="properties.fill_color",  
        get_line_color=[0, 0, 0],
        line_width_min_pixels=1
    )

    # Set the initial view of the map
    view_state = pdk.ViewState(
        latitude=35,
        longitude=15,
        zoom=0.4,
        pitch=0
    )

    # Set tooltip
    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>Country:</b> {name}<br/><b>Access (%): </b> {total_rate}",
            "style": {"color": "white"},
        },
    )

    # Create two columns
    col1, col2 = st.columns([7, 1])  
    with col1:
        # Display the map
        st.pydeck_chart(deck)
    with col2:
        # Display the legend
        fig = create_legend('Reds', min_rate, max_rate, text="Access to \nelectricity (%)")
        st.pyplot(fig)


def linechart_countries():
    # Filter countries with at least one value for total_rate
    countries = sorted(data.filter(
        pl.col("total_rate").is_not_null()
        ).select("Country Name").unique().to_series().to_list())
 
    # Select countries
    selected_countries = st.multiselect(
        "Select one or more countries (max 5):",
        countries,
        default=["Italy", "China", "Algeria", "Argentina", "Indonesia"],   
        max_selections=5,
        key="selected_countries",
    )
    
    # Select the year range
    year_range = st.slider(
        "Select years:",
        min_value=1990,
        max_value=2022,
        value=(1990, 2022)
    )
   
    # Filter data for the selected countries and year range
    filtered_data = data.filter(
        (pl.col("Country Name").is_in(selected_countries)) &
        (pl.col("year").cast(int).is_between(year_range[0], year_range[1]))
    )

    if len(filtered_data) == 0:
        st.warning("Select at least one country with available data")
        return

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["year"],  # Field to trigger selection
        nearest=True,     # Select nearest point
        on="mouseover",   # Trigger on mouseover
        empty="none"      # No selection by default
    )

    # Line chart for total_rate for the selected countries
    line = alt.Chart(filtered_data).mark_line().encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("total_rate:Q", title="Access to electricity (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("Country Name:N", title="Country")
    )

    # Adding points on the line with tooltips
    points = alt.Chart(filtered_data).mark_point(size=50, filled=True).encode(
        x=alt.X("year:O"),
        y=alt.Y("total_rate:Q"),
        color=alt.Color("Country Name:N"),
        size=alt.condition(
            highlight,
            alt.value(200),  # size for selected points
            alt.value(50)    # Size for normal points
        ),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("year:N", title="Year"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f")  # Arrotonda a 2 decimali
        ]
    ).add_params(
        highlight 
    )

    # Combine line and points
    chart = (line + points).properties(
        width=800,
        height=400
    )

    # Display the chart in Streamlit
    st.altair_chart(chart, use_container_width=True)



# Access to electricity in urban and rural areas
def scatterplot_urban_rural():
    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2022,
        value=2015,
    )

    # Filter data for selected year, remove World and null values
    filtered_data = data.filter(
        (pl.col("year") == str(selected_year)) &  
        (pl.col("urban_rate").is_not_null()) &
        (pl.col("Country Name")!="World")
    ).select(["Country Name", "Continent","urban_rate", "rural_rate"])

    if filtered_data.is_empty():
        st.warning("Nessun dato disponibile per l'anno selezionato.")
        return
    
    # Filter countries with at least one value for urban rate
    countries = sorted(data.filter(
        pl.col("urban_rate").is_not_null()
        ).select("Country Name").unique().to_series().to_list())

    # Select a country
    selected_country = st.selectbox(
        "Search for one country: ",
        countries,
        index=countries.index("Kenya")
    )

    # Split data for selected country and other countries
    selected_country_data = filtered_data.filter(pl.col("Country Name") == selected_country)
    other_countries_data = filtered_data.filter(pl.col("Country Name") != selected_country)

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["Country Name"],  # Field to trigger selection
        nearest=True,     # Select nearest point
        on="mouseover",   # Trigger on mouseover
        empty="none"      # No selection by default
    )

    # Color map for continents
    color_map = {
        'Europe': 'red',         
        'North America': '#1f78b4',   
        'South America': '#a6cee3',   
        'Asia/Oceania': '#33a02c',    
        'Africa': '#fb9a99'          
    }

    # Base chart for other countries
    base_chart = alt.Chart(other_countries_data.to_pandas()).mark_point(size=100, filled=True).encode(
        x=alt.X("rural_rate:Q", title="Access to Electricity in rural areas (%)", scale=alt.Scale(zero=False)),
        y=alt.Y("urban_rate:Q", title="Access to Electricity in urban areas (%)", scale=alt.Scale(zero=False)),
        color=alt.Color(
            "Continent:N",
            title="Continent",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values())
            )
        ),
        size=alt.condition(
            highlight,  
            alt.value(250),  # size for selected points
            alt.value(50)    # Size for normal points
        ),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("urban_rate:Q", title="Access in urban areas (%)", format=".2f"),
            alt.Tooltip("rural_rate:Q", title="Access in rural areas (%)", format=".2f")
        ],
    ).add_params(
        highlight  
    )

    # Chart for selected country
    selected_chart = alt.Chart(selected_country_data.to_pandas()).mark_point(size=100, filled=True).encode(
        x=alt.X("rural_rate:Q", title="Access to Electricity in rural areas (%)", scale=alt.Scale(zero=False)),
        y=alt.Y("urban_rate:Q", title="Access to Electricity in urban areas (%)", scale=alt.Scale(zero=False)),
        color=alt.Color(
            "Continent:N",
            title="Continent",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values())
            )
        ),
        size=alt.value(600),   # bigger size for the selected country
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("urban_rate:Q", title="Access in urban areas (%)", format=".2f"),
            alt.Tooltip("rural_rate:Q", title="Access in rural areas (%)", format=".2f")
        ],
    ).add_params(
        highlight 
    )

    # Combine the base chart and chart for the selected country
    chart = alt.layer(base_chart, selected_chart).configure_view(strokeWidth=0
              ).properties(
                width=800,
                height=600
    )

    # Display the chart in Streamlit    
    st.altair_chart(chart, use_container_width=True)


def merge_data_disparity(data, geojson):
    # Create a dictionary mapping Country Code to a sub-dictionary with the variables disparity, urban_rate, rural_rate
    data_dict = data.set_index('Country Code')[['disparity', "urban_rate", "rural_rate"]].to_dict(orient='index')

    # Iterate over each country in the GeoJSON
    for feature in geojson['features']:
        country_code = feature['id']
        country_data = data_dict.get(country_code, None) # Get data for the country if available
        if country_data:
            # Extract values for disparity, urban_rate, and rural_rate
            disparity=country_data.get("disparity", None)
            urban_rate=country_data.get("urban_rate", None)
            rural_rate=country_data.get("rural_rate", None)
            # Check if disparity is not null before assigning values
            if pd.notnull(disparity):  
                feature["properties"]["disparity"] = round(float(disparity), 2) 
                feature["properties"]["urban_rate"] = round(float(urban_rate), 2)
                feature["properties"]["rural_rate"] = round(float(rural_rate), 2)
            else:
                # Assign None if data is missing
                feature["properties"]["disparity"] = None
                feature["properties"]["urban_rate"] = None
                feature["properties"]["rural_rate"] = None
    return geojson

def map_disparity():
    # Load GeoJSON data
    geojson = load_geojson()

    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2022,
        value=2000,
    )

    # Compute disparity values
    disparity=pl.col("urban_rate")-pl.col("rural_rate")

    # Filter data for the selected year
    filtered_data = (
        data.filter(pl.col("year") == str(selected_year))
            .select(["Country Name", "Country Code", "urban_rate", "rural_rate", disparity.alias("disparity")])
            )
    
    # Merge filtered data with GeoJSON data
    merged_geojson = merge_data_disparity(filtered_data.to_pandas(), geojson)

    min_rate = 0
    max_rate = 100

    # Assign colors
    merged_geojson = assign_color(merged_geojson, min_rate, max_rate, colormap_name="Blues", variable="disparity")

    # Create a GeoJSON layer for the map
    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=merged_geojson,
        pickable=True,
        filled=True,
        stroked=True,
        get_fill_color="properties.fill_color",  
        get_line_color=[0, 0, 0],
        line_width_min_pixels=1
    )

    # Set the initial view of the map
    view_state = pdk.ViewState(
        latitude=35,
        longitude=15,
        zoom=0.4,
        pitch=0
    )

    # Set tooltip
    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>Country:</b> {name}<br/><b>Disparity: </b> {disparity}<br/><b>Access in urban areas (%): </b> {urban_rate}<br/><b>Access in rural areas (%): </b> {rural_rate}",
            "style": {"color": "white"},
        },
    )

    # Create two columns
    col1, col2 = st.columns([7, 1])  
    with col1:
        # Display the map
        st.pydeck_chart(deck)
    with col2:
        # Display the legend
        fig = create_legend('Blues', min_rate, max_rate, text="Disparity (%)")
        st.pyplot(fig)



# Access to electricity vs GPD
def linechart_access_gdp():
    # Slider to select year range
    year_range = st.slider(
        "Select years:",
        min_value=1990,
        max_value=2022,
        value=(1990, 2022)  
    )

    # Filter countries with available GDP and total_rate
    countries = sorted(data.filter(
        (pl.col("GDP").is_not_null()) &  
        (pl.col("total_rate").is_not_null())
    ).select("Country Name").unique().to_series().to_list())

    # Select one country
    country = st.selectbox(
        "Select one country: ",
        countries,
        index=countries.index("Kenya")
    )

    # Filter data for selected country and selected year range
    filtered_data = data.filter(
        (pl.col("Country Name") == country) &
        (pl.col("year").cast(int).is_between(year_range[0], year_range[1]))
    ).select(
        pl.col("GDP", "year", "total_rate")
    )

    # Converti i dati filtrati in Pandas per Altair e aggiungi un campo "series"
    filtered_data = filtered_data.to_pandas()
    total_rate_data = filtered_data.assign(series="Total Rate")
    gdp_data = filtered_data.assign(series="GDP")

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["year", "series"],  # Field to trigger selection
        on="mouseover",
        empty="none"
    )

    # Line chart for total_rate 
    line_a = alt.Chart(total_rate_data).mark_line().encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y(
            "total_rate:Q",
            title="Access to electricity (%)",
            scale=alt.Scale(domain=[0, 100], zero=True),
            axis=alt.Axis(titleColor="Red", titleFontSize=20)  # Titolo rosso
        ),
        color=alt.value("red")
    )

    # Add points for total_rate
    points_a = alt.Chart(total_rate_data).mark_point(size=50, filled=True).encode(
        x=alt.X("year:O"),
        y=alt.Y("total_rate:Q"),
        color=alt.value("red"),
        size=alt.condition(
            highlight,
            alt.value(300),  
            alt.value(50)
        ),
        tooltip=[
            alt.Tooltip("year:N", title="Year"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f")
        ]
    ).add_params(
        highlight
    )

    # Combine line and points for total_rate
    chart_a = (line_a + points_a).properties(
        width=800,
        height=450
    )

    # Line chart for GDP
    line_b = alt.Chart(gdp_data).mark_line().encode(
        x=alt.X("year:O"),
        y=alt.Y(
            "GDP:Q",
            title="GDP",
            scale=alt.Scale(zero=False),
            axis=alt.Axis(titleColor="blue", titleFontSize=20)  
        ),
        color=alt.value("blue")
    )

    # Add points for GDP
    points_b = alt.Chart(gdp_data).mark_point(size=50, filled=True).encode(
        x=alt.X("year:O"),
        y=alt.Y("GDP:Q"),
        color=alt.value("blue"),
        size=alt.condition(
            highlight,
            alt.value(200),  
            alt.value(50)   
        ),
        tooltip=[
            alt.Tooltip("year:N", title="Year"),
            alt.Tooltip("GDP:Q", title="GDP", format=".2f")
        ]
    ).add_params(
        highlight
    )

    # Combine line and points for GDP
    chart_b = (line_b + points_b).properties(
        width=800,
        height=450
    )

    # Combine the two graphs with independend y-axes
    chart = alt.layer(
        chart_b,
        chart_a
    ).resolve_scale(
        y="independent"
    )

    # Display the chart in Streamlit
    st.altair_chart(chart, use_container_width=True)

def scatterplot_access_gdp():
    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2022,
        value=2000,
        key="scatterplot_slider"
    )

    # List of continents
    continents = ["Africa", "Asia/Oceania", "Europe", "North America", "South America"]
    
    # Select continents
    selected_continents = st.multiselect(
        "Select one or more continents (max 3):",
        continents,
        default= ["Africa"],    
        max_selections=3,
        key="selected_continents",
    )

    if not selected_continents:
        st.warning("Select at least one continent")
        return

    # Filter data for selected year and continents
    filtered_data = data.filter(
        (pl.col("year") == str(selected_year)) & 
        (pl.col("total_rate").is_not_null()) &
        (pl.col("GDP").is_not_null()) &
        (pl.col("Country Name")!="World") &
        (pl.col("Continent").is_in(selected_continents))
    ).select(["Country Name", "total_rate", "Continent", "GDP"])

    if filtered_data.is_empty():
        st.warning("Nessun dato disponibile per l'anno selezionato.")
        return
    
    # Color map for continents
    color_map = {
        'Europe': 'red',         
        'North America': '#1f78b4',   
        'South America': '#a6cee3',   
        'Asia/Oceania': '#33a02c',    
        'Africa': '#fb9a99' 
    }

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["Country Name"],  
        nearest=True,     
        on="mouseover",   
        empty="none"      
    )

    # Chart scatterplot comparing total_rate and GDP
    chart = alt.Chart(filtered_data.to_pandas()).mark_point(size=100, filled=True).encode(
        x=alt.X("GDP:Q", title="GDP"),
        y=alt.Y("total_rate:Q", title="Access to Electricity (%)"),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f"),
            alt.Tooltip("GDP:Q", title="GDP", format=".2f"),
        ],
        color=alt.Color(
            "Continent:N",
            title="Continent",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values())
            )
        ),
        size=alt.condition(
            highlight,  
            alt.value(250),  
            alt.value(50)   
        )).add_params(
            highlight 
    ).properties(
        width=800,
        height=600
    )

    # Display the chart in Streamlit    
    st.altair_chart(chart, use_container_width=True)



# Access to electricity vs energy imports
def merge_data_imports(data, geojson):
    # Create a dictionary mapping Country Code to energy_imports
    data_dict = data.set_index('Country Code')['energy_imports'].to_dict()

    # Iterate over each country in the GeoJSON
    for feature in geojson['features']:
        country_code = feature['id']
        energy_imports = data_dict.get(country_code, None) # Get energy imports value for the country
        if pd.notnull(energy_imports):  
            #Assign energy_imports value
            feature["properties"]["energy_imports"] = round(float(energy_imports), 2) 
        else:
            # Assing None if data is missing
            feature["properties"]["energy_imports"] = None
    return geojson

def assign_color_imports(geojson, min_rate, max_rate, colormap_name='RdBu', missing_color=[105, 105, 105]):
    # Normalize values using TwoSlopeNorm, setting vcenter at 0 for diverging colormap
    norm = TwoSlopeNorm(vmin=min_rate, vcenter=0, vmax=max_rate)
    
    # Get the colormap from matplotlib
    colormap = matplotlib.colormaps.get_cmap(colormap_name)
    
    # Iterate over each country in the GeoJSON
    for feature in geojson["features"]:
        rate = feature["properties"].get("energy_imports", None) # Get energy import rate
        if rate is None or pd.isnull(rate):
            feature["properties"]["fill_color"] = missing_color  # Missing values
        else:
            # Normalize the value using TwoSlopeNorm
            norm_rate = norm(rate)
            # Get the corresponding color from the colormap
            color = colormap(norm_rate)  # Returns [R, G, B, A]
            # Convert RGB values from range [0,1] to [0,255]
            feature["properties"]["fill_color"] = [int(255 * c) for c in color[:3]]
    return geojson

@st.cache_data
def create_legend_imports(colormap_name, min_rate, max_rate, missing_color=[105, 105, 105]):
    # Crea una figura e un asse
    fig, ax = plt.subplots(figsize=(4, 60))  # Figura verticale stretta
    fig.patch.set_facecolor('none')  
    ax.set_facecolor('none')      
    # Definisci la normalizzazione con TwoSlopeNorm centrata a 0
    norm = mcolors.TwoSlopeNorm(vmin=min_rate, vcenter=0, vmax=max_rate)

    # Ottieni la colormap desiderata
    cmap = plt.get_cmap(colormap_name)

    # Crea un oggetto ScalarMappable per la colorbar
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])  # Necessario per alcuni backend di Matplotlib

    # Crea la colorbar all'interno dell'asse
    cbar = fig.colorbar(sm, cax=ax, orientation='vertical')

    # Definisci i valori dei tick, assicurandoti che zero sia incluso
    tick_values = np.linspace(min_rate, max_rate, num=6)
    if 0 not in tick_values:
        tick_values = np.unique(np.append(tick_values, 0))
    
    # Imposta i tick e le etichette dei tick
    cbar.set_ticks(tick_values)
    cbar.set_ticklabels([f"{v:.2f}" for v in tick_values])

    # Imposta l'etichetta della colorbar
    cbar.ax.text(0.5, 1.05, "Energy \n Imports (%)",
                    transform=cbar.ax.transAxes,
                    ha='center', va='bottom',
                    color='white', fontsize=150)
    # Personalizza l'aspetto dei tick
    cbar.ax.tick_params(colors='white', labelsize=120)

    # Imposta il colore del bordo della colorbar
    cbar.outline.set_edgecolor('white')  # Colore del bordo della colorbar
    cbar.ax.yaxis.set_tick_params(color='white')  # Colore delle linee dei tick

    ax_inset = fig.add_axes([0.15, 0.01, 0.8, 0.05], facecolor='black')  # [left, bottom, width, height]
    ax_inset.imshow([[missing_color]], aspect='auto')
    ax_inset.axis('off')
    ax_inset.text(0.8, 0.05, 'Missing', va='center', fontsize=120, color='white')
    
    return fig

def map_imports():
    # Load GeoJSON data
    geojson = load_geojson()

    # Filtering data for the year range (1990, 2014)
    year_range_data = (
            data.filter(pl.col("year").cast(pl.Int32).is_between(1990, 2014, closed="both"))
        )

    # Comunting min and max rate in the year range (1990, 2014)
    min_rate = year_range_data.select(pl.col("energy_imports")).min().to_numpy()[0]
    max_rate = year_range_data.select(pl.col("energy_imports")).max().to_numpy()[0]
    
    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2014,
        value=2000,
    )

    # Filter data for the selected year
    filtered_data = (
        data.filter(pl.col("year") == str(selected_year))
            .select(["Country Name", "Country Code", "energy_imports"])
            .drop_nulls(["energy_imports"])
    )

    if filtered_data.is_empty():
        st.warning("No available data for the selected year")
        return

    # Merge filtered data with GeoJSON data
    merged_geojson = merge_data_imports(filtered_data.to_pandas(), geojson)
    
    # Assign colors
    merged_geojson = assign_color_imports(merged_geojson, min_rate, max_rate)

    # Create a GeoJSON layer for the map
    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=merged_geojson,
        pickable=True,
        filled=True,
        stroked=True,
        get_fill_color="properties.fill_color",  
        get_line_color=[0, 0, 0],
        line_width_min_pixels=1
    )

    # Set the initial view of the map
    view_state = pdk.ViewState(
        latitude=35,
        longitude=15,
        zoom=0.4,
        pitch=0
    )

    # Set tooltip
    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>Country:</b> {name}<br/><b>Energy imports (%): </b> {energy_imports}",
            "style": {"color": "white"},
        },
    )

    # Create two columns
    col1, col2 = st.columns([7, 1])  
    with col1:
        # Display the map
        st.pydeck_chart(deck)
    with col2:
        # Display the legend
        fig = create_legend_imports('RdBu', min_rate, max_rate)  # Passa num_ticks
        st.pyplot(fig)
    

def scatterplot_access_imports():
    # Compute min energy imports overall
    @st.cache_data
    def compute_min_energy_imports():
        return data.filter(
                (pl.col("year").cast(int).is_between(1990, 2014)) & 
                (pl.col("total_rate").is_not_null()) &
                (pl.col("energy_imports").is_not_null()) &
                (pl.col("Country Name")!="World") 
            ).select("energy_imports").to_series().min()
    min_energy_imports = compute_min_energy_imports()

    # Slider to select the year
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2014,
        value=2000, 
        key="scatterplot_slider"
    )

    # List of continents
    continents = ["Africa", "Asia/Oceania", "Europe", "North America", "South America"]
    
    # Select continents
    selected_continents = st.multiselect(
        "Select one continent:",
        continents,
        default="Africa",
        key="selected_continents",
    )

    if not selected_continents:
        st.warning("Select one continent")
        return

    

    # Filter data for selected year and continents
    filtered_data = data.filter(
        (pl.col("year") == str(selected_year)) & 
        (pl.col("total_rate").is_not_null()) &
        (pl.col("energy_imports").is_not_null()) &
        (pl.col("Country Name")!="World") &
        (pl.col("Continent").is_in(selected_continents))
    ).select(["Country Name", "total_rate", "Continent", "energy_imports"])

    if filtered_data.is_empty():
        st.warning("Nessun dato disponibile per l'anno selezionato.")
        return
    
    # Color map for continents
    color_map = {
        'Europe': 'red',         
        'North America': '#1f78b4',   
        'South America': '#a6cee3',   
        'Asia/Oceania': '#33a02c',    
        'Africa': '#fb9a99' 
    }

    # Selection for highlighting points
    highlight = alt.selection_point(
        fields=["Country Name"],  
        nearest=True,     
        on="mouseover",   
        empty="none"      
    )

    # Chart scatterplot comparing total_rate and energy imports
    chart = alt.Chart(filtered_data.to_pandas()).mark_point(size=100, filled=True).encode(
        x=alt.X("energy_imports:Q", title="Energy imports (%)", scale=alt.Scale(domain=(min_energy_imports, 100))), 
        y=alt.Y("total_rate:Q", title="Access to Electricity (%)", scale=alt.Scale(domain=(1,100))),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f"),
            alt.Tooltip("energy_imports:Q", title="Energy imports (%)", format=".2f"),
        ],
        color=alt.Color(
            "Continent:N",
            title="Continent",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values())
            )
        ),
        size=alt.condition(
            highlight,  
            alt.value(250),  
            alt.value(50) 
        )).add_params(
            highlight 
    ).properties(
        width=800,
        height=600
    )

    # Display the chart in Streamlit    
    st.altair_chart(chart, use_container_width=True)




# Energy sources
def energy_trend_chart():
    year_range = st.slider(
        "Select years:",
        min_value=1971,
        max_value=2015,
        value=(1971, 2015)  # Valore iniziale: tutto il range
    )
    world_data = data.filter(
        (pl.col("Country Name") == "World")& 
        (pl.col("year").cast(int).is_between(year_range[0], year_range[1]))

    ).select(["year", "oil_gas_coal", "nuclear", "hydroelectric", "renewable"])

    world_data_long = world_data.unpivot(
        index="year",  # Colonna che rimane invariata
        variable_name="Energy Source",  # Nuova colonna per le fonti di energia
        value_name="Percentage"  # Nuova colonna per i valori
    )


    highlight = alt.selection_point(
        fields=["year", "Energy Source"],  # Campo su cui attivare la selezione
        nearest=True,     # Seleziona il punto più vicino
        on="mouseover",   # Attivazione al passaggio del mouse
        empty="none"      # Non selezionare niente di default
    )

    line = alt.Chart(world_data_long).mark_line().encode(
        x=alt.X("year:O", title="Year", scale=alt.Scale(zero=False)),
        y=alt.Y("Percentage:Q", title="Energy production (%)"),
        color=alt.Color("Energy Source:N", title="Energy Source")
    )

    points = alt.Chart(world_data_long).mark_point(size=50, filled=True).encode(
        x=alt.X("year:O"),
        y=alt.Y("Percentage:Q"),
        color=alt.Color("Energy Source:N",scale=alt.Scale(domain=["oil_gas_coal", "nuclear", "hydroelectric", "renewable"])),
        size=alt.condition(
            highlight,  # Se è selezionato
            alt.value(200),  # Dimensione del punto selezionato
            alt.value(50)    # Dimensione dei punti normali
        ),
        tooltip=[
            alt.Tooltip("Energy Source:N", title="Energy Source"),
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("Percentage:Q", title="Energy production (%)", format=".2f")
        ]
    ).add_params(
        highlight  # Aggiungi la selezione
    )


    chart = (line + points).properties(
        width=800,
        height=400
    )

    # Mostra il grafico con Streamlit
    st.altair_chart(chart, use_container_width=True)

def circle_chart():
    # Elenco di paesi basato sui dati
    countries = data.select("Country Name").unique().to_series().to_list()
    countries = sorted(countries)

    # Dropdown per selezionare un paese
    country = st.selectbox(
        "Select one country: ",
        countries,
        index=countries.index("Kenya")
    )

    year = st.slider("Select the year: ", min_value=1960, max_value=2015, value=1990, key="circle_chart_year_slider" )

    filtered_data=data.filter(
        (pl.col("Country Name")==country) &
        (pl.col("year")==str(year))
    ).select(["oil_gas_coal", "nuclear", "hydroelectric", "renewable"])

    filtered_data_long = filtered_data.unpivot(
        
        variable_name="Energy Source",  # Nuova colonna per le fonti di energia
        value_name="Percentage"  # Nuova colonna per i valori
    ).filter(
        ~pl.col("Percentage").is_null()  # Rimuove le righe con valori nulli
    )

    # Verifica se ci sono dati dopo aver rimosso i nulls
    if filtered_data_long.height == 0:
        st.warning(f"No data available for {country} in {year}.")
        return


    chart = (
        alt.Chart(filtered_data_long)   
        .mark_arc(radius=80, radius2=130, cornerRadius=10)  
        .encode(
            theta=alt.Theta("Percentage:Q"),  # aggregate='sum' per fare in modo venga fuori tutto unito, e non le varie linee che separano gli stati
            color=alt.Color("Energy Source:N",scale=alt.Scale(domain=["oil_gas_coal", "nuclear", "hydroelectric", "renewable"])),
            tooltip=[
                alt.Tooltip("Energy Source"),
                alt.Tooltip("Percentage:Q", format=".2f")                
            ]
        )
    )

    text=(
        alt.Chart(filtered_data_long)
            .mark_text(radius=160, radius2=150, cornerRadius=100, size=20).encode(
                theta=alt.Theta("Percentage:Q", stack=True),
                text=alt.Text("Percentage:Q", format=".2f"),
                color=alt.Color("Energy Source")
            )
        
    )

    chart = (
            chart + text
        ).properties(
            width=150,
            height=400
        )
    

    st.altair_chart(chart, use_container_width=True)

def stackedchart():
    countries = data.filter(
        ~pl.col("oil_gas_coal").is_null()  # Trova righe dove 'oil_gas_coal' non è null
    ).select("Country Name").unique().to_series().to_list()
    countries = sorted(countries)


    selected_countries = st.multiselect(
        "Select one or more countries (max 7): ",
        countries,
        default=["Italy", "France", "Germany", "China", "United States"],
        max_selections=7,
    )

    if len(selected_countries) == 0:
        st.warning("Select at least one country to visualize the data")
        return

    selected_year = st.slider(
        "Select the year: ",
        min_value=1960,
        max_value=2015,
        value=1990,
    )

    filtered_data = data.filter(
        (pl.col("Country Name").is_in(selected_countries)) & 
        (pl.col("year") == str(selected_year))
    ).select(["Country Name", "oil_gas_coal", "nuclear", "renewable", "hydroelectric"]
    ).unpivot(
        index="Country Name",  
        variable_name="Energy Source",  
        value_name="Percentage", 
    )
    
    chart = alt.Chart(filtered_data).mark_bar().encode(
        x=alt.X("sum(Percentage):Q", stack="normalize", title="Energy production (%)"),
        y=alt.Y("Country Name:N", title="Country"),
        color=alt.Color("Energy Source:N", 
                        title="Energy source",
                        scale=alt.Scale(domain=["oil_gas_coal", "nuclear", "hydroelectric", "renewable"])),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("Energy Source:N", title="Energy source"),
            alt.Tooltip("Percentage:Q", title="Percentage", format=".2f"),
        ]
    ).properties(
        width=800,
        height=400,
    )

    st.altair_chart(chart, use_container_width=True)

# Access to electricity vs energy sources
def scatterplot(data):
    # Selezione dell'anno tramite slider
    selected_year = st.slider(
        "Select the year:",
        min_value=1990,
        max_value=2015,
        value=2015,  # Valore iniziale
    )

    # Selezione della risorsa energetica da confrontare
    energy_sources = ["oil_gas_coal", "nuclear", "renewable", "hydroelectric"]
    selected_energy = st.selectbox(
        "Select one energy source:",
        options=energy_sources,
        format_func=lambda x: {
            "oil_gas_coal": "Oil, Gas, Coal",
            "nuclear": "Nuclear",
            "renewable": "Renewable",
            "hydroelectric": "Hydroelectric",
        }.get(x, x),
    )

    # Filtrare i dati per l'anno selezionato
    filtered_data = data.filter(
        (pl.col("year") == str(selected_year)) & 
        (pl.col(selected_energy).is_not_null()) & 
        (pl.col("total_rate").is_not_null()) &
        (pl.col("Country Name")!="World")
    ).select(["Country Name", "total_rate", "Continent", selected_energy])

    if filtered_data.is_empty():
        st.warning("Nessun dato disponibile per l'anno selezionato.")
        return

    # Creare il grafico scatterplot
    chart = alt.Chart(filtered_data.to_pandas()).mark_point(size=100, filled=True).encode(
        x=alt.X("total_rate:Q", title="Access to Electricity (%)"),
        y=alt.Y(selected_energy, title=f"Usage of {selected_energy.capitalize()} (%)"),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Country"),
            alt.Tooltip("total_rate:Q", title="Access (%)", format=".2f"),
            alt.Tooltip(selected_energy, title=f"Usage of {selected_energy.capitalize()} (%)", format=".2f"),
        ],
        color=alt.Color("Continent:N", title="Continent")
    ).properties(
        width=800,
        height=600
    )

    # Mostrare il grafico
    st.altair_chart(chart, use_container_width=True)






### Pages
def page_introduction():
    st.markdown("# ACCESS TO ELECTRICITY ")
    st.markdown("## How does the access to electricity varies around the world? How does it differ in urban and rural areas? Is this related to GDP or energy imports?")
    
    
    st.markdown("""  
                ### The dataset:""")
    st.write(data)
    st.markdown('### Variables description: ')
    st.table(variable_table)
    #st.write(data.filter((pl.col("Country Name")=="Kenya") & (pl.col("year")=="2000")))
    
    st.markdown("Data source: https://databank.worldbank.org/source/world-development-indicators/")


def page_access_electricity():
    st.markdown("# Access to electricity")

    st.markdown("## Access to electricity in the world")
    st.markdown("The chart shows the trend of access to electricity worldwide from 1998 to 2022; use the red slider to select a range of years and visualize the corresponding data trend")
    linechart_world()
    st.markdown("<br><br><br>", unsafe_allow_html=True)  
    
    st.markdown("## Access to electricity around the world")
    st.markdown("The map visualizes the percentage of access to electricity across countries; use the red slider to select a specific year and move the cursor over each country to see detailed data")
    map_access()
    st.markdown("<br><br><br>", unsafe_allow_html=True) 

    st.markdown("## Comparing countries")
    st.markdown("The chart compares access to electricity across selected countries over time; use the red slider to select a range of years and choose up to five countries to visualize their respective trends")
    linechart_countries()

    st.markdown("""
    ## :question: Is access to electricity increasing over time  across the world? 

    ### :pushpin: Key observations  
    - :chart_with_upwards_trend: **LINE CHART:** Continuous increase in global electricity access from 1998 to 2022, with access rising from around 72% to over 90%.  

    - :earth_africa: **MAP:**  
        - Disparities, especially in Africa, where several countries still have low access.  
        - Increase in access to electricity for most countries over time.  

    ## :exclamation: Conclusions  
    - :heavy_check_mark: **General increase in access to electricity.**  
    - :x: **African and some Asian countries have lower access than the global average, but progress is evident.**  
    """)


def page_access_urban_rural():
    st.markdown("# Access to electricity in urban and rural areas")

    st.markdown("## Comparing access to electricity in urban and rural areas")
    st.markdown("This interactive scatter plot shows the percentage of access to electricity in urban (Y-axis) and rural (X-axis) areas. Each dot represents a country, with colors indicating continents. Use the red slider to select a specific year or use the search box to highlight a country")
    scatterplot_urban_rural()
    st.markdown("<br><br><br>", unsafe_allow_html=True) 

    st.markdown("## Map for the disparity between urban and rural areas")
    st.markdown("This interactive map visualizes the disparity between urban and rural access to electricity across countries (defined as disparity = urban_rate - rural_rate). Darker shades indicate greater disparities. Use the year slider to explore changes over time, and hover over countries for detailed data")
    map_disparity()
    st.markdown("<br><br><br>", unsafe_allow_html=True)

    st.markdown("""
    ## :question: Is access to electricity different in rural and urban areas?

    ### :pushpin: Key observations
    - :red_circle: **SCATTERPLOT:** 
        - **Europe:** high electricity access in both rural and urban areas. 
        - **Asia, Oceania, America:** some countries show slightly lower electricity access in rural areas compared to urban areas. 
        - **Africa:** vary significantly. Some, like Tunisia, have high access in both rural and urban areas, while others show low access in both areas. Many have a large gap between urban and rural access.
    - :earth_africa: **MAP:**
        - Several African countries display huge disparities in electricity access between rural and urban areas.
        - Disparity in electricity access is increasing over time in Africa, due to the fact that improvement in electricity access primarily starts from urban areas This urban-first growth widens the gap between cities and rural regions.    
    ## :exclamation: Conclusions
    - There is a clear difference between rural and urban electricity access, particularly in Africa, where disparities are often the most extreme. However, Asia, Oceania, and Central & South America also show some level of rural-urban inequality in electricity access.
    """)


def page_gdp():
    st.markdown("# Access to electricity vs GDP")

    st.markdown("## Comparing access to electricity and GDP trends")
    st.markdown("This interactive line chart compares access to electricity (red) and GDP (blue) over time for the selected country. Use the year slider to explore trends from 1960 to 2022")
    linechart_access_gdp()
    st.markdown("<br><br><br>", unsafe_allow_html=True) 

    st.markdown("## Comparing access to electricity and GDP in a specific year")
    st.markdown("This scatter plot visualizes the relationship between GDP (gross domestic product) and access to electricity (%) across countries. Use the slider to select a year and filter by continent to explore regional trends.")
    scatterplot_access_gdp()
    st.markdown("<br><br><br>", unsafe_allow_html=True) 



    st.markdown("""
    ## :question: Is There a Relationship Between ACCESS TO ELECTRICITY and GDP?

    ### :pushpin: Key observations

    - :chart_with_upwards_trend: **LINE CHART:** Some countries show a strong relationship between the two variables, while others do not:  
        - **Africa:** electricity access increases as GDP rises (e.g. Kenya).
        - **Developed countries:** no relationship, as electricity access is already close to its maximum of 100% (e.g. Italy).   

    - :red_circle: **SCATTERPLOT:** 
        - In most countries, except European ones, electricity access consistently increases with GDP, suggesting that economic growth supports electrification.
        - Some low-GDP countries (for example in Asia/Oceania) achieve high electricity access, probably because of a strong government focus on electrification.
    ## :exclamation: Conclusions  

    :heavy_check_mark: For most countries, there is a strong monotonic increasing relationship between GDP and electricity access, but other factors, such as government policies, may also play a role. 
    """)



def page_energy_imports():
    st.markdown("# Access to electricity vs energy imports")

    st.markdown("## Map for percentage of energy imports around the world")
    st.markdown("This interactive map shows the percentage of net energy imports relative to total energy use (1990-2014). Blue countries depend on energy imports, while red countries are net exporters, meaning they produce more energy than they consume. White areas have balanced values. Use the slider to select a year and zoom or pan to explore regions.")
    map_imports()
    st.markdown("<br><br><br>", unsafe_allow_html=True)  
    
    st.markdown("## Comparing access to electricity and energy imports")
    st.markdown("This scatter plot visualizes the relationship between net energy imports (% of energy use) and access to electricity (%) across countries. Use the slider to select a year and filter by continent to explore regional trends.")
    scatterplot_access_imports()
    st.markdown("<br><br><br>", unsafe_allow_html=True)  


    st.markdown("""
    ## :question: Is there a relationship between ACCESS TO ELECTRICITY and ENERGY IMPORTS?

    ### :pushpin: Key observations
    - :earth_africa: **MAP:**  
        - **Europe:** mainly imports, except for Norway
        - **Africa and Middle East:** several countries export huge quantities of energy
    - :red_circle: **SCATTERPLOT:** 
        - **Africa:** some countries have limited electrification, despite exporting large amounts of energy, likely due to weak infrastructure and low investment.
        - Strong variability in countries with high access to electricity (expecially in Asia/Oceania): many countries rely on energy imports, while others export large amounts of energy.
         
    ## :exclamation: Conclusions
    - :x: There's no single, clear relationship between access to electricity and energy imports. This relationship depends on various factors, such as local resources, infrastructure, policies and investments.
                
    - :x: Energy exports do not guarantee access to electricity: infrastructure, policies and international agreements on energy resource utilization all play a crucial role in ensuring widespread electrification.  
    """)



def page_energy_sources():
    st.title("Energy sources")

    st.header("Energy sources in the world")
    energy_trend_chart()

    st.header("Energy sources in a single country")
    circle_chart()

    st.header("Comparing countries")
    stackedchart()


def page_access_energy():
    st.title("Access to electricity vs energy sources")
    scatterplot(data)

    
# Navigation
pages = {
    "Introduction": page_introduction,
    "Access to electricity": page_access_electricity,
    "Access to electricity in urban and rural areas": page_access_urban_rural,
    "Access to electricity vs GDP": page_gdp,
    "Access to electricity vs energy imports": page_energy_imports,
    #"Energy sources??": page_energy_sources,
    #"Access to electricity vs energy sources??": page_access_energy
    
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Select: ", list(pages.keys()))

# Compute selected page
pages[selection]()
