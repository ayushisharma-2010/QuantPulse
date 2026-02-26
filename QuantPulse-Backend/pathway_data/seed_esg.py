"""
ESG Data Seeding Script for Pathway Pipeline
============================================

This script generates realistic ESG (Environmental, Social, Governance) data
and writes it as JSON files to the pathway_data/esg/ directory.

Usage:
    python pathway_data/seed_esg.py
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ESGSeeder:
    """Seed ESG data for Pathway pipeline"""
    
    def __init__(self, output_dir: str):
        """
        Initialize ESG seeder
        
        Args:
            output_dir: Directory to write ESG JSON files
        """
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Stock symbols and company names
        self.companies = {
            'RELIANCE.NS': 'Reliance Industries Limited',
            'TCS.NS': 'Tata Consultancy Services',
            'INFY.NS': 'Infosys Limited',
            'HDFCBANK.NS': 'HDFC Bank Limited',
            'ICICIBANK.NS': 'ICICI Bank Limited',
            'HINDUNILVR.NS': 'Hindustan Unilever Limited',
            'ITC.NS': 'ITC Limited',
            'SBIN.NS': 'State Bank of India',
            'BHARTIARTL.NS': 'Bharti Airtel Limited',
            'KOTAKBANK.NS': 'Kotak Mahindra Bank Limited',
            'LT.NS': 'Larsen & Toubro Limited',
            'AXISBANK.NS': 'Axis Bank Limited',
            'MARUTI.NS': 'Maruti Suzuki India Limited',
            'SUNPHARMA.NS': 'Sun Pharmaceutical Industries',
            'TITAN.NS': 'Titan Company Limited',
            'WIPRO.NS': 'Wipro Limited',
            'HCLTECH.NS': 'HCL Technologies Limited',
            'BAJFINANCE.NS': 'Bajaj Finance Limited',
            'ASIANPAINT.NS': 'Asian Paints Limited',
            'ULTRACEMCO.NS': 'UltraTech Cement Limited'
        }
        
        print(f"ESGSeeder initialized")
        print(f"Output directory: {output_dir}")
        print(f"Companies: {len(self.companies)}")
    
    def generate_esg_data(self, symbol: str, company_name: str) -> Dict[str, Any]:
        """
        Generate realistic ESG data for a company
        
        Args:
            symbol: Stock symbol
            company_name: Company name
            
        Returns:
            ESG data dictionary
        """
        # Base scores with some variation
        base_score = random.uniform(50, 85)
        
        # Environmental metrics (0-100 scale)
        carbon_emissions = base_score + random.uniform(-15, 15)
        carbon_emissions = max(0, min(100, carbon_emissions))
        
        water_usage = base_score + random.uniform(-10, 10)
        water_usage = max(0, min(100, water_usage))
        
        renewable_energy = base_score + random.uniform(-20, 20)
        renewable_energy = max(0, min(100, renewable_energy))
        
        waste_management = base_score + random.uniform(-10, 10)
        waste_management = max(0, min(100, waste_management))
        
        # Social metrics
        board_diversity = base_score + random.uniform(-15, 15)
        board_diversity = max(0, min(100, board_diversity))
        
        employee_satisfaction = base_score + random.uniform(-10, 10)
        employee_satisfaction = max(0, min(100, employee_satisfaction))
        
        community_engagement = base_score + random.uniform(-10, 10)
        community_engagement = max(0, min(100, community_engagement))
        
        # Governance metrics
        governance_score = base_score + random.uniform(-10, 10)
        governance_score = max(0, min(100, governance_score))
        
        board_independence = base_score + random.uniform(-15, 15)
        board_independence = max(0, min(100, board_independence))
        
        transparency = base_score + random.uniform(-10, 10)
        transparency = max(0, min(100, transparency))
        
        # Calculate overall score (weighted average)
        overall_score = (
            carbon_emissions * 0.15 +
            water_usage * 0.10 +
            renewable_energy * 0.10 +
            waste_management * 0.05 +
            board_diversity * 0.10 +
            employee_satisfaction * 0.10 +
            community_engagement * 0.05 +
            governance_score * 0.20 +
            board_independence * 0.10 +
            transparency * 0.05
        )
        
        # Determine category
        if overall_score >= 75:
            category = 'high'
            rating = 'A'
        elif overall_score >= 60:
            category = 'medium'
            rating = 'B'
        elif overall_score >= 45:
            category = 'medium'
            rating = 'C'
        else:
            category = 'low'
            rating = 'D'
        
        # Generate report date (within last 6 months)
        report_date = datetime.now() - timedelta(days=random.randint(0, 180))
        
        esg_data = {
            'symbol': symbol,
            'company_name': company_name,
            'report_date': report_date.strftime('%Y-%m-%d'),
            'report_year': report_date.year,
            'overall_score': round(overall_score, 1),
            'category': category,
            'rating': rating,
            'environmental': {
                'carbon_emissions_score': round(carbon_emissions, 1),
                'water_usage_score': round(water_usage, 1),
                'renewable_energy_score': round(renewable_energy, 1),
                'waste_management_score': round(waste_management, 1),
                'overall': round((carbon_emissions + water_usage + renewable_energy + waste_management) / 4, 1)
            },
            'social': {
                'board_diversity_score': round(board_diversity, 1),
                'employee_satisfaction_score': round(employee_satisfaction, 1),
                'community_engagement_score': round(community_engagement, 1),
                'overall': round((board_diversity + employee_satisfaction + community_engagement) / 3, 1)
            },
            'governance': {
                'governance_score': round(governance_score, 1),
                'board_independence_score': round(board_independence, 1),
                'transparency_score': round(transparency, 1),
                'overall': round((governance_score + board_independence + transparency) / 3, 1)
            },
            'highlights': self._generate_highlights(overall_score, category),
            'concerns': self._generate_concerns(overall_score, category),
            'generated_at': datetime.now().isoformat()
        }
        
        return esg_data
    
    def _generate_highlights(self, score: float, category: str) -> list:
        """Generate ESG highlights based on score"""
        all_highlights = [
            "Strong commitment to renewable energy transition",
            "Excellent board diversity and gender representation",
            "Transparent reporting and stakeholder engagement",
            "Significant reduction in carbon emissions year-over-year",
            "Industry-leading employee satisfaction scores",
            "Robust corporate governance framework",
            "Active community development programs",
            "Sustainable supply chain management",
            "Water conservation initiatives showing results",
            "Strong ethical business practices"
        ]
        
        # Return more highlights for higher scores
        if category == 'high':
            return random.sample(all_highlights, k=random.randint(4, 6))
        elif category == 'medium':
            return random.sample(all_highlights, k=random.randint(2, 4))
        else:
            return random.sample(all_highlights, k=random.randint(1, 2))
    
    def _generate_concerns(self, score: float, category: str) -> list:
        """Generate ESG concerns based on score"""
        all_concerns = [
            "Carbon emissions reduction targets need acceleration",
            "Board independence could be improved",
            "Water usage efficiency below industry average",
            "Limited disclosure on supply chain sustainability",
            "Employee diversity metrics need improvement",
            "Waste management practices require enhancement",
            "Community engagement programs need expansion",
            "Renewable energy adoption lagging peers",
            "Governance transparency could be strengthened",
            "ESG reporting frequency should increase"
        ]
        
        # Return more concerns for lower scores
        if category == 'low':
            return random.sample(all_concerns, k=random.randint(4, 6))
        elif category == 'medium':
            return random.sample(all_concerns, k=random.randint(2, 4))
        else:
            return random.sample(all_concerns, k=random.randint(1, 2))
    
    def write_esg_file(self, esg_data: Dict[str, Any]):
        """
        Write ESG data to JSON file
        
        Args:
            esg_data: ESG data dictionary
        """
        symbol = esg_data['symbol'].replace('.NS', '')
        filename = f"esg_{symbol}_{esg_data['report_year']}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(esg_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Written: {filename} (Score: {esg_data['overall_score']}, Rating: {esg_data['rating']})")
            
        except Exception as e:
            print(f"✗ Error writing {filename}: {e}")
    
    def seed_all(self):
        """Seed ESG data for all companies"""
        print("\n" + "="*60)
        print(f"Seeding ESG data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        for symbol, company_name in self.companies.items():
            print(f"Generating ESG data for {company_name}...")
            
            esg_data = self.generate_esg_data(symbol, company_name)
            self.write_esg_file(esg_data)
        
        print(f"\n✓ Seeded ESG data for {len(self.companies)} companies")


def main():
    """Main entry point"""
    # Determine output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'esg')
    
    # Create seeder
    seeder = ESGSeeder(output_dir=output_dir)
    
    # Seed all companies
    seeder.seed_all()
    
    print("\nESG data seeding complete!")
    print(f"Files written to: {output_dir}")


if __name__ == "__main__":
    main()
