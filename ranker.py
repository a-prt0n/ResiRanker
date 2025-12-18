import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="ResiRanker", layout="wide", page_icon="🏥")

# 2. Initialize Session State
# This ensures your data persists even when the script reruns
DEFAULT_CATS = [
    "Resident Happiness", "Case Exposure", "Schedule", 
    "Fellowship Match Strength", "Location Fit", "Faculty Culture/Feedback", 
    "Salary:COL", "Research Support", "Program Reputation"
]

if "categories" not in st.session_state:
    st.session_state.categories = DEFAULT_CATS.copy()

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame([
        {"Program": "Example Hospital", **{k: 3 for k in st.session_state.categories}}
    ])

# 3. Handle File Upload (Only update if a NEW file is detected)
st.title("🏥 Residency Ranker")
st.header("📂 1. Load Your Data")

uploaded_file = st.file_uploader("Upload a CSV to sync categories and scores", type="csv")

# We track the last uploaded file name to prevent it from resetting manual changes on every rerun
if uploaded_file:
    file_key = f"processed_{uploaded_file.name}"
    if file_key not in st.session_state:
        try:
            df_upload = pd.read_csv(uploaded_file).fillna(3)
            if "Program" in df_upload.columns:
                # Sync logic
                new_cats = [c for c in df_upload.columns if c not in ["Program", "Final Score"]]
                st.session_state.categories = new_cats
                st.session_state.data = df_upload
                st.session_state[file_key] = True # Mark this file as processed
                st.success(f"Successfully synced {len(new_cats)} categories!")
                st.rerun() # Force refresh to show new sliders
            else:
                st.error("CSV must contain a 'Program' column.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# 4. Sidebar: Category & Weight Management
with st.sidebar:
    st.header("⚙️ Category Manager")
    
    # ADD CATEGORY
    new_cat = st.text_input("New category name:", key="new_cat_input")
    if st.button("➕ Add Category"):
        if new_cat and new_cat not in st.session_state.categories:
            st.session_state.categories.append(new_cat)
            # Add the column to the existing data with default 3
            st.session_state.data[new_cat] = 3
            st.rerun()

    # REMOVE CATEGORY
    st.divider()
    to_remove = st.multiselect("Select categories to delete:", st.session_state.categories)
    if st.button("🗑️ Remove Selected"):
        if to_remove:
            # Update the list
            st.session_state.categories = [c for c in st.session_state.categories if c not in to_remove]
            # Physically drop columns from the data
            st.session_state.data = st.session_state.data.drop(columns=to_remove, errors='ignore')
            st.rerun()

    st.divider()
    st.header("⚖️ Set Weights")
    weights = {}
    for cat in st.session_state.categories:
        weights[cat] = st.slider(f"{cat}", 0, 50, 10, key=f"slider_{cat}")

# 5. The Editor
st.header("📝 2. Score Your Programs")

# Ensure the editor is showing the correct columns based on the current session state
display_cols = ["Program"] + st.session_state.categories
# Fill in any gaps that might have appeared
current_df = st.session_state.data.reindex(columns=display_cols).fillna(3)

# The editor returns a new dataframe every time a cell is changed
edited_df = st.data_editor(
    current_df,
    num_rows="dynamic",
    use_container_width=True,
    key="main_editor"
)

# Crucial: Update the session state data so calculations use the latest edits
st.session_state.data = edited_df

# Save/Download
csv_bytes = edited_df.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Download/Save CSV", 
    data=csv_bytes, 
    file_name="my_residency_rankings.csv", 
    mime="text/csv"
)

# 6. Rankings & Visuals
def calculate_scores(df, w_dict):
    if df.empty: return df
    d = df.copy()
    results = []
    for _, row in d.iterrows():
        s = 0
        for cat, weight in w_dict.items():
            val = row.get(cat, 3)
            # Handle empty strings or NaNs from the editor
            try:
                val_num = float(val) if pd.notnull(val) and val != "" else 3.0
            except:
                val_num = 3.0
            s += (val_num / 5) * weight
        results.append(round(s, 2))
    d["Final Score"] = results
    return d.sort_values("Final Score", ascending=False).reset_index(drop=True)

st.divider()
ranked_df = calculate_scores(edited_df, weights)

if not ranked_df.empty:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("🏆 Your Rank List")
        out = ranked_df[["Program", "Final Score"]].copy()
        out.index += 1
        st.dataframe(out, use_container_width=True)

    with c2:
        st.subheader("📊 Score Distribution")
        fig = px.bar(ranked_df, x="Program", y="Final Score", color="Final Score", color_continuous_scale="Viridis", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    # Radar Comparison
    st.divider()
    st.subheader("🕸️ Program Comparison")
    selected = st.multiselect("Compare these programs:", ranked_df["Program"].unique())
    if selected:
        fig_radar = go.Figure()
        cats = st.session_state.categories
        for p in selected:
            row = ranked_df[ranked_df["Program"] == p].iloc[0]
            vals = [row.get(c, 3) for c in cats]
            vals.append(vals[0])
            fig_radar.add_trace(go.Scatterpolar(r=vals, theta=cats + [cats[0]], fill='toself', name=p))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True)
        st.plotly_chart(fig_radar, use_container_width=True)
