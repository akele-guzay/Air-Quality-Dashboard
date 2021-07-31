#import all necessary packages
import streamlit as st
import openaq
import plotly.express as px
import pandas as pd
import datetime
import plotly.graph_objects as go
from PIL import Image
from streamlit_folium import folium_static
import folium
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt

# set parameters for the page
st.set_page_config(page_title="OpenAirQuality explorer", page_icon="‍🕵🏿‍♀️",
                   layout="wide", initial_sidebar_state="expanded",)

#create an instance of the api
api = openaq.OpenAQ()
#load the list of availalble Countries which have readings
codes = api.countries(df=True,index=None,date_from='2010-01-01',limit=1000,has_geo=True)
#let's make a dictionary
cntry_dic = dict(zip(codes.code.tolist(),codes.name.tolist()))

#glossary function
def glossary():
    with st.sidebar.beta_expander('Glossary'):
        st.warning('''
        Measurement paramters:
        - pm25 measures fine inhalable particles, with diameters that are generally 2.5 micrometers and smaller in parts per million (ppm)
        - pm10 measures inhalable particles, with diameters that are generally 10 micrometers and smaller in parts per million (ppm)
        - co measures CarbonMonoxide in μg/m3
        - o3 measures atomospheric Ozone in μg/m3
        - so2 measures Sulfurdioxide in μg/m3
        - no2 measures Nitrogendioxide in μg/m3
        ''')
    return
#function to obtain information for all countries
def all_country(mode):
    df= api.countries(df=True,index=None,date_from='2010-01-01',limit=1000,has_geo=True)

    # get the GeoJson data
    geo = gpd.read_file('custom.geo.json')

    #prep the data for merging
    df.rename(columns={'name':'admin'},inplace=True)
    df = df.set_index('admin')

    #merge the datasets
    merged = geo.merge(df[['count','locations','cities']],on ='admin')

    # create the figure
    center_coor=[46.227638, 2.213749]
    #another approach for the tooltip
    m = folium.Map(location=center_coor, zoom_start=1.5,  tiles='OpenStreetMap')

    #choropleth layer for the police bounds and report data - for police sexual offenses
    chlor= folium.Choropleth(geo_data=merged,
                 data=merged,
                 columns=['admin','{}'.format(mode)],name = 'Median household income',control=False,
                 key_on='feature.properties.admin',
                 fill_color='YlGnBu', fill_opacity=0.7,
                             line_opacity=0.3,nan_fill_color="gray",
                             nan_fill_opacity=0.4,legend_name='Country count by {}'.format(mode), highlight=True,smooth_factor=0).add_to(m)

    # add labels indicating the name of the station name
    style_function = "font-size: 15px; font-weight: normal"
    chlor.geojson.add_child(
        folium.features.GeoJsonTooltip(['admin','{}'.format(mode)], style=style_function, labels=False))

    #display the map
    folium_static(m,width=940,height=500)
    #now we do the table
    df= api.countries(df=True,index=None,date_from='2010-01-01',limit=1000,has_geo=True)
    table = go.Figure(data=[go.Table(header=dict(values=list(df.columns),
                    line_color='darkslategray',
                    fill_color='#F38BA0',
                    align='left',font=dict(color='black', size=15)),
        cells=dict(values=[df['code'],df['count'],df['locations'],df['cities'],df['name']],   # 2nd column
                   line_color='#0c4271',
                   fill_color='#FFBCBC',
                   align='left',font=dict(color='black', size=12)))
    ])
    table.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(table,use_container_width=True)

    return
#function to obtain the latest readings
def latest():
    st.sidebar.info('Latest 10 readings from any country')
    df= api.latest(df=True,index=None,date_from='2010-01-01',limit=15,has_geo=True)
    st.table(df[0:10])
    return
#functiont to obtain information for specific countries
def country_compare(codes,cntry_dic):
    def get_key(val):
        for key, value in cntry_dic.items():
             if val == value:
                 return key
    #interactive layout
    with st.sidebar.form(key='parameters'):
        st.markdown('### Select parameters 👇🏿')
        country =st.selectbox('Please select a country 🌎 ',codes['name'].unique().tolist(),10)
        countries = get_key(country)
        parameters = st.selectbox('Select measurement',['pm25', 'pm10', 'so2', 'co', 'no2', 'o3'],0)
        start_date = st.date_input('Select starting date 📅',datetime.date(2021,5,1))
        end_date = st.date_input('Select end date 📅',datetime.datetime.today())
        limit = st.number_input('Entries to display 🧮', min_value=1000, max_value=5000)
        generate = st.form_submit_button(label='Get Info')
    #glossery
    glossary()
    #function to get data
    @st.cache
    def get_location_data(countries,parameters):
        '''Countries are written in two digit ISO code format'''
        df_final= api.measurements(country =countries,parameter=parameters,df=True,index=None,date_from=start_date,date_to=end_date,limit=limit,has_geo=True)
        return df_final[df_final['value']>=0] #because we have negative values

    if generate:

        df1 = get_location_data(countries,parameters)
        st.markdown('''
        {}
        ----
        '''.format(country))
        #let's map the countries
        map = go.Figure(go.Scattermapbox(
            lat=df1['coordinates.latitude'], lon=df1['coordinates.longitude'], mode='markers',marker=go.scattermapbox.Marker(size=df1['value'].apply(lambda x: (x/ df1['value'].mean()*9.8)),
            color=df1['value'], showscale=True,
            colorbar={'title': 'average {} value'.format(parameters), 'titleside': 'top', 'thickness': 7, 'ticksuffix': '{}'.format(' ppm' if parameters=='pm25' or parameters=='pm10' else ' mg/m3')})))

        # layout of the figure
        map.update_layout(hovermode='closest',mapbox=dict(style='open-street-map',
                                      center=go.layout.mapbox.Center(lat=df1['coordinates.latitude'].iloc[0], lon=df1['coordinates.longitude'].iloc[0]), zoom=3.6), margin={'r': 0, 'l': 0, 'b': 0, 't': 0})
        #display the map
        st.plotly_chart(map, use_container_width=True)

        #let's chart the parameter readings readings
        fig1 = px.line(df1, x="date.utc", y="value",
                       hover_name='parameter', log_x=False, color='location')
        fig1.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0})
        #fig1.update_layout(hovermode='x')
        st.markdown('### {} airquality readings between *{}* and *{}*'.format(parameters,df1['date.utc'].min(),df1['date.utc'].max()))
        st.plotly_chart(fig1,use_container_width=True)
        #summary of the figures
        st.markdown("### Raw data table for {} between {} and {}".format(parameters,df1['date.utc'].min(),df1['date.utc'].max()))
        st.write(df1)
        col1, col2 = st.beta_columns(2)
        col1.markdown ("### Summary of {} readings by City".format(parameters))
        col2.markdown ("### Summary of {} readings for {}".format(parameters,country))
        col1.write(df1[['city','parameter','value']].groupby('city').agg({'parameter':'count','value':['min','max','median']}).style.highlight_max(color = '#F38BA0', axis = 0))
        col2.write(df1[['country','parameter','value']].groupby('country').agg({'parameter':'count','value':['min','max','median']}))
        #now we do the table
        st.markdown('### {} measurement locations'.format(country))
        #country summary
        df= api.cities(country =countries,df=True,index=None,date_from='2010-01-01',limit=1000,has_geo=True)
        #let's display it in a Table
        table = go.Figure(data=[go.Table(header=dict(values=list(df[['city','locations']].columns),
                        line_color='darkslategray',
                        fill_color='#F38BA0',
                        align='left',font=dict(color='black', size=15)),
            cells=dict(values=[df['city'],df['locations']],   # 2nd column
                       line_color='#0c4271',
                       fill_color='#FFBCBC',
                       align='left',font=dict(color='black', size=12)))
        ])
        table.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(table,use_container_width=True)
    else:
        st.warning('Please select parameters on the left 👈🏾 ')

    return

col1,col2 = st.beta_columns((2,1))
col2.write('''<h3 style="background-color: #F38BA0; text-align: center;
font-family:monaco;border-bottom-left-radius: 15px; border-top-left-radius: 15px;
border-top-right-radius: 15px; border-bottom-right-radius: 15px; padding: 7px; box-shadow: 6px -5px #B5EAEA;">
OpenAQ Airquality Explorer</h3>''',unsafe_allow_html=True)
st.markdown('---')
menu=st.sidebar.selectbox('Menu',['About','Country Mode','All countries summary','Latest Readings'])

if menu == 'About':
    st.sidebar.markdown('Written with ❤️ in <span style="background-color: #F38BA0">Python.</span> Check out the code on [Github]('').',unsafe_allow_html=True)
    st.markdown('''
    ## Open Air Quality

    OpenAQ is a non-profit organization empowering communities around the globe to clean their air by harmonizing, sharing, and using open air quality data.

    ## Harmonizing air quality data

    The OpenAQ Community harmonizes disparate air quality data from across the world so that citizens and organizations can fight air inequality more efficiently.

    ## This app
    This app utalizes this [Python Wrapper](https://github.com/dhhagan/py-openaq) for the OpenAQ API to display airquality data from accross the globe.
    Data is displayed more or less as is.
    ''')
if menu =='All countries summary':
    try:
        st.subheader('Measurement locations by country')
        st.markdown('---')
        mode = st.sidebar.selectbox('Display map by ',['locations','count','cities'])
        all_country(mode)
    except:
        col1,col2 = st.beta_columns((0.5,1.5))
        col1.markdown('''
        ![](https://media.giphy.com/media/Rkis28kMJd1aE/giphy.gif)
        ''')
        col2.error('''
        There seems to be an error! Here's what might be happening:
        - The country/countries 🌎 you selected might not have any reading
        - The open Airquality servers might be down :(
        ''')
if menu =='Latest Readings':
    try:
        latest()
        glossary()
    except:
        col1,col2 = st.beta_columns((0.5,1.5))
        col1.markdown('''
        ![](https://media.giphy.com/media/Rkis28kMJd1aE/giphy.gif)
        ''')
        col2.error('''
        There seems to be an error! Here's what might be happening:
        - The open Airquality servers might be down :(
        ''')
if menu == 'Country Mode':
    try:
        country_compare(codes,cntry_dic)
    except:
        col1,col2 = st.beta_columns((0.5,1.5))
        col1.markdown('''
        ![](https://media.giphy.com/media/Rkis28kMJd1aE/giphy.gif)
        ''')
        col2.error('''
        There seems to be an error! Here's what might be happening:
        - The country 🌎 you selected might not have any Readings
        - The parameter you selected might not have any readings
        - The dates you specified might not have any readings
        - The open Airquality servers might be down :(
        ''')
