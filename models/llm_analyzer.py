"""
LLM-based Fight Analyzer - Uses GPT-4 or Claude for qualitative analysis
"""

import os
import json
from typing import Dict, Optional
import yaml
from loguru import logger
from openai import OpenAI
from anthropic import Anthropic

from database.db_manager import DatabaseManager
from database.schema import Fighter, Fight


class LLMFightAnalyzer:
    """Use LLMs to analyze fights qualitatively"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize LLM analyzer"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.llm_config = self.config['llm']
        self.provider = self.llm_config['provider']
        
        # Initialize API clients
        if self.provider == 'openai':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        elif self.provider == 'anthropic':
            self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        self.db = DatabaseManager(config_path)
        logger.info(f"Initialized LLM analyzer with {self.provider}")
    
    def analyze_fight(self, fighter_1_id: int, fighter_2_id: int) -> Dict:
        """
        Analyze a fight matchup using LLM
        
        Args:
            fighter_1_id: First fighter database ID
            fighter_2_id: Second fighter database ID
            
        Returns:
            Dictionary with analysis and predictions
        """
        session = self.db.get_session()
        
        try:
            # Get fighter data
            fighter_1 = session.query(Fighter).filter_by(id=fighter_1_id).first()
            fighter_2 = session.query(Fighter).filter_by(id=fighter_2_id).first()
            
            if not fighter_1 or not fighter_2:
                logger.error("One or both fighters not found")
                return None
            
            # Build prompt
            prompt = self._build_analysis_prompt(fighter_1, fighter_2)
            
            # Get LLM response
            response = self._call_llm(prompt)
            
            # Parse response
            analysis = self._parse_llm_response(response)
            
            logger.success(f"Completed LLM analysis for {fighter_1.name} vs {fighter_2.name}")
            
            return analysis
            
        finally:
            session.close()
    
    def _build_analysis_prompt(self, fighter_1: Fighter, fighter_2: Fighter) -> str:
        """Build the prompt for LLM analysis"""
        
        # Fighter 1 stats
        f1_stats = f"""
Fighter A: {fighter_1.name}
- Record: {fighter_1.wins}-{fighter_1.losses}-{fighter_1.draws}
- Height: {fighter_1.height_cm}cm, Reach: {fighter_1.reach_inches}"
- Age: {fighter_1.age}
- Stance: {fighter_1.stance}
- Striking: {fighter_1.sig_strikes_landed_per_min:.2f} SLpM, {fighter_1.striking_accuracy*100:.1f}% accuracy
- Defense: {fighter_1.striking_defense*100:.1f}% striking defense, {fighter_1.takedown_defense*100:.1f}% TD defense
- Grappling: {fighter_1.takedown_avg_per_15min:.2f} TD avg, {fighter_1.submission_avg_per_15min:.2f} sub avg
"""
        
        # Fighter 2 stats
        f2_stats = f"""
Fighter B: {fighter_2.name}
- Record: {fighter_2.wins}-{fighter_2.losses}-{fighter_2.draws}
- Height: {fighter_2.height_cm}cm, Reach: {fighter_2.reach_inches}"
- Age: {fighter_2.age}
- Stance: {fighter_2.stance}
- Striking: {fighter_2.sig_strikes_landed_per_min:.2f} SLpM, {fighter_2.striking_accuracy*100:.1f}% accuracy
- Defense: {fighter_2.striking_defense*100:.1f}% striking defense, {fighter_2.takedown_defense*100:.1f}% TD defense
- Grappling: {fighter_2.takedown_avg_per_15min:.2f} TD avg, {fighter_2.submission_avg_per_15min:.2f} sub avg
"""
        
        prompt = self.llm_config['analysis_prompt'].format(
            fighter_a_stats=f1_stats,
            fighter_b_stats=f2_stats,
            recent_form="(Recent form data would go here)",
            style_analysis="(Style matchup analysis would go here)"
        )
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API"""
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.llm_config['model'],
                    messages=[
                        {"role": "system", "content": "You are an expert UFC analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.llm_config['temperature'],
                    max_tokens=self.llm_config['max_tokens']
                )
                return response.choices[0].message.content
            
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.llm_config['model'],
                    max_tokens=self.llm_config['max_tokens'],
                    temperature=self.llm_config['temperature'],
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse the LLM response into structured data"""
        # This is a simplified parser
        # In production, you'd want more robust parsing
        
        analysis = {
            'raw_analysis': response,
            'fighter_1_win_probability': 0.5,  # Default
            'fighter_2_win_probability': 0.5,
            'confidence': 5,  # Default medium confidence
            'predicted_method': 'Decision',
            'key_factors': []
        }
        
        # Try to extract probability from response
        # This would need to be more sophisticated in production
        if 'fighter a' in response.lower() and 'probability' in response.lower():
            # Extract probability estimates
            pass
        
        return analysis


def main():
    """Main function for testing LLM analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze fights with LLM')
    parser.add_argument('--fighter-1', type=int, required=True,
                       help='First fighter ID')
    parser.add_argument('--fighter-2', type=int, required=True,
                       help='Second fighter ID')
    
    args = parser.parse_args()
    
    analyzer = LLMFightAnalyzer()
    analysis = analyzer.analyze_fight(args.fighter_1, args.fighter_2)
    
    if analysis:
        print("\n" + "="*80)
        print("LLM FIGHT ANALYSIS")
        print("="*80)
        print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    main()

