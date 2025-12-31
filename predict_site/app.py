#!/usr/bin/env python3
"""
UFC Prediction Web Interface

A simple Streamlit app for:
1. Uploading/pasting CSV files and running batch predictions
2. Comparing two fighters directly
"""

import sys
from pathlib import Path

# Add parent directory to path to import project modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from io import StringIO
from loguru import logger

# Import project modules (after adding PROJECT_ROOT to path)
from scripts.export_predictions_to_excel import add_model_predictions
from xgboost_predict import xgboost_predict

# Configure page
st.set_page_config(
    page_title="UFC Fight Predictions",
    page_icon="🥊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🥊 UFC Fight Predictions")
st.markdown("---")

# Sidebar for model selection
st.sidebar.header("Model Settings")
model_name = st.sidebar.selectbox(
    "Select Model",
    options=["xgboost_model_with_2025", "xgboost_model"],
    index=0,
    help="Choose which trained model to use for predictions"
)

use_symmetric = st.sidebar.checkbox(
    "Use Symmetric Mode",
    value=True,
    help="Average predictions from both fighter orders for more stable results"
)

# Main tabs
tab1, tab2 = st.tabs(["📊 Batch Predictions (CSV)", "⚔️ Fighter Comparison"])

# Tab 1: Batch Predictions
with tab1:
    st.header("Batch Predictions from CSV")
    st.markdown(
        """
        Upload a CSV file or paste CSV data with the following columns:
        - `event`: Event name (e.g., "UFC 325")
        - `fight_date`: Optional date
        - `fighter_1_name`: First fighter name
        - `fighter_2_name`: Second fighter name
        - `fighter_1_odds`: American odds (e.g., -172, 250)
        - `fighter_2_odds`: American odds (e.g., 147, -340)
        - `is_title_fight`: 0 or 1
        """
    )
    
    # Example CSV files
    example_files = {
        "UFC 325": "data/predictions/upcoming_fights_ufc325.csv",
        "UFC 324": "data/predictions/upcoming_fights_ufc324.csv",
        "UFC 323": "data/predictions/upcoming_fights_ufc323.csv",
        "Fight Night: Royval vs. Kape": "data/predictions/upcoming_fights_fight_night_royval_kape.csv",
    }
    
    # Initialize session state for selected example
    if "selected_example" not in st.session_state:
        st.session_state.selected_example = None
    
    st.markdown("### 📋 Example Files")
    example_cols = st.columns(len(example_files))
    
    for idx, (name, path) in enumerate(example_files.items()):
        with example_cols[idx]:
            if st.button(f"📄 {name}", key=f"example_{idx}", use_container_width=True):
                st.session_state.selected_example = path
                st.rerun()
    
    # CSV input methods
    input_method = st.radio(
        "Input Method",
        ["Use Example File", "Upload CSV File", "Paste CSV Data"],
        horizontal=True
    )
    
    csv_data = None
    
    if input_method == "Use Example File" or st.session_state.selected_example:
        # Use selected example or let user choose
        if st.session_state.selected_example:
            example_path = st.session_state.selected_example
        else:
            example_path = st.selectbox(
                "Select Example File",
                options=list(example_files.values()),
                format_func=lambda x: [k for k, v in example_files.items() if v == x][0]
            )
            st.session_state.selected_example = example_path
        
        example_file = Path(example_path)
        if example_file.exists():
            csv_data = example_file.read_text()
            st.success(f"✅ Loaded: {[k for k, v in example_files.items() if v == example_path][0]}")
            with st.expander("Preview Example File", expanded=False):
                st.dataframe(pd.read_csv(StringIO(csv_data)), use_container_width=True)
        else:
            st.warning(f"Example file not found: {example_path}")
            st.info("Make sure the file is committed to your repository for Streamlit Cloud deployment.")
    
    # Clear selection if switching to other input methods
    if input_method != "Use Example File":
        st.session_state.selected_example = None
    
    elif input_method == "Upload CSV File":
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            help="Upload a CSV file with fight data"
        )
        if uploaded_file is not None:
            csv_data = uploaded_file.read().decode('utf-8')
    
    else:  # Paste CSV Data
        csv_text = st.text_area(
            "Paste CSV data here",
            height=200,
            help="Paste CSV data including header row"
        )
        if csv_text:
            csv_data = csv_text
    
    if csv_data:
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(csv_data))
            
            # Validate required columns
            required_cols = [
                "fighter_1_name", "fighter_2_name",
                "fighter_1_odds", "fighter_2_odds"
            ]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}")
            else:
                st.success(f"✅ Loaded {len(df)} fights")
                
                # Show preview
                with st.expander("Preview Data", expanded=False):
                    st.dataframe(df, use_container_width=True)
                
                # Run predictions
                if st.button("🚀 Run Predictions", type="primary"):
                    with st.spinner("Running predictions... This may take a minute."):
                        try:
                            # Add model predictions
                            df_results = add_model_predictions(
                                df,
                                model_name=model_name,
                                symmetric=use_symmetric
                            )
                            
                            st.success("✅ Predictions complete!")
                            
                            # Display results
                            st.subheader("Prediction Results")
                            
                            # Calculate best fighter and best edge columns if not present
                            # (preview_upcoming_fights creates these, but add_model_predictions might not)
                            if "best_fighter" not in df_results.columns:
                                df_results["best_fighter"] = df_results.apply(
                                    lambda row: row["fighter_1_name"] if row.get("model_p_f1_pct", 0) > row.get("model_p_f2_pct", 0) 
                                    else row["fighter_2_name"], axis=1
                                )
                            
                            if "best_model_prob_pct" not in df_results.columns:
                                df_results["best_model_prob_pct"] = df_results.apply(
                                    lambda row: max(row.get("model_p_f1_pct", 0), row.get("model_p_f2_pct", 0)), axis=1
                                )
                            
                            if "best_market_prob_pct" not in df_results.columns:
                                df_results["best_market_prob_pct"] = df_results.apply(
                                    lambda row: max(row.get("implied_p_f1_pct", 0), row.get("implied_p_f2_pct", 0)), axis=1
                                )
                            
                            if "best_edge_pct" not in df_results.columns:
                                df_results["best_edge_pct"] = df_results.apply(
                                    lambda row: max(row.get("edge_f1_pct", 0), row.get("edge_f2_pct", 0)), axis=1
                                )
                            
                            # Create styled summary table
                            summary_cols = [
                                "event", "fight_date",
                                "fighter_1_name", "fighter_2_name",
                                "best_fighter",
                                "best_model_prob_pct", "best_market_prob_pct", "best_edge_pct",
                                "risk_notes"
                            ]
                            available_summary_cols = [col for col in summary_cols if col in df_results.columns]
                            
                            # Display with highlighting
                            df_display = df_results[available_summary_cols].copy()
                            
                            # Create a styled dataframe with highlighted best_fighter
                            def style_row(row):
                                styles = [''] * len(row)
                                if 'best_fighter' in df_display.columns:
                                    best_fighter_idx = df_display.columns.get_loc('best_fighter')
                                    styles[best_fighter_idx] = 'background-color: #fff3cd; font-weight: bold; color: #856404; font-size: 1.1em;'
                                # Also highlight best_edge_pct if positive
                                if 'best_edge_pct' in df_display.columns:
                                    edge_idx = df_display.columns.get_loc('best_edge_pct')
                                    edge_val = row.iloc[edge_idx] if edge_idx < len(row) else 0
                                    if edge_val > 10:
                                        styles[edge_idx] = 'background-color: #d4edda; font-weight: bold; color: #155724;'
                                    elif edge_val > 0:
                                        styles[edge_idx] = 'background-color: #fff3cd; font-weight: bold;'
                                return styles
                            
                            # Apply styling
                            styled_df = df_display.style.apply(style_row, axis=1)
                            
                            st.dataframe(
                                styled_df,
                                use_container_width=True,
                                height=400
                            )
                            
                            # Also show a cleaner summary table
                            st.markdown("---")
                            st.subheader("📊 Summary by Edge")
                            
                            # Sort by best_edge_pct descending
                            df_sorted = df_display.sort_values("best_edge_pct", ascending=False)
                            
                            # Create a more readable summary
                            for idx, row in df_sorted.iterrows():
                                fighter_1 = row.get("fighter_1_name", "N/A")
                                fighter_2 = row.get("fighter_2_name", "N/A")
                                best_fighter = row.get("best_fighter", "N/A")
                                model_prob = row.get("best_model_prob_pct", 0)
                                market_prob = row.get("best_market_prob_pct", 0)
                                edge = row.get("best_edge_pct", 0)
                                risk_notes = row.get("risk_notes", "")
                                
                                # Determine if this is a strong edge
                                is_strong_edge = edge > 10
                                border_color = "#28a745" if is_strong_edge else "#6c757d"
                                bg_color = "#d4edda" if is_strong_edge else "#f8f9fa"
                                
                                risk_html = ""
                                if risk_notes:
                                    risk_html = f'<p style="margin: 5px 0; color: #856404;"><strong>⚠️ Note:</strong> {risk_notes}</p>'
                                
                                st.markdown(f"""
                                <div style="padding: 15px; margin: 10px 0; border: 2px solid {border_color}; border-radius: 8px; background-color: {bg_color};">
                                    <h4 style="margin: 0 0 10px 0; color: {border_color};">
                                        {fighter_1} vs {fighter_2}
                                    </h4>
                                    <p style="margin: 5px 0;">
                                        <strong>🏆 Predicted Winner:</strong> 
                                        <span style="background-color: #fff3cd; padding: 3px 8px; border-radius: 4px; font-weight: bold;">
                                            {best_fighter}
                                        </span>
                                    </p>
                                    <div style="display: flex; gap: 20px; margin-top: 10px;">
                                        <div>
                                            <strong>Model:</strong> {model_prob:.1f}%
                                        </div>
                                        <div>
                                            <strong>Market:</strong> {market_prob:.1f}%
                                        </div>
                                        <div>
                                            <strong>Edge:</strong> <span style="color: {'#28a745' if edge > 0 else '#dc3545'}; font-weight: bold;">{edge:+.1f}%</span>
                                        </div>
                                    </div>
                                    {risk_html}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Download button
                            csv_output = df_results.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results CSV",
                                data=csv_output,
                                file_name=f"predictions_{model_name}.csv",
                                mime="text/csv"
                            )
                        
                        except Exception as e:
                            st.error(f"Error running predictions: {str(e)}")
                            logger.exception("Prediction error")
        
        except Exception as e:
            st.error(f"Error parsing CSV: {str(e)}")
            logger.exception("CSV parsing error")

# Tab 2: Fighter Comparison
with tab2:
    st.header("Compare Two Fighters")
    st.markdown("Search for fighters by name. Matching fighters will appear as you type.")
    
    # Initialize database connection for fighter search
    @st.cache_resource
    def get_db():
        from database.db_manager import DatabaseManager
        return DatabaseManager()
    
    db = get_db()
    
    def search_fighters(query: str, limit: int = 20):
        """Search for fighters matching the query."""
        if not query or len(query) < 2:
            return []
        
        from database.schema import Fighter, Fight
        from sqlalchemy import or_
        
        session = db.get_session()
        try:
            # Search by name (case-insensitive)
            fighters = session.query(Fighter).filter(
                Fighter.name.ilike(f"%{query}%")
            ).limit(limit).all()
            
            # Get fight counts for each fighter
            results = []
            for fighter in fighters:
                fight_count = session.query(Fight).filter(
                    or_(Fight.fighter_1_id == fighter.id, Fight.fighter_2_id == fighter.id)
                ).count()
                
                record = f"{fighter.wins or 0}-{fighter.losses or 0}-{fighter.draws or 0}"
                results.append({
                    'id': fighter.id,
                    'name': fighter.name,
                    'nickname': fighter.nickname or '',
                    'record': record,
                    'ufcstats_id': fighter.fighter_id,
                    'age': fighter.age,
                    'fight_count': fight_count
                })
            
            # Sort by fight count (most active first), then by name
            results.sort(key=lambda x: (-x['fight_count'], x['name']))
            return results
        finally:
            session.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Fighter 1")
        fighter_1_query = st.text_input(
            "Search Fighter 1",
            value="",
            key="fighter_1_search",
            help="Type to search for a fighter (e.g., 'Arn' for Arnold)"
        )
        
        fighter_1_id = None
        fighter_1_name = None
        
        if fighter_1_query:
            matches = search_fighters(fighter_1_query)
            
            if matches:
                # Create display strings for selectbox
                fighter_options = []
                for f in matches:
                    display = f"{f['name']}"
                    if f['nickname']:
                        display += f" '{f['nickname']}'"
                    display += f" (ID: {f['id']}, Record: {f['record']}"
                    if f['fight_count'] > 0:
                        display += f", {f['fight_count']} fights"
                    display += ")"
                    fighter_options.append((f['id'], display, f['name']))
                
                if len(matches) == 1:
                    # Auto-select if only one match
                    selected = fighter_options[0]
                    fighter_1_id = selected[0]
                    fighter_1_name = selected[2]
                    st.info(f"✅ Found: {selected[1]}")
                else:
                    # Show selectbox for multiple matches
                    selected_display = st.selectbox(
                        "Select Fighter 1",
                        options=[opt[1] for opt in fighter_options],
                        key="fighter_1_select",
                        help=f"Found {len(matches)} matches. Select the correct fighter."
                    )
                    
                    # Find selected fighter
                    for opt in fighter_options:
                        if opt[1] == selected_display:
                            fighter_1_id = opt[0]
                            fighter_1_name = opt[2]
                            break
            else:
                st.warning(f"No fighters found matching '{fighter_1_query}'")
        
        # Manual ID override
        manual_id_1 = st.number_input(
            "Or enter Fighter 1 ID manually",
            min_value=0,
            value=0,
            key="fighter_1_manual_id",
            help="Override with specific fighter ID"
        )
        if manual_id_1 > 0:
            fighter_1_id = int(manual_id_1)
            # Look up name
            from database.schema import Fighter
            session = db.get_session()
            try:
                f = session.query(Fighter).filter(Fighter.id == fighter_1_id).first()
                if f:
                    fighter_1_name = f.name
                    st.success(f"✅ Fighter: {f.name} (Record: {f.wins}-{f.losses}-{f.draws})")
                else:
                    st.error(f"Fighter ID {fighter_1_id} not found")
            finally:
                session.close()
    
    with col2:
        st.subheader("Fighter 2")
        fighter_2_query = st.text_input(
            "Search Fighter 2",
            value="",
            key="fighter_2_search",
            help="Type to search for a fighter (e.g., 'Arn' for Arnold)"
        )
        
        fighter_2_id = None
        fighter_2_name = None
        
        if fighter_2_query:
            matches = search_fighters(fighter_2_query)
            
            if matches:
                # Create display strings for selectbox
                fighter_options = []
                for f in matches:
                    display = f"{f['name']}"
                    if f['nickname']:
                        display += f" '{f['nickname']}'"
                    display += f" (ID: {f['id']}, Record: {f['record']}"
                    if f['fight_count'] > 0:
                        display += f", {f['fight_count']} fights"
                    display += ")"
                    fighter_options.append((f['id'], display, f['name']))
                
                if len(matches) == 1:
                    # Auto-select if only one match
                    selected = fighter_options[0]
                    fighter_2_id = selected[0]
                    fighter_2_name = selected[2]
                    st.info(f"✅ Found: {selected[1]}")
                else:
                    # Show selectbox for multiple matches
                    selected_display = st.selectbox(
                        "Select Fighter 2",
                        options=[opt[1] for opt in fighter_options],
                        key="fighter_2_select",
                        help=f"Found {len(matches)} matches. Select the correct fighter."
                    )
                    
                    # Find selected fighter
                    for opt in fighter_options:
                        if opt[1] == selected_display:
                            fighter_2_id = opt[0]
                            fighter_2_name = opt[2]
                            break
            else:
                st.warning(f"No fighters found matching '{fighter_2_query}'")
        
        # Manual ID override
        manual_id_2 = st.number_input(
            "Or enter Fighter 2 ID manually",
            min_value=0,
            value=0,
            key="fighter_2_manual_id",
            help="Override with specific fighter ID"
        )
        if manual_id_2 > 0:
            fighter_2_id = int(manual_id_2)
            # Look up name
            from database.schema import Fighter
            session = db.get_session()
            try:
                f = session.query(Fighter).filter(Fighter.id == fighter_2_id).first()
                if f:
                    fighter_2_name = f.name
                    st.success(f"✅ Fighter: {f.name} (Record: {f.wins}-{f.losses}-{f.draws})")
                else:
                    st.error(f"Fighter ID {fighter_2_id} not found")
            finally:
                session.close()
    
    is_title_fight = st.checkbox("Title Fight (5 rounds)", value=False)
    
    # Use the selected names or fall back to queries if names weren't selected
    fighter_1 = fighter_1_name if fighter_1_name else (fighter_1_query if fighter_1_query else "")
    fighter_2 = fighter_2_name if fighter_2_name else (fighter_2_query if fighter_2_query else "")
    
    if st.button("🥊 Predict Fight", type="primary"):
        if not fighter_1 or not fighter_2:
            st.warning("Please search and select both fighters")
        elif not fighter_1_id and not fighter_1_name:
            st.warning("Please select Fighter 1 from the search results")
        elif not fighter_2_id and not fighter_2_name:
            st.warning("Please select Fighter 2 from the search results")
        else:
            with st.spinner("Running prediction... This may take a moment."):
                try:
                    # Capture output from xgboost_predict
                    import io
                    import re
                    from contextlib import redirect_stdout, redirect_stderr
                    
                    output_buffer = io.StringIO()
                    error_buffer = io.StringIO()
                    
                    with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                        xgboost_predict(
                            fighter_1_name=fighter_1,
                            fighter_2_name=fighter_2,
                            title_fight=is_title_fight,
                            quiet=False,
                            model_name=model_name,
                            fighter_1_id=fighter_1_id,
                            fighter_2_id=fighter_2_id,
                            allow_ambiguous=True,
                            symmetric=use_symmetric,
                        )
                    
                    output = output_buffer.getvalue()
                    errors = error_buffer.getvalue()
                    
                    if errors:
                        st.warning(f"Warnings: {errors}")
                    
                    # Parse the output to extract key information
                    # Extract prediction percentages
                    prob_pattern = r'(\w+(?:\s+\w+)*):\s+(\d+\.\d+)% chance to win'
                    probabilities = re.findall(prob_pattern, output)
                    
                    # Extract predicted winner
                    winner_pattern = r'⭐ Predicted Winner:\s+(.+)'
                    winner_match = re.search(winner_pattern, output)
                    predicted_winner = winner_match.group(1).strip() if winner_match else None
                    
                    # Extract fight type
                    fight_type_pattern = r'Fight Type:\s+(.+)'
                    fight_type_match = re.search(fight_type_pattern, output)
                    fight_type = fight_type_match.group(1).strip() if fight_type_match else "Unknown"
                    
                    # Display main prediction in a nice format
                    st.markdown("---")
                    st.markdown("### 🥊 Prediction Results")
                    
                    # Create columns for fighter probabilities
                    col1, col2 = st.columns(2)
                    
                    f1_prob = None
                    f2_prob = None
                    f1_name_display = fighter_1
                    f2_name_display = fighter_2
                    
                    for name, prob in probabilities:
                        prob_float = float(prob)
                        if name.strip() == fighter_1 or name.strip() in fighter_1:
                            f1_prob = prob_float
                            f1_name_display = name.strip()
                        elif name.strip() == fighter_2 or name.strip() in fighter_2:
                            f2_prob = prob_float
                            f2_name_display = name.strip()
                    
                    # Display fighter 1
                    with col1:
                        is_winner_1 = predicted_winner and (f1_name_display in predicted_winner or predicted_winner in f1_name_display)
                        winner_badge = " 🏆 WINNER" if is_winner_1 else ""
                        color = "#28a745" if is_winner_1 else "#6c757d"
                        
                        st.markdown(f"""
                        <div style="text-align: center; padding: 20px; border: 2px solid {color}; border-radius: 10px; background-color: {'#d4edda' if is_winner_1 else '#f8f9fa'};">
                            <h2 style="color: {color}; margin-bottom: 10px;">{f1_name_display}{winner_badge}</h2>
                            <h1 style="color: {color}; font-size: 48px; margin: 10px 0;">{f1_prob:.1f}%</h1>
                            <p style="color: #666;">Win Probability</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Display fighter 2
                    with col2:
                        is_winner_2 = predicted_winner and (f2_name_display in predicted_winner or predicted_winner in f2_name_display)
                        winner_badge = " 🏆 WINNER" if is_winner_2 else ""
                        color = "#28a745" if is_winner_2 else "#6c757d"
                        
                        st.markdown(f"""
                        <div style="text-align: center; padding: 20px; border: 2px solid {color}; border-radius: 10px; background-color: {'#d4edda' if is_winner_2 else '#f8f9fa'};">
                            <h2 style="color: {color}; margin-bottom: 10px;">{f2_name_display}{winner_badge}</h2>
                            <h1 style="color: {color}; font-size: 48px; margin: 10px 0;">{f2_prob:.1f}%</h1>
                            <p style="color: #666;">Win Probability</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Fight type
                    st.markdown(f"**Fight Type:** {fight_type}")
                    
                    # Extract top features
                    top_features_pattern = r'Top \d+ Most Important Features in Model:\s*\n((?:\s+\d+\.\s+[^\n]+\n?)+)'
                    top_features_match = re.search(top_features_pattern, output)
                    
                    if top_features_match:
                        st.markdown("---")
                        st.markdown("### 📊 Top Features")
                        features_text = top_features_match.group(1)
                        # Clean up the features list
                        features_list = [line.strip() for line in features_text.split('\n') if line.strip() and '.' in line]
                        for feature in features_list[:5]:  # Show top 5
                            # Remove the number prefix
                            feature_clean = re.sub(r'^\s*\d+\.\s*', '', feature)
                            st.markdown(f"- **{feature_clean}**")
                    
                    # Extract feature contribution analysis
                    contribution_pattern = r'\[FEATURE CONTRIBUTION ANALYSIS\](.*?)(?=\n\n|\Z)'
                    contribution_match = re.search(contribution_pattern, output, re.DOTALL)
                    
                    if contribution_match:
                        st.markdown("---")
                        st.markdown("### 🔍 Feature Analysis")
                        contribution_text = contribution_match.group(1)
                        
                        # Extract features favoring each fighter - use the actual names from output
                        # Look for "Top 3 favoring [name]:" pattern
                        f1_favors_pattern = rf'Top 3 favoring {re.escape(f1_name_display)}:\s*\n((?:.*\n)*?)(?=\n\s*Top 3 favoring|\n\s*\[|\Z)'
                        f1_favors_match = re.search(f1_favors_pattern, contribution_text, re.DOTALL)
                        
                        f2_favors_pattern = rf'Top 3 favoring {re.escape(f2_name_display)}:\s*\n((?:.*\n)*?)(?=\n\s*\[|\Z)'
                        f2_favors_match = re.search(f2_favors_pattern, contribution_text, re.DOTALL)
                        
                        col_f1, col_f2 = st.columns(2)
                        
                        with col_f1:
                            st.markdown(f"**Favoring {f1_name_display}:**")
                            if f1_favors_match:
                                favors_text = f1_favors_match.group(1)
                                favors_lines = [line.strip() for line in favors_text.split('\n') if line.strip() and ':' in line]
                                for line in favors_lines[:3]:
                                    # Format: feature_name: value (description)
                                    parts = line.split(':')
                                    if len(parts) >= 2:
                                        feature = parts[0].strip()
                                        rest = ':'.join(parts[1:]).strip()
                                        st.markdown(f"  • **{feature}**: {rest}")
                        
                        with col_f2:
                            st.markdown(f"**Favoring {f2_name_display}:**")
                            if f2_favors_match:
                                favors_text = f2_favors_match.group(1)
                                favors_lines = [line.strip() for line in favors_text.split('\n') if line.strip() and ':' in line]
                                for line in favors_lines[:3]:
                                    # Format: feature_name: value (description)
                                    parts = line.split(':')
                                    if len(parts) >= 2:
                                        feature = parts[0].strip()
                                        rest = ':'.join(parts[1:]).strip()
                                        st.markdown(f"  • **{feature}**: {rest}")
                    
                    # Full output in expandable section
                    with st.expander("📋 Full Prediction Details (Debug Output)", expanded=False):
                        st.code(output, language=None)
                
                except Exception as e:
                    st.error(f"Error running prediction: {str(e)}")
                    logger.exception("Fighter comparison error")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        UFC Analysis v2 - Prediction Interface
    </div>
    """,
    unsafe_allow_html=True
)

