"""
Streamlit Dashboard for UFC Betting Engine
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from models.ensemble import EnsembleModel
from features.matchup_features import MatchupFeatureExtractor

# Page config
st.set_page_config(
    page_title="UFC Betting Engine",
    page_icon="🥊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        color: #d20a0a;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize components
@st.cache_resource
def init_components():
    db = DatabaseManager()
    model = EnsembleModel()
    try:
        model.load_models()
    except:
        st.warning("Models not trained yet. Please train models first.")
    return db, model

db, model = init_components()

# Sidebar
st.sidebar.title("🥊 UFC Betting Engine")
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Fighter Analysis", "Fight Predictions", "Backtest Results", "Model Performance"]
)

# Main content
if page == "Home":
    st.markdown('<div class="main-header">UFC Betting Engine</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ## Welcome to the UFC Betting Engine
    
    This advanced system uses machine learning and statistical analysis to predict UFC fight outcomes 
    and identify profitable betting opportunities.
    
    ### Features:
    - **Comprehensive Fighter Database**: Stats and fight history for all UFC fighters
    - **ML Models**: XGBoost, Random Forest, Neural Networks, and LLM analysis
    - **Feature Engineering**: 100+ predictive features including rolling stats and matchup analysis
    - **Backtesting**: Historical validation of betting strategies
    - **Edge Detection**: Compare predictions vs betting lines to find value bets
    
    ### Quick Start:
    1. Navigate to **Fighter Analysis** to explore fighter statistics
    2. Use **Fight Predictions** to get predictions for upcoming fights
    3. Review **Backtest Results** to see historical performance
    4. Check **Model Performance** for accuracy metrics
    """)
    
    # Database stats
    stats = db.get_stats_summary()
    
    st.subheader("📊 Database Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Fighters", f"{stats['fighters']:,}")
    with col2:
        st.metric("Events", f"{stats['events']:,}")
    with col3:
        st.metric("Fights", f"{stats['fights']:,}")
    with col4:
        st.metric("Predictions", f"{stats['predictions']:,}")

elif page == "Fighter Analysis":
    st.title("🥋 Fighter Analysis")
    
    session = db.get_session()
    
    # Get all fighters
    from database.schema import Fighter
    fighters = session.query(Fighter).order_by(Fighter.name).all()
    
    if fighters:
        fighter_names = [f.name for f in fighters]
        
        selected_fighter_name = st.selectbox("Select Fighter", fighter_names)
        
        # Find selected fighter
        selected_fighter = next((f for f in fighters if f.name == selected_fighter_name), None)
        
        if selected_fighter:
            # Display fighter info
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"{selected_fighter.name}")
                if selected_fighter.nickname:
                    st.markdown(f"*'{selected_fighter.nickname}'*")
                
                st.markdown(f"""
                **Record**: {selected_fighter.wins}-{selected_fighter.losses}-{selected_fighter.draws}
                
                **Physical Attributes:**
                - Height: {selected_fighter.height_cm} cm
                - Weight: {selected_fighter.weight_lbs} lbs
                - Reach: {selected_fighter.reach_inches} inches
                - Stance: {selected_fighter.stance}
                - Age: {selected_fighter.age}
                """)
            
            with col2:
                st.subheader("Career Statistics")
                
                # Win rate gauge
                total_fights = selected_fighter.wins + selected_fighter.losses + selected_fighter.draws
                win_rate = (selected_fighter.wins / total_fights * 100) if total_fights > 0 else 0
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = win_rate,
                    title = {'text': "Win Rate"},
                    gauge = {'axis': {'range': [None, 100]},
                            'bar': {'color': "darkred"},
                            'steps': [
                                {'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 100], 'color': "gray"}],
                            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 75}}))
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            # Striking stats
            st.subheader("Striking Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("SLpM", f"{selected_fighter.sig_strikes_landed_per_min:.2f}")
            with col2:
                st.metric("Str. Acc.", f"{selected_fighter.striking_accuracy*100:.1f}%")
            with col3:
                st.metric("SApM", f"{selected_fighter.sig_strikes_absorbed_per_min:.2f}")
            with col4:
                st.metric("Str. Def", f"{selected_fighter.striking_defense*100:.1f}%")
            
            # Grappling stats
            st.subheader("Grappling Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("TD Avg", f"{selected_fighter.takedown_avg_per_15min:.2f}")
            with col2:
                st.metric("TD Acc.", f"{selected_fighter.takedown_accuracy*100:.1f}%")
            with col3:
                st.metric("TD Def", f"{selected_fighter.takedown_defense*100:.1f}%")
            with col4:
                st.metric("Sub Avg", f"{selected_fighter.submission_avg_per_15min:.2f}")
    
    else:
        st.info("No fighters in database. Please run the scraper first.")
    
    session.close()

elif page == "Fight Predictions":
    st.title("🔮 Fight Predictions")
    
    st.markdown("""
    Select two fighters to get a prediction for their matchup.
    The model will analyze their statistics, fighting styles, and recent form to predict the outcome.
    """)
    
    session = db.get_session()
    
    from database.schema import Fighter
    fighters = session.query(Fighter).order_by(Fighter.name).all()
    
    if fighters:
        fighter_names = [f.name for f in fighters]
        
        col1, col2 = st.columns(2)
        
        with col1:
            fighter_1_name = st.selectbox("Fighter 1", fighter_names, key="f1")
        
        with col2:
            fighter_2_name = st.selectbox("Fighter 2", fighter_names, key="f2")
        
        if st.button("Generate Prediction", type="primary"):
            if fighter_1_name == fighter_2_name:
                st.error("Please select two different fighters!")
            else:
                with st.spinner("Analyzing matchup..."):
                    fighter_1 = next((f for f in fighters if f.name == fighter_1_name), None)
                    fighter_2 = next((f for f in fighters if f.name == fighter_2_name), None)
                    
                    try:
                        # Get prediction
                        result = model.predict_fight(fighter_1.id, fighter_2.id)
                        
                        # Display prediction
                        st.success("Prediction Complete!")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                f"{fighter_1_name} Win Probability",
                                f"{result['fighter_1_win_probability']:.1%}"
                            )
                        
                        with col2:
                            st.metric(
                                f"{fighter_2_name} Win Probability",
                                f"{result['fighter_2_win_probability']:.1%}"
                            )
                        
                        with col3:
                            st.metric(
                                "Confidence",
                                f"{result['confidence']:.1%}"
                            )
                        
                        # Visualization
                        fig = go.Figure(data=[
                            go.Bar(
                                x=[fighter_1_name, fighter_2_name],
                                y=[result['fighter_1_win_probability'], result['fighter_2_win_probability']],
                                marker_color=['#d20a0a', '#1f77b4']
                            )
                        ])
                        
                        fig.update_layout(
                            title="Win Probability",
                            yaxis_title="Probability",
                            yaxis_tickformat='.0%',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Winner announcement
                        if result['predicted_winner'] == 'fighter_1':
                            st.markdown(f"### Prediction: **{fighter_1_name}** to win")
                        else:
                            st.markdown(f"### Prediction: **{fighter_2_name}** to win")
                    
                    except Exception as e:
                        st.error(f"Error generating prediction: {e}")
                        st.info("Make sure models are trained and feature pipeline is configured.")
    else:
        st.info("No fighters in database. Please run the scraper first.")
    
    session.close()

elif page == "Backtest Results":
    st.title("📈 Backtest Results")
    
    st.markdown("""
    Historical performance of the betting strategy on past fights.
    """)
    
    # Look for backtest results
    results_dir = Path('data/predictions')
    
    if results_dir.exists():
        result_files = list(results_dir.glob('backtest_results_*.csv'))
        
        if result_files:
            # Load most recent
            latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
            
            df = pd.read_csv(latest_file)
            
            st.subheader(f"Results from: {latest_file.name}")
            
            # Summary metrics
            bets_df = df[df['bet_placed']]
            
            if len(bets_df) > 0:
                initial_bankroll = df['bankroll'].iloc[0] - df['profit_loss'].iloc[0]
                final_bankroll = df['bankroll'].iloc[-1]
                total_profit = final_bankroll - initial_bankroll
                roi = (total_profit / initial_bankroll) * 100
                
                wins = len(bets_df[bets_df['profit_loss'] > 0])
                losses = len(bets_df) - wins
                win_rate = wins / len(bets_df) * 100
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Profit", f"${total_profit:,.2f}")
                with col2:
                    st.metric("ROI", f"{roi:.2f}%")
                with col3:
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                with col4:
                    st.metric("Total Bets", len(bets_df))
                
                # Bankroll over time
                fig = px.line(df, x=df.index, y='bankroll', title='Bankroll Over Time')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Profit distribution
                fig = px.histogram(bets_df, x='profit_loss', title='Profit/Loss Distribution',
                                 nbins=30, color_discrete_sequence=['#d20a0a'])
                st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No backtest results found. Run a backtest first.")
    else:
        st.info("No results directory found.")

elif page == "Model Performance":
    st.title("🎯 Model Performance")
    
    st.markdown("""
    Evaluation metrics for the prediction models.
    """)
    
    # Look for metrics file
    metrics_file = Path('models/saved/baseline_metrics.csv')
    
    if metrics_file.exists():
        df = pd.read_csv(metrics_file)
        
        st.subheader("Model Comparison")
        
        # Display metrics table
        st.dataframe(df, use_container_width=True)
        
        # Visualize metrics
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['model_name'],
            y=df['accuracy'],
            name='Accuracy',
            marker_color='#d20a0a'
        ))
        
        fig.add_trace(go.Bar(
            x=df['model_name'],
            y=df['roc_auc'],
            name='ROC AUC',
            marker_color='#1f77b4'
        ))
        
        fig.update_layout(
            title="Model Performance Comparison",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("No model metrics found. Train models first.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
UFC Betting Engine v1.0

Built with:
- Python
- Streamlit
- XGBoost
- PyTorch
- scikit-learn

**Disclaimer**: For educational purposes only.
Gamble responsibly.
""")

