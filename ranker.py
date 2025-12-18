import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Config
st.set_page_config(page_title="Residency Ranker Pro", layout="wide", page_icon="🏥")

# 2. Initializing Categories
DEFAULT_CATS = [
    "Resident Happiness", "Case Exposure", "Schedule", 
    "Fellowship Match Strength", "Location Fit", "Faculty Culture/Feedback", 
    "Salary:COL", "Research Support", "Program Reputation"
]

# Initialize session state keys if they don't exist
if "categories" not in st.session_state:
    st.session_state.categories = DEFAULT_CATS.copy()

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame([
        {"Program": "Example Hospital", **{k: 3 for k in st.session_state.categories}}
    ])

# 3. Upload Logic (Placed BEFORE Sidebar to ensure categories sync)
st.title("🏥 Residency Ranker Pro")
st.header("📂 1. Load Your Data")

uploaded_file = st.file_uploader("Upload CSV to sync categories and scores", type="csv")

if uploaded_file:
    try:
        df_upload = pd.read_csv(uploaded_file).fillna(3)
        if "Program" in df_upload.columns:
            # Sync categories: ignore Program and Final Score
            st.session_state.categories = [c for c in df_upload.columns if c not in ["Program", "Final Score"]]
            st.session_state.data = df_upload
            st.success("Data synced! Check the sidebar for new weight sliders.")
        else:
            st.error("CSV missing 'Program' column.")
    except Exception as e:
        st.error(f"Error loading file: {e}")

# 4. Sidebar: Category & Weight Manager
with st.sidebar:
    st.header("⚙️ Category Manager")
    
    new_cat = st.text_input("Add a custom category:")
    if st.button("Add Category") and new_cat:
        if new_cat not in st.session_state.categories:
            st.session_state.categories.append(new_cat)
            st.rerun()

    to_remove = st.multiselect("Remove categories:", st.session_state.categories)
    if st.button("Remove Selected"):
        st.session_state.categories = [c for c in st.session_state.categories if c not in to_remove]
        st.rerun()

    st.divider()
    st.header("⚖️ Set Weights")
    
    weights = {}
    # This loop now pulls from the UPDATED session_state.categories
    for cat in st.session_state.categories:
        weights[cat] = st.slider(f"Weight: {cat}", 0, 50, 10, key=f"w_{cat}")

# 5. The Editor
st.header("📝 2. Score Programs")
cols_to_show = ["Program"] + st.session_state.categories

# Fill any new columns with 3
current_data = st.session_state.data.reindex(columns=cols_to_show).fillna(3)

edited_df = st.data_editor(
    current_data, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        cat: st.column_config.NumberColumn(default=3) for cat in st.session_state.categories
    }
)

# Keep the session state updated
st.session_state.data = edited_df

# Save Button
csv_bytes = edited_df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Save/Download CSV", data=csv_bytes, file_name="my_rankings.csv", mime="text/csv")

# 6. Calculation Logic
def get_rankings(df, w_dict):
    if df.empty: return df
    df_res = df.copy()
    total_scores = []
    
    for _, row in df_res.iterrows():
        s = 0
        for cat, weight in w_dict.items():
            val = row.get(cat, 3)
            # Handle manual empty entries
            if pd.isna(val) or val == "":
                val = 3
            s += (float(val) / 5) * weight
        total_scores.append(round(s, 2))
    
    df_res["Final Score"] = total_scores
    return df_res.sort_values("Final Score", ascending=False).reset_index(drop=True)

# 7. Visuals & Comparison
st.divider()
ranked_df = get_rankings(edited_df, weights)

if not ranked_df.empty:
    col_left, col_right = st.columns([1, 1.5])
    with col_left:
        st.subheader("🏆 Rank List")
        st.dataframe(ranked_df[["Program", "Final Score"]], use_container_width=True)

    with col_right:
        st.subheader("📊 Score Breakdown")
        fig = px.bar(ranked_df, x="Program", y="Final Score", color="Final Score", 
                     color_continuous_scale="Viridis", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    # Re-adding the Radar Comparison Map
    st.divider()
    st.subheader("🕸️ Program Comparison Map")
    st.info("Select multiple programs to see their profiles overlap.")
    
    selected_progs = st.multiselect("Select programs to compare:", options=ranked_df["Program"].unique())
    
    if selected_progs:
        fig_radar = go.Figure()
        
        # We use the current categories for the axes
        radar_cats = st.session_state.categories
        
        for prog in selected_progs:
            prog_data = ranked_df[ranked_df["Program"] == prog].iloc[0]
            values = [prog_data.get(c, 3) for c in radar_cats]
            values.append(values[0]) # Close the loop
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=radar_cats + [radar_cats[0]],
                fill='toself',
                name=prog
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 5])
            ),
            showlegend=True,
            height=600
        )
        st.plotly_chart(fig_radar, use_container_width=True)
