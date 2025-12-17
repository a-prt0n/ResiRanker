import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Setup
st.set_page_config(page_title="Residency Ranker Pro", layout="wide", page_icon="🏥")

st.title("🏥 Residency Ranker")
st.markdown("Enter your programs and scores (1-5) below. Your rank list and charts update instantly.")

# 2. Define New Categories and Default Weights
# Re-organized to prioritize your most important factors
default_weights = {
    "Case Exposure": 25,
    "Resident Happiness": 15,
    "Salary:COL": 15,
    "Location Fit": 10,
    "Fellowship Match Strength": 10,
    "Schedule": 10,
    "Research Support": 5,
    "Faculty Culture/Feedback": 5,
    "Program Reputation": 5
}

# 3. Sidebar for Weight Adjustments
with st.sidebar:
    st.header("⚙️ 1. Set Your Priorities")
    st.info("Adjust the weights to reflect what matters most to you. The total determines the max possible score.")
    weights = {}
    for label, weight in default_weights.items():
        weights[label] = st.slider(label, 0, 40, weight)
    
    total_weight = sum(weights.values())
    st.metric("Total Possible Points", total_weight)

# 4. Interactive Data Entry
st.header("📝 2. Score Your Programs")
st.write("Click any cell to edit. Use the '+' at the bottom of the table to add new programs.")

# Initialize state with a blank template if empty
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame([
        {"Program": "Dream Hospital", **{k: 5 for k in default_weights.keys()}},
        {"Program": "Safety Hospital", **{k: 3 for k in default_weights.keys()}}
    ])

# The Interactive Table
edited_df = st.data_editor(
    st.session_state.data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Program": st.column_config.TextColumn("Program Name", help="Name of the hospital/program", width="medium"),
        **{k: st.column_config.NumberColumn(min_value=1, max_value=5, step=1, format="%d") 
           for k in default_weights.keys()}
    }
)

# 5. Calculation Logic
def calculate_rank(df, weights):
    if df.empty:
        return df
    
    # Calculate weighted score: (Rating / 5) * Weight
    scores = []
    for _, row in df.iterrows():
        total = 0
        for col, weight in weights.items():
            # If a cell is empty (None), treat as 0 or 3? Let's use 0 for accuracy.
            rating = row[col] if pd.notnull(row[col]) else 0
            total += (rating / 5) * weight
        scores.append(round(total, 2))
    
    df["Final Score"] = scores
    return df.sort_values("Final Score", ascending=False).reset_index(drop=True)

# 6. Results and Visualization
if not edited_df.empty and "Program" in edited_df.columns:
    ranked_df = calculate_rank(edited_df.copy(), weights)
    
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("🏆 Your Rank List")
        # Display the rank list
        display_df = ranked_df[["Program", "Final Score"]].copy()
        display_df.index += 1 # Rank starts at 1
        st.dataframe(display_df, use_container_width=True)

    with col2:
        st.subheader("📊 Score Distribution")
        fig = px.bar(
            ranked_df, 
            x="Program", 
            y="Final Score", 
            color="Final Score",
            color_continuous_scale="Teal",
            text_auto=True
        )
        fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # 7. Comparison Radar Map
    st.divider()
    st.subheader("🕸️ Program Profile Comparison")
    selected = st.multiselect("Select programs to compare visually:", ranked_df["Program"].unique())
    
    if selected:
        fig_radar = go.Figure()
        categories = list(default_weights.keys())
        
        for prog in selected:
            prog_row = ranked_df[ranked_df["Program"] == prog].iloc[0]
            values = [prog_row[c] for c in categories]
            values.append(values[0]) # Close the loop
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=prog
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True,
            margin=dict(l=80, r=80, t=40, b=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
else:

    st.warning("Please add at least one program and ensure the 'Program' column is filled out.")
