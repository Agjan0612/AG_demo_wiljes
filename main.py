import pandas as pd
import openpyxl as pxl
import matplotlib as plt
import plotly.express as px
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

import gunicorn

pd.options.display.width= None
pd.options.display.max_columns= None
pd.set_option('display.max_rows', 3000)
pd.set_option('display.max_columns', 3000)







# Dataframes inlezen

Preferentie = pd.read_excel('pref wiljes 2023.xlsx')
recepten = pd.read_csv('recepten wiljes 2023.txt', names=['VERZEKERING', 'PATIENTNR', 'MW', 'DATUM RECEPT', 'TIJD RECEPT', 'RECEPTHERKOMST', 'EU/VU/D', 'ZI', 'ETIKETNAAM', 'EH', 'AANTAL', 'LOCATIE CODE', 'ZORGVERLENER'])
consulten = pd.read_excel('Consulten wiljes 2023.xlsx')
wachttijd = pd.read_csv('wachttijd jun tm okt 2023 wiljes.csv')

#CONSULTEN DATAFRAME
c =consulten
c['dag vd maand'] = c['PrestatieDatum'].dt.day
c[' maand vh jaar'] = c['PrestatieDatum'].dt.month
c['jaar'] = c['PrestatieDatum'].dt.year
c['maand-jaar'] = c['PrestatieDatum'].dt.to_period('M').dt.strftime('%m-%Y')
c1 = c.groupby(by=['maand-jaar', 'dag vd maand'])['dag vd maand'].count().to_frame(name='consulten per dag').reset_index()

Consulten = c1

# PREFERENTIE DATAFRAME

# Verwijder onnodige kolommen
preferentie1 = Preferentie.drop(columns=['PRK',  'ZI verstr.', 'Naam verstr.', 'S/P/G','S/P/G.1', 'W/S', 'Vrd', 'Zorgverz. groep','Patient', 'Geboortedatum', 'Verzekeraar', 'Uzovi'])
#Zet de datum kolom om in een datetime kolom zodat je de periode kan extraheren
preferentie1['Verstr. datum'] = pd.to_datetime(preferentie1['Verstr. datum'], format = '%d-%m-%Y')
preferentie1['DATUM'] = preferentie1['Verstr. datum'].dt.strftime('%d-%m-%Y')
#extraheer periode
preferentie1['MAAND-JAAR'] = pd.to_datetime(preferentie1['Verstr. datum']).dt.to_period('M')
#zet periode om naar string
preferentie1['maand-jaar'] = preferentie1['MAAND-JAAR'].dt.strftime('%m-%Y')
#combineer de zi kolom met de naam kolom
preferentie1['ZI + NAAM'] = preferentie1['ZI pref.'].astype(str) + '-' + preferentie1['Naam pref.']
# Nu gaan we een countif kolom maken per maand (aantal tellingen van een zi + naam combi per maand
preferentie2 = preferentie1.groupby(by=['maand-jaar', 'ZI + NAAM'])['ZI + NAAM'].count().to_frame(name='GEMIST PREF OP VRD ARTIKEL/MAAND').reset_index()
preferentie = preferentie2

# RECEPTEN DATAFRAME

# DATUM en TIJD kolommen omzetten naar datetime dataframes, tijdstip-uur kolom maken, dagnotitie maken, periode kolom maken (maand-jaar)

#DATUM kolom omzetten
recepten['DATUM RECEPT'] = pd.to_datetime(recepten['DATUM RECEPT'])
recepten['dag vd maand'] = recepten['DATUM RECEPT'].dt.day
recepten['maand vh jaar'] = recepten['DATUM RECEPT'].dt.month
recepten['jaar'] = recepten['DATUM RECEPT'].dt.year
recepten2 = recepten.sort_values(by=['dag vd maand', 'maand vh jaar', 'jaar'], ascending=True)
# recepten2['datum recept']= recepten2['DATUM RECEPT'].dt.strftime('%d-%m-%Y')
#periode extraheren (maand-jaar) en notitie aanpassen
recepten2['maand-jaar'] = recepten2['DATUM RECEPT'].dt.to_period('M').dt.strftime('%m-%Y')
#Tijdstip kolom omzetten naar time
recepten2['TIJD RECEPT'] = pd.to_datetime(recepten2['TIJD RECEPT'], format='%H:%M')
#UUR extraheren uit tijd kolom
recepten2['UUR'] = recepten2['TIJD RECEPT'].dt.hour
# AANTAL kolom aanpassen naar een integer
recepten2['AANTAL'] = recepten2['AANTAL'].astype(int)
#EU/VU/D kolom waarden laten vervangen door een waarde die hoort bij een verstrekkingstype
# Vervang NaN met 0.0
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].fillna(0.0)
# Zet waarden naar int --> string voor makkelijke conversie bij vervangen
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].astype(int)
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].astype(str)
# Vervang de codes door beschrijvingen van de prestaties
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].replace(dict.fromkeys(['150', '154', '152', '149', '156', '153'], 'Distributie-regels'))
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].replace(dict.fromkeys(['97', '98'], 'Eerste Uitgifte'))
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].replace('0', 'GEEN TARIEF/ZORGREGEL')
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].replace('1', 'Vervolguitgifte')
recepten2['EU/VU/D'] = recepten2['EU/VU/D'].replace('7', 'Eerste Uitgifte zonder begeleiding')
r = recepten2.loc[(recepten2['RECEPTHERKOMST'] != 'D') & (recepten2['RECEPTHERKOMST'] != 'H')] # RECEPTEN DATAFRAME ZONDER DISTRIBUTIE EN HHS REGELS

# DATAFRAME REGELS/DAG/MAAND
regels_per_dag_maand= recepten2.groupby(by=['dag vd maand', 'EU/VU/D', 'maand-jaar'])['dag vd maand'].count().to_frame(name='totaal regels/dag').reset_index()
#DATAFRAME TYPE REGEL/DAG/UUR
type_regel_per_uur_per_dag = r.groupby(by=['DATUM RECEPT', 'EU/VU/D', 'UUR'])['UUR'].count().to_frame(name='type regel/uur/dag').reset_index()
# DATAFRAME REGELS/MW/DAG/MAAND
regels_per_mw_per_dag_per_maand = recepten2.groupby(by=['maand-jaar', 'dag vd maand', 'MW'])['MW'].count().to_frame(name= 'regels/mw/dag/maand').reset_index()
#DATAFRAME REGELS/UUR/DAG
regels_per_uur_per_dag = recepten2.groupby(by=['DATUM RECEPT', 'UUR', 'RECEPTHERKOMST'])['UUR'].count().to_frame(name='regels/uur').reset_index()
#REGELS/UUR/MW/DAG
regels_per_mw_per_uur_per_dag = r.groupby(by=['DATUM RECEPT', 'UUR', 'MW'])['MW'].count().to_frame(name='regels/uur/mw/dag ex Distr & HHS').reset_index()
# DATAFRAME MET SOORT VERSTREKKING (HHS/N/D)
soort_recept = recepten2.groupby(by=['maand-jaar', 'dag vd maand', 'RECEPTHERKOMST'])['RECEPTHERKOMST'].count().to_frame(name='soort verstrekking/dag').reset_index()
# DATAFRAME MET LOCKERCODES/DAG/MAAND
lockercodes = recepten2.groupby(by=['maand-jaar', 'dag vd maand', 'LOCATIE CODE'])['LOCATIE CODE'].count().to_frame(name='Lockercode/dag/maand').reset_index()
# DATAFRAME MET VERDELING LOCKERCODES OVER HELE MAAND
lockercodes_maand = recepten2.groupby(by=['maand-jaar', 'LOCATIE CODE'])['LOCATIE CODE'].count().to_frame(name='lockercode/maand').reset_index()
# DATAFRAME met verzekeraars/maand
verzekeraars = recepten2.groupby(by=['maand-jaar', 'VERZEKERING'])['VERZEKERING'].count().to_frame(name='regels/verzekeraar/maand').reset_index()
# DATAFRAME MET VOORSCHRIJVERS/maand
voorschrijvers_maand = recepten2.groupby(by=['maand-jaar', 'ZORGVERLENER'])['ZORGVERLENER'].count().to_frame(name='regels/zorgverlener/maand').reset_index()
#DATAFRAME MET HARDSTLOPENDE ARTIKELEN VANUIT LADEKAST (excl distributie en CF)
#verwijder de receptherkomsten die niet via normale verstrekkingen lopen
ladekast = recepten2.loc[((recepten2['RECEPTHERKOMST'] != 'H') &(recepten2['RECEPTHERKOMST']!='CF')&(recepten2['RECEPTHERKOMST']!='D')&(recepten2['RECEPTHERKOMST']!='Z')& (recepten2['RECEPTHERKOMST']!='DIENST'))]

# aantal eenheden verstrekt in de maand per product
aantal_eh_verstrekt = ladekast.groupby(by=['maand-jaar', 'ZI', 'ETIKETNAAM'])['AANTAL'].sum().to_frame(name='aantal stuks/maand verstrekt').reset_index()

Aantal_per_maand = aantal_eh_verstrekt

# aantal verstrekkingen dataframe
ladekast_vs_per_maand = ladekast.groupby(by=['ZI', 'ETIKETNAAM', 'maand-jaar'])['ETIKETNAAM'].count().to_frame(name='aantal verstrekkingen ladekast producten/maand').reset_index()
ladekast_vs_per_maand['ZI'] = ladekast_vs_per_maand['ZI'].astype(str)
ladekast_vs_per_maand['zi-product'] = (ladekast_vs_per_maand['ZI'])+ '-'+ (ladekast_vs_per_maand['ETIKETNAAM'])

hardlopende_producten_per_maand = ladekast_vs_per_maand

# Aantal klanten per dag per maand
wachttijd[['DATUM', 'TICKETNUMMER', 'KNOPKEUZE', 'BALIE', 'TIJD START', 'TIJD AANGENOMEN', 'WACHTTIJD IN SECONDEN']] = wachttijd['Datum,"Ticket Nummer","Knop Keuze","Balie","Tijd Start","Tijd Aangenomen","Wachttijd in sec"'].str.split(',', expand=True)
w1 = wachttijd.drop(columns=['Datum,"Ticket Nummer","Knop Keuze","Balie","Tijd Start","Tijd Aangenomen","Wachttijd in sec"'])
w1['TIJD START'] = w1['TIJD START'].str.replace(r'"', '')
w1['TIJD START'] = pd.to_datetime(w1['TIJD START'])
w1['uur vd dag'] = w1['TIJD START'].dt.hour
w1['DATUM'] = pd.to_datetime(w1['DATUM'])
w1['dag vd maand'] = w1['DATUM'].dt.day
w1['maand-jaar'] = w1['DATUM'].dt.to_period('M')
w1['maand-jaar'] = w1['maand-jaar'].dt.strftime('%m-%Y')
w1['maand vh jaar'] = w1['DATUM'].dt.month
w1['jaar vh jaar'] = w1['DATUM'].dt.year
# klanten per dag per maand
klanten_per_dag = w1.groupby(by=['maand-jaar','dag vd maand'])['dag vd maand'].count().to_frame(name= 'klanten per dag per maand').reset_index()
# klanten per dag per uur
klanten_per_uur_per_dag = w1.groupby(by=['DATUM', 'uur vd dag'])['uur vd dag'].count().to_frame(name = 'klanten per uur').reset_index()

#-----------------------------------------------------------------------------------------------------------------------------------------

# Dropdown menu's

maand = recepten2['maand-jaar'].unique()

dag = recepten2['DATUM RECEPT'].unique()

#---------------------------------------------------------------------------------

#DATAFRAMES OP EEN RIJ VOOR DE APP
#-------------------------------------------------------------------
preferentie  #preferente middelen gemist per maand op vrd mosadex

Consulten     #consultdeclaratie per maand

regels_per_dag_maand

type_regel_per_uur_per_dag

regels_per_mw_per_dag_per_maand

regels_per_uur_per_dag

regels_per_mw_per_uur_per_dag

soort_recept

lockercodes # lc/dag/maand

lockercodes_maand

verzekeraars

voorschrijvers_maand

ladekast

aantal_eh_verstrekt
#--------------------------------------------------------------


load_figure_template('spacelab')
#WE GAAN DE APP MAKEN

app = Dash(__name__, external_stylesheets=[dbc.themes.SPACELAB])

server = app.server

load_figure_template("SPACELAB")
app.layout = dbc.Container([

    dbc.Row([

        dbc.Col(html.H1('DASHBOARD WILJES JUN TM OKT 2023')
                , width=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.H4('selecteer een maand'),
            dcc.Dropdown(id='maand-selectie', options=maand, value='06-2023')
        ], width=3)

    ]),

    dbc.Row([

        dbc.Col([
            html.H5('regels per dag per maand'),

            dcc.Graph(id='regels per dag per maand')
        ], width=12)
    ]),

    dbc.Row([

        dbc.Col([

            html.H5('consulten per maand'),

            dcc.Graph(id='consulten per maand')
        ], width=12)
    ]),

    dbc.Row([

        dbc.Col([
            html.H5('verdeling lockercodes per maand'),
            dcc.Graph(id='Lockercodes per maand'),

        ]),

        dbc.Col([
            html.H5('top 10 voorschrijvers per maand'),
            dcc.Graph(id= 'top tien voorschrijvers'),


        ]),

    ]),

    dbc.Row([

        dbc.Col([
            html.H5('Type recept per maand'),
            dcc.Graph(id='Type recept')
        ], width=6),

        dbc.Col([
            html.H5('Verdeling verzekeraars'),
            dcc.Graph(id='Verdeling verzekeraars')
        ], width=6)

    ]),

    dbc.Row([

        dbc.Col([
            html.H5('regels per mw per dag per maand'),
            dcc.Graph(id='regels per mw per dag per maand')
        ], width=12),

        dbc.Row([

        dbc.Col([
            html.H5('gemiste voorradige preferente verstrekkingen'),
            dcc.Graph(id='gemiste preferente verstrekkingen')

        ], width=12)

        ]),

        dbc.Row([
            dbc.Col([
                html.H5('klanten per dag per maand'),
                dcc.Graph(id='klanten per dag per maand'),
            ])
        ]),

        dbc.Row([
            dbc.Col([
                dbc.RadioItems(id='top artikelen', value=10, options=[10, 20, 30])
            ], width=3)
        ]),

        dbc.Row([
            dbc.Col([
                html.H5('hardlopende artikelen verstrekkingen uit ladekast'),
                dcc.Graph(id='hardlopers verstrekkingen')
            ], width=12)


        ])
    ])])


@callback(
        Output('regels per dag per maand', 'figure'),
        Output('consulten per maand', 'figure'),
        Output('regels per mw per dag per maand', 'figure'),
        Output('gemiste preferente verstrekkingen', 'figure'),
        Output('Lockercodes per maand', 'figure'),
        Output('Type recept', 'figure'),
        Output('Verdeling verzekeraars', 'figure'),
        Output('top tien voorschrijvers', 'figure'),
        Output('klanten per dag per maand', 'figure'),
        Output('hardlopers verstrekkingen', 'figure'),
        Input('maand-selectie', 'value'),
        Input('top artikelen', 'value'))



def update_grafieken(maand, top):

    r = regels_per_dag_maand.loc[regels_per_dag_maand['maand-jaar'] == maand]
    fig = px.bar(r, x='dag vd maand', y='totaal regels/dag', color='EU/VU/D', text_auto=True)

    c= Consulten.loc[Consulten['maand-jaar'] == maand]
    fig1 = px.bar(c, x='dag vd maand', y='consulten per dag')

    rmdm = regels_per_mw_per_dag_per_maand.loc[regels_per_mw_per_dag_per_maand['maand-jaar'] == maand]
    fig2 = px.bar(rmdm, x='dag vd maand', y='regels/mw/dag/maand', color='MW')

    gpv = preferentie.loc[preferentie['maand-jaar'] == maand]
    gpv1 = gpv.nlargest(n=10, columns=['GEMIST PREF OP VRD ARTIKEL/MAAND'])
    fig3 = px.bar(gpv1, x='ZI + NAAM', y='GEMIST PREF OP VRD ARTIKEL/MAAND', text_auto=True)

    tr = soort_recept.loc[soort_recept['maand-jaar'] == maand]
    fig7 = px.pie(tr, names='RECEPTHERKOMST', values='soort verstrekking/dag')

    lpm = lockercodes_maand.loc[lockercodes_maand['maand-jaar'] == maand]
    fig4 = px.pie(lpm, names='LOCATIE CODE', values='lockercode/maand')

    vsm = voorschrijvers_maand.loc[voorschrijvers_maand['maand-jaar'] == maand]
    vsm1 = vsm.nlargest(n=10, columns=['regels/zorgverlener/maand'])
    fig5 = px.pie(vsm1, names='ZORGVERLENER', values='regels/zorgverlener/maand')

    kpd = klanten_per_dag.loc[klanten_per_dag['maand-jaar'] == maand]
    fig6 = px.bar(kpd, x='dag vd maand', y='klanten per dag per maand', text_auto=True)

    vz = verzekeraars.loc[verzekeraars['maand-jaar'] == maand]
    vz10 = vz.nlargest(n=10, columns='regels/verzekeraar/maand')
    fig8= px.pie(vz10, names='VERZEKERING', values='regels/verzekeraar/maand')

    hl = hardlopende_producten_per_maand.loc[hardlopende_producten_per_maand['maand-jaar'] == maand]
    hltop = hl.nlargest(n=top, columns='aantal verstrekkingen ladekast producten/maand')
    fig9 = px.bar(hltop, x='zi-product', y='aantal verstrekkingen ladekast producten/maand', text_auto=True)






    return fig, fig1, fig2, fig3, fig4,fig7, fig8, fig5, fig6, fig9




# @callback(
#     Output('graph-content', 'figure'),
#     Input('dropdown-selection', 'value')
# )
# def update_graph(value):
#     dff = df[df.country==value]
#     return px.line(dff, x='year', y='pop')


# ])

if __name__ == '__main__':

    app.run_server(debug=True)
#

















