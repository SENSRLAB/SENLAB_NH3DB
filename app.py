import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.interpolate import griddata
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import brentq

# To assign the plot settings to all plots
# Simply typing `rcparams()` in other python scripts will do the job.

import matplotlib.pyplot as plt
from matplotlib import rcParams

def rcparams():
    rcParams['figure.figsize'] = 5, 4
    rcParams['font.family'] = 'sans-serif'

    # Label should be far away from the axes
    rcParams['axes.labelpad'] = 8
    rcParams['xtick.major.pad'] = 7
    rcParams['ytick.major.pad'] = 7

    # Add minor ticks
    rcParams['xtick.minor.visible'] = True
    rcParams['ytick.minor.visible'] = True

    # Tick width
    rcParams['xtick.major.width'] = 1
    rcParams['ytick.major.width'] = 1
    rcParams['xtick.minor.width'] = 0.5
    rcParams['ytick.minor.width'] = 0.5

    # Tick length
    rcParams['xtick.major.size'] = 5
    rcParams['ytick.major.size'] = 5
    rcParams['xtick.minor.size'] = 3
    rcParams['ytick.minor.size'] = 3

    # Tick color
    rcParams['xtick.color'] = 'black'
    rcParams['ytick.color'] = 'black'

    rcParams['font.size'] = 14
    rcParams['axes.titlepad'] = 10
    rcParams['axes.titleweight'] = 'normal'
    rcParams['axes.titlesize'] = 18

    # Axes settings
    rcParams['axes.labelweight'] = 'normal'
    rcParams['xtick.labelsize'] = 12
    rcParams['ytick.labelsize'] = 12
    rcParams['axes.labelsize'] = 16
    rcParams['xtick.direction'] = 'in'
    rcParams['ytick.direction'] = 'in'

#######################################################################
# Data 1: Ammonia - Vapour Pressure at Gas-Liquid Equilibrium (K, MPa)
#######################################################################
    
text_1 = """
| 240 | 0.1014 |
| 240 | 0.1041 |
| 241 | 0.1076 |
| 241 | 0.1103 |
| 242 | 0.1131 |
| 243 | 0.1165 |
| 243 | 0.1193 |
| 244 | 0.1227 |
| 244 | 0.1262 |
| 245 | 0.1296 |
| 245 | 0.1331 |
| 246 | 0.1365 |
| 246 | 0.1400 |
| 247 | 0.1441 |
| 248 | 0.1475 |
| 248 | 0.1517 |
| 249 | 0.1558 |
| 249 | 0.1600 |
| 250 | 0.1634 |
| 250 | 0.1682 |
| 251 | 0.1724 |
| 251 | 0.1765 |
| 252 | 0.1813 |
| 253 | 0.1855 |
| 253 | 0.1903 |
| 254 | 0.1951 |
| 254 | 0.1999 |
| 255 | 0.2048 |
| 255 | 0.2096 |
| 256 | 0.2151 |
| 256 | 0.2199 |
| 257 | 0.2255 |
| 258 | 0.2310 |
| 258 | 0.2365 |
| 259 | 0.2420 |
| 259 | 0.2475 |
| 260 | 0.2537 |
| 260 | 0.2592 |
| 261 | 0.2654 |
| 261 | 0.2717 |
| 262 | 0.2779 |
| 263 | 0.2841 |
| 263 | 0.2910 |
| 264 | 0.2972 |
| 264 | 0.3041 |
| 265 | 0.3110 |
| 265 | 0.3178 |
| 266 | 0.3254 |
| 266 | 0.3323 |
| 267 | 0.3399 |
| 268 | 0.3475 |
| 268 | 0.3551 |
| 269 | 0.3627 |
| 269 | 0.3702 |
| 270 | 0.3785 |
| 270 | 0.3868 |
| 271 | 0.3951 |
| 271 | 0.4033 |
| 272 | 0.4116 |
| 278 | 0.5054 |
| 283 | 0.6150 |
| 289 | 0.7419 |
| 294 | 0.8880 |
| 298 | 0.9860 |
| 298 | 1.00 |
| 299 | 1.02 |
| 299 | 1.04 |
| 300 | 1.05 |
| 300 | 1.07 |
| 301 | 1.09 |
| 301 | 1.11 |
| 302 | 1.13 |
| 303 | 1.15 |
| 303 | 1.17 |
| 304 | 1.19 |
| 304 | 1.21 |
| 305 | 1.23 |
| 305 | 1.25 |
| 306 | 1.27 |
| 306 | 1.29 |
| 307 | 1.31 |
| 308 | 1.33 |
| 308 | 1.35 |
| 309 | 1.37 |
| 309 | 1.39 |
| 310 | 1.42 |
| 310 | 1.44 |
| 311 | 1.46 |
| 311 | 1.48 |
| 312 | 1.51 |
| 313 | 1.53 |
| 313 | 1.55 |
| 314 | 1.58 |
| 314 | 1.60 |
| 315 | 1.63 |
| 315 | 1.65 |
| 316 | 1.68 |
| 316 | 1.70 |
| 317 | 1.73 |
| 318 | 1.75 |
| 318 | 1.78 |
| 319 | 1.81 |
| 319 | 1.84 |
| 320 | 1.86 |
| 320 | 1.89 |
| 321 | 1.92 |
| 321 | 1.95 |
| 322 | 1.97 |
| 330 | 2.42 |
| 350 | 3.87 |
| 370 | 5.88 |
| 390 | 8.60 |
| 400 | 10.3 |
| 405 | 11.3 |
"""

# Split the text by lines
lines = text_1.strip().split('\n')

# Initialize an empty list to store tuples
data = []

# Iterate over the lines to process each one
for line in lines:
    # Split the line by '|' and strip whitespace, then convert each part to the correct type
    kelvin, mpa = line.strip("| ").split(" | ")
    data.append((int(kelvin), float(mpa)))

vapor_pressure_data = data

# Make converted tuples into DataFrame
df_vpgle = pd.DataFrame(data, columns=['Kelvin', 'MPa'])

###############################################################
# Data 2: Density of Ammonia vs. Temperature (Celsius, g_per_l)
###############################################################

text_2 = """
| -35 | 0.8843 |
| -10 | 0.7938 |
| 0 | 0.7625 |
| 10 | 0.7336 |
| 20 | 0.7069 |
| 30 | 0.6822 |
| 40 | 0.6593 |
| 50 | 0.6380 |
| 75 | 0.5909 |
| 100 | 0.5509 |
| 125 | 0.5162 |
| 150 | 0.4858 |
| 175 | 0.4586 |
| 200 | 0.4341 |
| 250 | 0.3917 |
| 300 | 0.3573 |
| 350 | 0.3295 |
| 400 | 0.3058 |
"""

# Split the text by lines
lines = text_2.strip().split('\n')

# Initialize an empty list to store tuples
data = []

# Iterate over the lines to process each one
for line in lines:
    # Split the line by '|' and strip whitespace, then convert each part to the correct type
    celsius, g_per_l = line.strip("| ").split(" | ")
    data.append((float(celsius), float(g_per_l)))

# Make converted tuples into DataFrame
df_density = pd.DataFrame(data, columns=['Celsius', 'g_per_l'])

# Add the column Kelvin
df_density['Kelvin'] = df_density['Celsius'] + 273.15


###############################################################
# STREAMLIT
###############################################################

# Streamlit 초기셋팅 (좁게, 사이드바 펼쳐진 상태, 제목, 아이콘)
st.set_page_config(layout="centered", initial_sidebar_state="auto", page_title="EESLAB 암모니아 물성 데이터베이스", page_icon=":atom:")

# Streamlit app layout
st.title("EESLAB 암모니아 물성 데이터베이스 V1.0.1 (@last updated 2024-03-19)")


# Sidebar to show app info.
st.sidebar.markdown("""
                    
    ### **EESLAB**
    - [EESLAB Homepage](https://sites.google.com/view/ees-snu/home)
                    
    ### **Contributors**
    - 고우진 (woojingo@snu.ac.kr)
    - 민채림 (asd578300@snu.ac.kr)
    - 정건우 (gw.jeong@snu.ac.kr)
    - 강태현 (kang990925@pusan.ac.kr)
    
    ### **Supervisor**
    - 서유택 (yutaek.seo@snu.ac.kr)
    """)

# User selects the desired property
option = st.selectbox(
    "원하시는 암모니아 물성을 선택하세요:",
    (
        "Vapour Pressure at Gas-Liquid Equilibrium",
        "Density vs. Temperature",
        "Specific heat vs. Temperature",
        "Dew point and bubble point information"
    )
)

if option == "Vapour Pressure at Gas-Liquid Equilibrium":
    st.write("**Vapor Pressure at Gas-Liquid Equilibrium**을 선택하셨네요.")

    st.markdown("#### **Data 1: Vapour Pressure at Gas-Liquid Equilibrium**", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)  # Creates two columns

    with col1:
        with st.expander("클릭하여 문헌 데이터를 확인해보세요."):
            # Create an interactive plot
            fig, ax = plt.subplots()
            rcparams()

            # Plot the data
            ax.plot(df_vpgle['Kelvin'], df_vpgle['MPa'], 'o', color='black')

            ax.set_xlabel('Temperature (K)')
            ax.set_ylabel('Pressure (MPa)')
            st.pyplot(fig)
            st.markdown("이 문헌 값을 interpolation하여 값을 제시한답니다.", unsafe_allow_html=True)
    
    with col2: 
        user_choice = st.radio(
            "'온도 (temperature)'와 '압력 (pressure)' 중에서 알고 계신 값을 선택해주세요:",
            ('temperature', 'pressure')
        )
        
        # Interpolation functions
        interp_pressure = interp1d(df_vpgle['Kelvin'], df_vpgle['MPa'], bounds_error=False, fill_value="extrapolate")
        interp_temperature = interp1d(df_vpgle['MPa'], df_vpgle['Kelvin'], bounds_error=False, fill_value="extrapolate")
        
        if user_choice == 'temperature':
            temperature = st.number_input('온도를 켈빈 (K) 단위로 입력해주세요.', min_value=241, max_value=410)
            if temperature:
                pressure = interp_pressure(temperature)
                st.write(f"해당 온도에 따른 압력은 {pressure} MPa 입니다.")
                
        elif user_choice == 'pressure':
            pressure = st.number_input('압력을 메가파스칼 (MPa) 단위로 입력해주세요.', min_value=0.0, max_value=12.0)
            if pressure:
                temperature = interp_temperature(pressure)
                st.write(f"해당 압력에 따른 온도는 {temperature} K 입니다.")

elif option == "Density vs. Temperature":
    st.write("**Density vs. Temperature**을 선택하셨네요.")

    st.markdown("#### **Data 2: Density of Ammonia vs. Temperature**", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("클릭하여 문헌 데이터를 확인해보세요."):
            # Create an interactive plot
            fig, ax = plt.subplots()
            rcparams()

            # Plot the data
            ax.plot(df_density['Kelvin'], df_density['g_per_l'], 'o', color='black')

            ax.set_xlabel('Temperature (K)')
            ax.set_ylabel('Density (g/L)')
            st.pyplot(fig)

            st.markdown("이 문헌 값을 interpolation하여 값을 제시한답니다.", unsafe_allow_html=True)

    with col2:
        user_choice = st.radio(
            "어떤 단위의 온도를 사용하시겠어요?",
            ('Kelvin', 'Celsius')
        )

        # Interpolation functions
        interp_density = interp1d(df_density['Kelvin'], df_density['g_per_l'], bounds_error=False, fill_value="extrapolate")

        if user_choice == 'Kelvin':
            temperature = st.number_input('온도를 켈빈 (K) 단위로 입력해주세요.', min_value=200, max_value = 700)
            if temperature:
                density = interp_density(temperature)
                st.write(f"온도에 따른 밀도는 {density} g/L 입니다.")

        elif user_choice == 'Celsius':
            temperature = st.number_input('온도를 섭씨 (Celsius) 단위로 입력해주세요.', min_value=-73, max_value=427)
            if temperature:
                density = interp_density(temperature + 273.15)
                st.write(f"온도에 따른 밀도는 {density} g/L 입니다.")

###############################################################
# Data 3: Specific heat vs. Temperature
###############################################################

elif option == "Specific heat vs. Temperature":
    st.write("**Specific heat vs. Temperature**을 선택하셨네요.")

    # Display information using markdown
    st.markdown("""
    #### **Data 3: Specific heat vs. Temperature**

    이 프로그램에서는 보다 넓은 온도 범위에서 암모니아의 Specific heat을 계산하기 위해, [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7664417&Mask=1&Type=JANAFG&Table=on#ref-1)에서 제공하는 바와 같이, Shomate 방정식을 사용합니다. 

    - **Shomate 방정식**: 
        $$
        C_{p}^{o} = A + Bt + Ct^{2} + Dt^{3} + \\frac{E}{t^{2}}
        $$

        $$
        H^{o} - H^{o}_{298.15} = At + \\frac{Bt^{2}}{2} + \\frac{Ct^{3}}{3} + \\frac{Dt^{4}}{4} - \\frac{E}{t} + F - H
        $$

        $$
        S^{o} = A\\ln{t} + Bt + \\frac{Ct^{2}}{2} + \\frac{Dt^{3}}{3} - \\frac{E}{2t^{2}} + G
        $$

    - **암모니아의 Shomate 방정식에 대한 계수들은 다음과 같습니다.**
        - $t$: temperature (K) / 1000.0
        - $A$: 19.99563
        - $B$: 49.77119
        - $C$: -15.37599
        - $D$: 1.921168
        - $E$: 0.189174
        - $F$: -53.30667
        - $G$: 203.8591
        - $H$: -45.89806
        - **Comment**: Data last reviewed in June, 1977
    """, unsafe_allow_html=True)

    def shomate_equation(T, A, B, C, D, E, F, G, H):
        t = T / 1000.0
        Cp = A + B*t + C*t**2 + D*t**3 + E/t**2
        Delta_H = A*t + B*t**2/2 + C*t**3/3 + D*t**4/4 - E/t + F - H #Delta_H = H^o - H^o_298.15
        S = A*np.log(t) + B*t + C*t**2/2 + D*t**3/3 - E/(2*t**2) + G
        return Cp, Delta_H, S

    # Shomate Equation Constants for NH3 (from the provided table)
    A, B, C, D, E, F, G, H = 19.99563, 49.77119, -15.37599, 1.921168, 0.189174, -53.30667, 203.8591, -45.89806

    # 구분선
    st.markdown("------", unsafe_allow_html=True)

    # User input for temperature

    col1, col2 = st.columns(2) 

    with col1:

        input_temperature = st.number_input("**온도 값을 켈빈 (K) 단위로 입력해주세요 (200 ~ 1400).**", min_value=200, max_value=1400, step=50)

        if input_temperature:
            # Calculating properties
            Cp, Delta_H, S = shomate_equation(input_temperature, A, B, C, D, E, F, G, H)

            # Alert
            st.markdown("온도에 따른 암모니아의 Specific heat, $\Delta H$, $S^{o}$ 값을 아래 표에서 확인해보세요.")

            # Displaying properties
            st.markdown("""
                        | **Specific heat (J/mol*K)** | **$\Delta H$ (kJ/mol)** | **$S°$ (J/mol*K)** |
                        | :---: | :---: | :---: |
                        | {0:.2f} | {1:.2f} | {2:.2f} |
                        """.format(Cp, Delta_H, S), unsafe_allow_html=True)
            
            st.markdown("------", unsafe_allow_html=True)
            st.markdown("입력 온도에 따라 변하는 Specific heat, $\Delta H$, $S^{o}$ 값을 그래프에서 확인해보세요.", unsafe_allow_html=True)
            
    with col2:

        # Plotting
        T_range = np.arange(200, 1400, 1)
        Cp_values, Delta_H_values, S_values = shomate_equation(T_range, A, B, C, D, E, F, G, H)

        fig, axs = plt.subplots(3, 1, figsize=(5, 8))
        rcparams()

        ## 선형플롯 1
        axs[0].plot(T_range, Cp_values, 'g-')
        axs[0].set_xlabel('Temperature (K)')
        axs[0].set_ylabel(r'$C_{p}^{o}$ (J/mol*K)')

        ## 사용자의 입력 온도에 대한 Cp 값 그래프에 표시
        axs[0].axvline(x=input_temperature, color = 'green', linestyle='--', linewidth=0.5)
        axs[0].axhline(y=Cp, color = 'green', linestyle='--', linewidth=0.5)
        axs[0].plot(input_temperature, Cp, 'g-', markersize=5)

        ## 선형플롯 2
        axs[1].plot(T_range, Delta_H_values, 'r')
        axs[1].set_xlabel('Temperature (K)')
        axs[1].set_ylabel(r'$\Delta H$ (kJ/mol)')
        
        ## 사용자의 입력 온도에 대한 Delta_H 값 그래프에 표시
        axs[1].axvline(x=input_temperature, color = 'red', linestyle='--', linewidth=0.5)
        axs[1].axhline(y=Delta_H, color = 'red', linestyle='--', linewidth=0.5)
        axs[1].plot(input_temperature, Delta_H, 'r')

        ## 선형플롯 3
        axs[2].plot(T_range, S_values, 'b-')
        axs[2].set_xlabel('Temperature (K)')
        axs[2].set_ylabel(r'$S^{o}$ (J/mol*K)')
        
        ## 사용자의 입력 온도에 대한 S 값 그래프에 표시
        axs[2].axvline(x=input_temperature, color = 'blue', linestyle='--', linewidth=0.5)
        axs[2].axhline(y=S, color = 'blue', linestyle='--', linewidth=0.5)
        axs[2].plot(input_temperature, S, 'b-')

        plt.tight_layout()
        st.pyplot(fig)

###############################################################
# Data 4: Dew point and bubble point information
###############################################################

elif option == "Dew point and bubble point information":
    st.write("**Dew point and bubble point information**을 선택하셨네요.")

    st.markdown("#### Data 4: Dew point and bubble point information", unsafe_allow_html=True)

    mixture_choice = st.radio(
        "원하시는 항목을 아래에서 선택해주세요:",
        ('1. Pure $NH_3$', '2. $NH_3 + H_2O$ 혼합물', '3. $NH_3 + H_2$ 혼합물')
    )

    if mixture_choice == "1. Pure $NH_3$": 
        st.markdown("""
                    ------
                    ## 순수 $NH_3$의 거품점 및 이슬점 정보""", unsafe_allow_html=True)

        # Convert to arrays for interpolation
        temperatures, pressures = zip(*vapor_pressure_data)
        temperatures = np.array(temperatures)
        pressures = np.array(pressures)

        # Remove duplicates
        _, idx = np.unique(temperatures, return_index=True)
        temperatures = temperatures[idx]
        pressures = pressures[idx]

        # Interpolate to find temperature for a given pressure and vice versa
        vapor_pressure_func_temp = interp1d(pressures, temperatures, kind='cubic', fill_value="extrapolate")
        vapor_pressure_func_press = interp1d(temperatures, pressures, kind='cubic', fill_value="extrapolate")

        def calculate_dew_point(system_pressure=None, system_temperature=None):
            try:
                if system_pressure is not None:
                    return vapor_pressure_func_temp(system_pressure)
                elif system_temperature is not None:
                    return vapor_pressure_func_press(system_temperature)
            except ValueError as e:
                st.error(f'Error: {e}')
                return np.nan
            
        def calculate_bubble_point(system_pressure=None, system_temperature=None):
            try:
                if system_pressure is not None:
                    return vapor_pressure_func_temp(system_pressure)
                elif system_temperature is not None:
                    return vapor_pressure_func_press(system_temperature)
            except ValueError as e:
                st.error(f'Error: {e}')
                return np.nan
            
        col1, col2 = st.columns(2)

        with col1:
            # Plotting 
            fig, ax = plt.subplots()
            rcparams()

            # Plot the data
            ax.plot(df_vpgle['Kelvin'], df_vpgle['MPa'], 'o', color='black')

            ax.set_xlabel('Temperature (K)')
            ax.set_ylabel('Pressure (MPa)')
            st.pyplot(fig)

        with col2:
            user_choice = st.radio(
                "어떤 변수를 입력하시겠어요?", 
                ('Pressure', 'Temperature')
            )

            if user_choice == 'Pressure':
                system_pressure = st.number_input('압력을 메가파스칼 (MPa) 단위로 입력해주세요.', min_value=0.1, max_value=12.0, step=0.5)
                if system_pressure:
                    dew_point = calculate_dew_point(system_pressure=system_pressure)
                    st.write(f"해당 압력에 대한 이슬점 온도는 {dew_point:.2f} K 입니다.")

                    bubble_point = calculate_bubble_point(system_pressure=system_pressure)
                    st.write(f"해당 압력에 대한 거품점 온도는 {bubble_point:.2f} K 입니다.")
                    st.markdown("**INFO.** 순수 암모니아의 경우, 거품점 온도는 이슬점 온도와 같답니다.")

            elif user_choice == 'Temperature':
                system_temperature = st.number_input('온도를 켈빈 (K) 단위로 입력해주세요.', min_value=241, max_value=410, step=5)
                if system_temperature != 0:
                    dew_point = calculate_dew_point(system_temperature=system_temperature)
                    bubble_point = calculate_bubble_point(system_temperature=system_temperature)

                    if not np.isnan(dew_point):
                        st.write(f"해당 온도에 대한 이슬점 압력은 {dew_point:.2f} MPa 입니다.")

                    if not np.isnan(bubble_point):
                        st.write(f"해당 온도에 대한 거품점 압력은 {bubble_point:.2f} MPa 입니다.")
                        st.markdown("**INFO.** 순수 암모니아의 경우, 거품점 압력은 이슬점 압력과 같습니다.")

    elif mixture_choice == "2. $NH_3 + H_2O$ 혼합물":
        st.markdown("""
        ------
        ## $NH_3 + H_2O$ 혼합물의 거품점 및 이슬점 정보
        > **Reference**: [Development of thermo-physical properties of aqua ammonia for Kalina cycle system (Ganesh et al.)](https://doi.org/10.1504/IJMPT.2017.084955)
        """)

        # Load bubble and dew point data
        df_bubble_data_celsius = pd.read_csv('./NH3+H2O_bubbleline.csv', index_col=0)
        df_bubble_data_kelvin = df_bubble_data_celsius + 273.15
        df_dew_data_celsius = pd.read_csv('./NH3+H2O_dewline.csv', index_col=0)
        df_dew_data_kelvin = df_dew_data_celsius + 273.15

        # Prepare the data for interpolation
        x = df_bubble_data_kelvin.index.values.astype(float)  # Ammonia mass fraction
        y_bubble = df_bubble_data_kelvin.columns.values.astype(float)  # Pressure for bubble line
        y_dew = df_dew_data_kelvin.columns.values.astype(float)  # Pressure for dew line
        z_bubble = df_bubble_data_kelvin.values  # Temperature for bubble line
        z_dew = df_dew_data_kelvin.values  # Temperature for dew line

        # Interpolation functions using RectBivariateSpline, which is suitable for grid data
        interp_bubble = RectBivariateSpline(x, y_bubble, z_bubble)
        interp_dew = RectBivariateSpline(x, y_dew, z_dew)

        # Define a function to find pressure for a given temperature and ammonia mass fraction
        def find_pressure(temperature, ammonia_mass_fraction, interp_func, pressure_range):
            # Define the function whose root we want to find
            def temp_difference(pressure):
                return interp_func(ammonia_mass_fraction, pressure, grid=False) - temperature
            
            # Use brentq to find the root, which in our case is the pressure
            try:
                return brentq(temp_difference, *pressure_range)
            except ValueError:
                return np.nan  # Return NaN if the root is not bracketed

        # Plotting setup
        colors = plt.cm.jet(np.linspace(0, 1, len(df_bubble_data_kelvin.columns))) # Color map

        # Create plot
        fig, ax = plt.subplots(figsize=(5, 4))
        rcparams()

        # Plot bubble point lines
        for i, column in enumerate(df_bubble_data_kelvin.columns):
            ax.plot(df_bubble_data_kelvin.index, df_bubble_data_kelvin[column], color=colors[i], label=f'{column} (Bubble)', linestyle='-')

        # Plot dew point lines
        for i, column in enumerate(df_dew_data_kelvin.columns):
            ax.plot(df_dew_data_kelvin.index, df_dew_data_kelvin[column], color=colors[i], label=f'{column} (Dew)', linestyle=':')

        ax.set_xlabel(r'Ammonia Mass Fraction, $x_{\mathrm{NH}_3}$')
        ax.set_ylabel('Temperature (K)')
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=2, title='Pressure (MPa)')
        ax.grid(True, linestyle=':', linewidth=1, alpha=0.8)
        st.pyplot(fig)

        col1, col2 = st.columns(2)
        with col1: 
        
            # User input and calculation
            user_choice = st.radio(
                "온도 (Temperature) 또는 압력 (Pressure) 중 어떤 것을 입력하시겠어요?",
                ('Temperature', 'Pressure')
            )

        with col2: 
            if user_choice == 'Temperature':
                temperature_k = st.number_input('온도를 켈빈 (K) 단위로 입력해주세요 (220 ~ 560 K).', min_value=220.0, max_value=560.0, step=10.0)
                x_nh3 = st.number_input("암모니아 분율을 입력해주세요 (0 ~ 1).", min_value=0.0, max_value=1.0, step=0.1)

                if temperature_k and x_nh3 is not None:
                    # Interpolate and calculate bubble and dew points
                    pressure_bubble = find_pressure(temperature_k, x_nh3, interp_bubble, pressure_range=(0.0, 10.0))
                    pressure_dew = find_pressure(temperature_k, x_nh3, interp_dew, pressure_range=(0.0, 10.0))

                    st.write(f"해당 온도와 암모니아 분율에 대한 거품점 압력은 {pressure_bubble:.2f} MPa 입니다.")
                    st.write(f"해당 온도와 암모니아 분율에 대한 이슬점 압력은 {pressure_dew:.2f} MPa 입니다.")

            elif user_choice == 'Pressure':
                pressure_mpa = st.number_input('압력을 메가파스칼 (MPa) 단위로 입력해주세요 (0 ~ 10).', min_value=0.0, max_value=10.0)
                x_nh3 = st.number_input("암모니아 분율을 입력해주세요 (0 ~ 1).", min_value=0.0, max_value=1.0)

                if pressure_mpa and x_nh3 is not None:
                    # Interpolate and calculate bubble and dew points
                    temperature_bubble = interp_bubble(x_nh3, pressure_mpa, grid=False)
                    temperature_dew = interp_dew(x_nh3, pressure_mpa, grid=False)

                    st.write(f"해당 압력과 암모니아 분율에 대한 거품점 온도는 {temperature_bubble:.2f} K 입니다.")
                    st.write(f"해당 압력과 암모니아 분율에 대한 이슬점 온도는 {temperature_dew:.2f} K 입니다.")
    
    elif mixture_choice == "3. $NH_3 + H_2$ 혼합물":
        st.markdown("""
        ------
        ## $NH_3 + H_2$ 혼합물의 거품점 및 이슬점 정보
        > **Reference**: [Phase Behavior in the Hydrogen-Ammonia System (Reamer et al.)](https://doi.org/10.1021/je60002a012)""", unsafe_allow_html=True
        )

        st.markdown("NOTE: 해당 문헌에서는 암모니아의 몰 분율에 따른 거품점과 이슬점 정보를 제공하고 있습니다. 이를 질량 분율로 변환하기 위해, 아래와 같은 환산과정을 사용했어요.")
        # Create a checkbox
        if st.checkbox('**체크박스 눌러 환산 과정 확인하기**'):
            # Display the markdown text when the checkbox is checked
            st.markdown("""
            ----
                        
            ## **Mass fraction conversion**

            This code converts the __mole fractions of *ammonia* at both dew / bubble points to mass fractions__. This conversion is crucial when working with mixtures of gases, like ammonia and hydrogen, as it allows for the representation of the composition in terms of mass instead of moles.

            This program calculates the mass fraction from the mole fraction using the molecular weights of hydrogen and ammonia. The conversion is performed as follows:

            1. Calculate the mole fraction of NH₃ ($x_{NH_3}$) as the complement of the hydrogen mole fraction:
            $$ x_{NH_3} = 1 - x_{H_2} $$

            2. Convert the mole fractions to mass fractions. The mass fraction of ammonia (NH₃) in the mixture can be calculated using the formula:        
                $$ w_{NH_3} = \\frac{x_{NH_3} \\times MW_{NH_3}}{x_{H_2} \\times MW_{H_2} + x_{NH_3} \\times MW_{NH_3}} $$
                        
            <br> where:
            - $w_{NH_3}$ is the mass fraction of ammonia,
            - $x_{H_2}$ is the mole fraction of hydrogen,
            - $x_{NH_3}$ is the mole fraction of ammonia,
            - $MW_{H_2}$ is the molecular weight of hydrogen (**2.016 g/mol**),
            - $MW_{NH_3}$ is the molecular weight of ammonia (**17.031 g/mol**).
                        
            ----
                        
            """, unsafe_allow_html=True)

        df_nh3h2 = pd.read_csv("./nh3+h2_modified.csv")

        # Data processing for NH3 + H2 mixture
        df_nh3h2['T_Kel'] = round((df_nh3h2['T_F'] - 32) * (5/9) + 273.15, 3)
        df_nh3h2['P_MPa'] = round(df_nh3h2['P_psi'] * 0.00689476, 3)

        # Convert mole fraction to mass fraction
        mw_h2 = 2.016  # g/mol for H2
        mw_nh3 = 17.031  # g/mol for NH3
        df_nh3h2['DewP_NH3'] = 1 - df_nh3h2['DewP']
        df_nh3h2['BubbleP_NH3'] = 1 - df_nh3h2['BubbleP']
        df_nh3h2['DewP_NH3_mass'] = (df_nh3h2['DewP_NH3'] * mw_nh3) / (df_nh3h2['DewP'] * mw_h2 + df_nh3h2['DewP_NH3'] * mw_nh3)
        df_nh3h2['BubbleP_NH3_mass'] = (df_nh3h2['BubbleP_NH3'] * mw_nh3) / (df_nh3h2['BubbleP'] * mw_h2 + df_nh3h2['BubbleP_NH3'] * mw_nh3)

        # Display initial data
        st.markdown("### 1. 가공된 데이터 미리보기:")
        st.dataframe(df_nh3h2)

        # Visualization of P-x curve for NH3 + H2 mixture
        st.markdown("### 2. NH₃ + H₂ 혼합물에 대한 P-x 정보 ([문헌](https://doi.org/10.1021/je60002a012) 발췌):")
        st.markdown("동그라미는 이슬점, 마름모는 거품점을 나타냅니다.", unsafe_allow_html=True)

        # Plot
        fig, ax = plt.subplots(figsize=(5, 4))

        # Define the temperature values for which you want to plot the P-x curve
        temperatures = [277.594, 310.928, 344.261, 377.594, 394.261]

        # Color dic
        color_dict = {277.594: 'blue', 310.928: 'green', 344.261: 'r', 377.594: 'orange', 394.261: 'purple'}

        for temp in sorted(df_nh3h2['T_Kel'].unique()):
            df_temp = df_nh3h2[df_nh3h2['T_Kel'] == temp]
            ax.scatter(df_temp['DewP_NH3_mass'], df_temp['P_MPa'], marker='o', label=f'{temp} K', color=color_dict[temp], alpha=0.6, s=20)
            ax.scatter(df_temp['BubbleP_NH3_mass'], df_temp['P_MPa'], marker='D', color=color_dict[temp], alpha=0.6, s=20)

        ax.set_xlabel('Ammonia Mass Fraction, $x_{\\mathrm{NH}_3}$')
        ax.set_ylabel('Pressure (MPa)')

        # LIMS
        ax.set_xlim(0, 1)

        ax.legend(loc='upper right', bbox_to_anchor=(1.4, 1), fontsize=11)
        st.pyplot(fig)

        st.markdown("### 3. NH₃ + H₂ 혼합물에 대한 P-x 내삽 그래프:")

        # Adjusting the temperature and ammonia mass fraction range as requested
        temperature_range = np.linspace(277.6, 394.2, 1000)
        ammonia_mass_fraction_range = np.linspace(0, 1, 1000)
        ammonia_mass_fraction_grid, temperature_grid = np.meshgrid(ammonia_mass_fraction_range, temperature_range)

        # Re-interpolating the data with the updated grid
        dew_point_pressure_grid = griddata(
            (df_nh3h2['T_Kel'], df_nh3h2['DewP_NH3_mass']),
            df_nh3h2['P_MPa'],
            (temperature_grid, ammonia_mass_fraction_grid),
            method='cubic'
        )

        bubble_point_pressure_grid = griddata(
            (df_nh3h2['T_Kel'], df_nh3h2['BubbleP_NH3_mass']),
            df_nh3h2['P_MPa'],
            (temperature_grid, ammonia_mass_fraction_grid),
            method='cubic'
        )

        # Plotting the updated interpolated data
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

        # Dew Point Pressure plot
        c1 = ax1.pcolormesh(ammonia_mass_fraction_grid, temperature_grid, dew_point_pressure_grid, shading='auto', cmap='plasma', vmin=0, vmax=40)
        ax1.set_title(r'$P_{\mathrm{dew}}$')
        ax1.set_xlabel(r'Ammonia Mass Fraction, $x_{\mathrm{NH}_3}$')
        ax1.set_ylabel('Temperature (K)')
        fig.colorbar(c1, ax=ax1).set_label('Pressure (MPa)')

        # Bubble Point Pressure plot
        c2 = ax2.pcolormesh(ammonia_mass_fraction_grid, temperature_grid, bubble_point_pressure_grid, shading='auto', cmap='plasma', vmin=0, vmax=40)
        ax2.set_title(r'$P_{\mathrm{bubble}}$')
        ax2.set_xlabel(r'Ammonia Mass Fraction, $x_{\mathrm{NH}_3}$')
        ax2.set_ylabel('Temperature (K)')
        fig.colorbar(c2, ax=ax2).set_label('Pressure (MPa)')

        # LIMS
        ax1.set_xlim(0, 1)
        ax2.set_xlim(0.95, 1)
        ax1.set_ylim(279.9, 400.1)
        ax2.set_ylim(279.9, 400.1)
        st.pyplot(fig)

        st.markdown("### 4. 내삽 데이터 다운로드 받기:")
        st.markdown("> 아래 버튼을 눌러 내삽 데이터를 확인해볼 수 있어요 (용량: 약 45 mb).")

        # Create a download button
        if st.button('**클릭하여 내삽 데이터 (CSV) 만들기**'):
            # Save the interpolated data to a DataFrame
            df_interpolated = pd.DataFrame({
                'T_Kel': temperature_grid.flatten(),
                'x_nh3': ammonia_mass_fraction_grid.flatten(),
                'DewP': dew_point_pressure_grid.flatten(),
                'BubbleP': bubble_point_pressure_grid.flatten()
            })

            # Save the DataFrame to a CSV file
            df_interpolated.to_csv('nh3+h2_interpolated.csv', index=False)

            # Display the download link
            st.markdown(
                f'<a href="nh3+h2_interpolated.csv" download="nh3+h2_interpolated.csv">nh3+h2_interpolated 다운받기.csv</a>',
                unsafe_allow_html=True
            )

        # Interactive user inputs and results
        st.markdown("### 5. 사용자 입력 및 결과 확인")
        # User input and calculation
        user_choice = st.radio(
            "온도 (Temperature) 또는 압력 (Pressure) 중 어떤 것을 입력하시겠어요?",
            ('Temperature', 'Pressure')
        )

        if user_choice == 'Temperature':
            user_temp = st.number_input("원하시는 온도를 입력하세요 (K):", min_value=float(df_nh3h2['T_Kel'].min()), max_value=float(df_nh3h2['T_Kel'].max()), value=330.0, step=50.0)
            user_mass_fraction = st.number_input("암모니아 분율을 입력해주세요 (0 ~ 1):", min_value=0.0, max_value=1.0, value=0.7, step=0.1)

            # Find the nearest indices in the grid for the user's input
            temp_idx = (np.abs(temperature_range - user_temp)).argmin()
            mass_frac_idx = (np.abs(ammonia_mass_fraction_range - user_mass_fraction)).argmin()

            # Get the corresponding pressure values
            dew_point_pressure = dew_point_pressure_grid[temp_idx, mass_frac_idx]
            bubble_point_pressure = bubble_point_pressure_grid[temp_idx, mass_frac_idx]

            # Display the results
            if np.isnan(dew_point_pressure): 
                st.error("해당 온도와 암모니아 분율에 대한 이슬점 압력을 찾을 수 없어요.")
            else:
                st.write(f"해당 온도와 암모니아 분율에 대한 이슬점 압력은 {round(dew_point_pressure, 2)} MPa 이에요.")

            if np.isnan(bubble_point_pressure):
                st.error("해당 온도와 암모니아 분율에 대한 거품점 압력을 찾을 수 없어요.")
            else:
                st.write(f"해당 온도와 암모니아 분율에 대한 거품점 압력은 {round(bubble_point_pressure, 2)} MPa 이에요.")

        elif user_choice == 'Pressure':
            user_pressure = st.number_input("원하시는 압력을 입력하세요 (MPa):", min_value=0.0, max_value=40.0, value=10.0, step=1.0)
            user_mass_fraction = st.number_input("암모니아 분율을 입력해주세요 (0 ~ 1):", min_value=0.0, max_value=1.0, value=0.98, step=0.1)

            # Find the nearest indices in the grid for the user's input
            pressure_idx = (np.abs(np.linspace(0, 40, 1000) - user_pressure)).argmin()
            mass_frac_idx = (np.abs(ammonia_mass_fraction_range - user_mass_fraction)).argmin()

            # Get the corresponding temperature for dew point and bubble point
            dew_point_slice = np.abs(dew_point_pressure_grid[:, mass_frac_idx] - user_pressure)
            if np.all(np.isnan(dew_point_slice)):
                dew_point_temperature = np.nan
            else:
                dew_point_temperature = temperature_range[np.nanargmin(dew_point_slice)]

            bubble_point_slice = np.abs(bubble_point_pressure_grid[:, mass_frac_idx] - user_pressure)
            if np.all(np.isnan(bubble_point_slice)):
                bubble_point_temperature = np.nan
            else:
                bubble_point_temperature = temperature_range[np.nanargmin(bubble_point_slice)]

            # Check if the values are nan and print the results
            if np.isnan(dew_point_temperature):
                st.error("해당 압력과 암모니아 분율에 대한 이슬점 온도를 찾을 수 없어요.")
            else:
                st.write(f"해당 압력과 암모니아 분율에 대한 이슬점 온도는 {round(dew_point_temperature, 2)} K 이에요.")

            if np.isnan(bubble_point_temperature):
                st.error("해당 압력과 암모니아 분율에 대한 거품점 온도를 찾을 수 없어요.")
            else:
                st.write(f"해당 압력과 암모니아 분율에 대한 거품점 온도는 {round(bubble_point_temperature, 2)} K 이에요.")

        else:
            st.error("뭔가 잘못되었어요. 다시 시도해주세요.")

    else:
        st.error("뭔가 잘못되었어요. 다시 시도해주세요.")

else:
    st.error("뭔가 잘못되었어요. 다시 시도해주세요.")