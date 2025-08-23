#!/usr/bin/env python3
"""
USP-81 Compliance Analysis Script
Analyzes the Excel file to understand USP-81 requirements and assess application compliance
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def analyze_usp81_excel(file_path):
    """Analyze the USP-81 Excel file for compliance requirements"""
    
    print("🔬 USP-81 Compliance Analysis")
    print("=" * 50)
    
    # Read the Excel file
    try:
        df = pd.read_excel(file_path)
        print(f"✅ Successfully loaded Excel file: {file_path}")
        print(f"📊 File dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return None
    
    # Analyze the structure
    print("\n📋 File Structure Analysis:")
    print("-" * 30)
    
    # Identify key columns and their purposes
    standard_col = df.iloc[:, 0]  # First column contains standards
    concentration_col = df.iloc[:, 1]  # Second column contains concentrations
    replicate_col = df.iloc[:, 2]  # Third column contains plate replicates
    
    # Extract unique standards
    standards = standard_col.dropna().unique()
    print(f"🏷️  Standards identified: {list(standards)}")
    
    # Extract concentrations
    concentrations = concentration_col.dropna().unique()
    print(f"🧪 Concentrations (μg/mL): {list(concentrations)}")
    
    # Extract replicates
    replicates = replicate_col.dropna().unique()
    print(f"🔄 Replicates: {list(replicates)}")
    
    # Clean up the data - remove header rows and get actual values
    actual_standards = [s for s in standards if s not in ['Standard', 'Concentration', 'Plate replicate']]
    actual_concentrations = [c for c in concentrations if c not in ['Concentration', 'Plate replicate'] and isinstance(c, (int, float))]
    actual_replicates = [r for r in replicates if r not in ['Standard', 'Concentration', 'Plate replicate'] and isinstance(r, (int, float))]
    
    print(f"🏷️  Actual Standards: {actual_standards}")
    print(f"🧪 Actual Concentrations: {actual_concentrations}")
    print(f"🔄 Actual Replicates: {actual_replicates}")
    
    # Analyze zone measurements
    print("\n📏 Zone Measurement Analysis:")
    print("-" * 30)
    
    # Find zone measurement columns
    zone_cols = []
    for col_idx, col_name in enumerate(df.columns):
        cell_value = str(df.iloc[1, col_idx])  # Use second row for zone detection
        if 'Zone' in cell_value and 'mm' in cell_value:
            zone_cols.append(col_idx)
    
    print(f"🎯 Zone measurement columns found: {len(zone_cols)}")
    print(f"   Zone columns: {[df.iloc[1, col] for col in zone_cols]}")
    
    # Extract zone data for each standard
    zone_data = {}
    for standard in actual_standards:
        standard_rows = df[standard_col == standard]
        zone_measurements = []
        
        for _, row in standard_rows.iterrows():
            for col in zone_cols:
                value = row.iloc[col]
                if pd.notna(value) and isinstance(value, (int, float)):
                    zone_measurements.append(value)
        
        if zone_measurements:
            zone_data[standard] = {
                'measurements': zone_measurements,
                'count': len(zone_measurements),
                'mean': np.mean(zone_measurements),
                'std': np.std(zone_measurements),
                'cv_percent': (np.std(zone_measurements) / np.mean(zone_measurements)) * 100 if np.mean(zone_measurements) > 0 else 0
            }
    
    # Display zone statistics
    for standard, stats in zone_data.items():
        print(f"\n📊 {standard}:")
        print(f"   Measurements: {stats['count']}")
        print(f"   Mean: {stats['mean']:.2f} mm")
        print(f"   Std Dev: {stats['std']:.2f} mm")
        print(f"   CV%: {stats['cv_percent']:.2f}%")
    
    # USP-81 Compliance Assessment
    print("\n✅ USP-81 Compliance Assessment:")
    print("-" * 40)
    
    compliance_checks = {
        'minimum_replicates': False,
        'cv_percent_acceptable': False,
        'concentration_range': False,
        'zone_measurement_precision': False
    }
    
    # Check minimum replicates (should be at least 3)
    min_replicates = min(actual_replicates) if actual_replicates else 0
    if min_replicates >= 3:
        compliance_checks['minimum_replicates'] = True
        print("✅ Minimum 3 replicates per concentration: PASS")
    else:
        print(f"❌ Minimum 3 replicates per concentration: FAIL (found {min_replicates})")
    
    # Check CV% (should be ≤ 15% for acceptable precision)
    cv_values = [stats['cv_percent'] for stats in zone_data.values()]
    if cv_values:
        max_cv = max(cv_values)
        if max_cv <= 15.0:
            compliance_checks['cv_percent_acceptable'] = True
            print(f"✅ CV% ≤ 15%: PASS (max CV: {max_cv:.2f}%)")
        else:
            print(f"❌ CV% ≤ 15%: FAIL (max CV: {max_cv:.2f}%)")
    
    # Check concentration range (should cover appropriate range)
    if len(actual_concentrations) >= 3:
        compliance_checks['concentration_range'] = True
        print("✅ Appropriate concentration range: PASS")
    else:
        print(f"❌ Appropriate concentration range: FAIL (found {len(actual_concentrations)} concentrations)")
    
    # Check zone measurement precision
    if all(stats['count'] >= 3 for stats in zone_data.values()):
        compliance_checks['zone_measurement_precision'] = True
        print("✅ Zone measurement precision: PASS")
    else:
        print("❌ Zone measurement precision: FAIL")
    
    # Overall compliance score
    compliance_score = sum(compliance_checks.values()) / len(compliance_checks) * 100
    print(f"\n📈 Overall Compliance Score: {compliance_score:.1f}%")
    
    if compliance_score >= 80:
        print("🎉 EXCELLENT: High compliance with USP-81 requirements")
    elif compliance_score >= 60:
        print("👍 GOOD: Moderate compliance with USP-81 requirements")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Low compliance with USP-81 requirements")
    
    # Generate recommendations
    print("\n💡 Recommendations for BioassayZone Application:")
    print("-" * 50)
    
    recommendations = []
    
    if not compliance_checks['minimum_replicates']:
        recommendations.append("Implement minimum replicate validation (≥3 per concentration)")
    
    if not compliance_checks['cv_percent_acceptable']:
        recommendations.append("Add CV% validation with 15% threshold")
    
    if not compliance_checks['concentration_range']:
        recommendations.append("Ensure appropriate concentration range coverage")
    
    if not compliance_checks['zone_measurement_precision']:
        recommendations.append("Implement zone measurement precision validation")
    
    # General recommendations
    recommendations.extend([
        "Add USP-81 specific validation rules",
        "Implement concentration-response curve analysis",
        "Add statistical significance testing",
        "Include potency calculation features",
        "Add compliance reporting templates"
    ])
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    # Save analysis results
    analysis_results = {
        'file_path': str(file_path),
        'standards': actual_standards,
        'concentrations': actual_concentrations,
        'replicates': actual_replicates,
        'zone_data': zone_data,
        'compliance_checks': compliance_checks,
        'compliance_score': compliance_score,
        'recommendations': recommendations
    }
    
    output_file = Path('usp81_analysis_results.json')
    with open(output_file, 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    
    print(f"\n💾 Analysis results saved to: {output_file}")
    
    return analysis_results

def assess_application_compliance(analysis_results):
    """Assess how well the BioassayZone application meets USP-81 requirements"""
    
    print("\n🔍 BioassayZone Application Compliance Assessment:")
    print("=" * 60)
    
    # Current application features
    current_features = {
        'zone_detection': True,
        'measurement_calculation': True,
        'statistical_analysis': True,
        'report_generation': True,
        'audit_trail': True,
        'user_management': True,
        'electronic_signatures': True
    }
    
    # USP-81 specific requirements
    usp81_requirements = {
        'minimum_replicates_validation': False,
        'cv_percent_threshold': False,
        'concentration_response_curve': False,
        'potency_calculation': False,
        'usp81_reporting': False,
        'statistical_significance': False,
        'quality_control_charts': False
    }
    
    print("📋 Current Application Features:")
    for feature, status in current_features.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {feature.replace('_', ' ').title()}")
    
    print("\n📋 USP-81 Specific Requirements:")
    for requirement, status in usp81_requirements.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {requirement.replace('_', ' ').title()}")
    
    # Gap analysis
    print("\n🔍 Gap Analysis:")
    print("-" * 20)
    
    gaps = []
    for requirement, status in usp81_requirements.items():
        if not status:
            gaps.append(requirement)
    
    if gaps:
        print("❌ Missing USP-81 features:")
        for gap in gaps:
            print(f"   • {gap.replace('_', ' ').title()}")
    else:
        print("✅ All USP-81 requirements are met!")
    
    # Implementation priority
    print("\n🎯 Implementation Priority:")
    print("-" * 25)
    
    high_priority = [
        'minimum_replicates_validation',
        'cv_percent_threshold',
        'usp81_reporting'
    ]
    
    medium_priority = [
        'concentration_response_curve',
        'statistical_significance'
    ]
    
    low_priority = [
        'potency_calculation',
        'quality_control_charts'
    ]
    
    print("🔴 High Priority (Implement First):")
    for item in high_priority:
        if item in gaps:
            print(f"   • {item.replace('_', ' ').title()}")
    
    print("\n🟡 Medium Priority:")
    for item in medium_priority:
        if item in gaps:
            print(f"   • {item.replace('_', ' ').title()}")
    
    print("\n🟢 Low Priority:")
    for item in low_priority:
        if item in gaps:
            print(f"   • {item.replace('_', ' ').title()}")
    
    # Overall assessment
    current_score = sum(current_features.values()) / len(current_features) * 100
    usp81_score = sum(usp81_requirements.values()) / len(usp81_requirements) * 100
    
    print(f"\n📊 Compliance Scores:")
    print(f"   General Bioassay Features: {current_score:.1f}%")
    print(f"   USP-81 Specific Features: {usp81_score:.1f}%")
    
    if usp81_score >= 80:
        print("🎉 EXCELLENT: Application is highly compliant with USP-81")
    elif usp81_score >= 60:
        print("👍 GOOD: Application has moderate USP-81 compliance")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Application needs USP-81 specific features")

def main():
    """Main function to run the analysis"""
    
    excel_file = Path('Data/Bioassy USP-81.xlsx')
    
    if not excel_file.exists():
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    # Analyze the Excel file
    analysis_results = analyze_usp81_excel(excel_file)
    
    if analysis_results:
        # Assess application compliance
        assess_application_compliance(analysis_results)
        
        print("\n" + "=" * 60)
        print("🏁 Analysis Complete!")
        print("=" * 60)

if __name__ == '__main__':
    main()
