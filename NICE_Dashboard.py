import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phone System Data Analysis", layout="wide")

custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');

        body {
            font-family: 'Arial', 'Open Sans', sans-serif;
        }

        .custom-markdown {
            font-size: 20px;
            line-height: 1.3;
            max-width: 800px;
            width: 100%;
        }
        
        .custom-text-area {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 20;
            line-height: 1.3;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
            white-space: pre-wrap;
        }
        .largish-font {
            font-size: 20px;
            font-weight: bold;
        } 

        .large-font {
            font-size: 24px;
            font-weight: bold;
        }
        
        
        .larger-font {
            font-size: 30px;
            font-weight: bold;
        }
        
        .largest-font {
            font-size: 38px;
            font-weight: bold;
        }
        
        .title {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 56px;
            font-weight: bold;

        }
        .custom-text-area ul {
            margin-left: 1.2em;
            padding-left: 0;
            line-height: .95; 
        }

        .custom-text-area li {
            margin-bottom: 0.4em;
        }      
    </style>
"""


st.markdown(custom_css, unsafe_allow_html=True)


#add the Michelin banner to the top of the application, if the image link breaks you can correct this by copying and
#pasting an alternative image url in the ()
st.markdown(
    """
    <div style='text-align: center;'>
        <img src='https://www.tdtyres.com/wp-content/uploads/2018/12/kisspng-car-michelin-man-tire-logo-michelin-logo-5b4c286206fa03.5353854915317177300286.png' width='1000'/>
    </div>
    """,
    unsafe_allow_html=True
)

#set the application title to 'Phone System Data Analysis'
st.markdown('<div class="custom-text-area title">{}</div>'.format('Phone System Data Analysis'), unsafe_allow_html=True)


st.markdown('''<div class="custom-text-area">Insert Text Here</br> </div>
''', unsafe_allow_html=True)


st.subheader("Phone System File Upload")
phonesystem_file = st.file_uploader("Upload Phone System Data File", type=["xlsx", "xls"])



if phonesystem_file:
    with st.spinner("Processing data..."):

        #Load data
        total_calls = pd.read_excel(phonesystem_file)

        #remove milliseconds after case work column
        total_calls.drop(columns =['ACW_Time'], inplace = True)
        total_calls['Agent_Time_Mins'] = total_calls['Agent_Time'] / 60
        total_calls.sort_values("start_time", inplace=True)

        total_calls['Total_Time'] = total_calls['Total_Time'].fillna(0)

        #filter spam
        excluded_mask = (total_calls["InQueue"] == 0) & (total_calls["PreQueue"] > 0)
        excluded_calls = excluded_mask.sum()
        total_calls = total_calls.loc[~excluded_mask]


        st.dataframe(total_calls)

