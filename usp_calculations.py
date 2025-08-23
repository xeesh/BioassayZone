#!/usr/bin/env python3
"""
USP-81 Compliance Calculator
Implements USP-81 specific calculations and validation rules
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class USP81ValidationResult:
    """Result of USP-81 validation checks"""
    is_compliant: bool
    score: float
    checks_passed: int
    total_checks: int
    details: Dict
    recommendations: List[str]

class USP81Calculator:
    """Calculator for USP-81 compliance requirements"""
    
    def __init__(self):
        # USP-81 specific thresholds
        self.MIN_REPLICATES = 3
        self.MAX_CV_PERCENT = 15.0
        self.MIN_CONCENTRATION_POINTS = 3
        self.MIN_ZONE_MEASUREMENTS = 3
        
    def validate_minimum_replicates(self, concentration_data: Dict) -> Dict:
        """
        Validate minimum replicates per concentration (USP-81 requirement: ≥3)
        
        Args:
            concentration_data: Dict with concentration as key and list of measurements as values
            
        Returns:
            Dict with validation results
        """
        validation_results = {
            'is_compliant': True,
            'failed_concentrations': [],
            'replicate_counts': {},
            'overall_status': 'PASS'
        }
        
        for concentration, measurements in concentration_data.items():
            replicate_count = len(measurements)
            validation_results['replicate_counts'][concentration] = replicate_count
            
            if replicate_count < self.MIN_REPLICATES:
                validation_results['is_compliant'] = False
                validation_results['failed_concentrations'].append({
                    'concentration': concentration,
                    'replicate_count': replicate_count,
                    'required': self.MIN_REPLICATES
                })
        
        if not validation_results['is_compliant']:
            validation_results['overall_status'] = 'FAIL'
            
        return validation_results
    
    def validate_cv_threshold(self, concentration_data: Dict) -> Dict:
        """
        Validate CV% threshold (USP-81 requirement: ≤15%)
        
        Args:
            concentration_data: Dict with concentration as key and list of measurements as values
            
        Returns:
            Dict with validation results
        """
        validation_results = {
            'is_compliant': True,
            'failed_concentrations': [],
            'cv_values': {},
            'overall_status': 'PASS'
        }
        
        for concentration, measurements in concentration_data.items():
            if len(measurements) < 2:
                continue
                
            mean_val = np.mean(measurements)
            std_val = np.std(measurements)
            cv_percent = (std_val / mean_val * 100) if mean_val > 0 else 0
            
            validation_results['cv_values'][concentration] = {
                'cv_percent': cv_percent,
                'mean': mean_val,
                'std': std_val
            }
            
            if cv_percent > self.MAX_CV_PERCENT:
                validation_results['is_compliant'] = False
                validation_results['failed_concentrations'].append({
                    'concentration': concentration,
                    'cv_percent': cv_percent,
                    'threshold': self.MAX_CV_PERCENT
                })
        
        if not validation_results['is_compliant']:
            validation_results['overall_status'] = 'FAIL'
            
        return validation_results
    
    def validate_concentration_range(self, concentrations: List[float]) -> Dict:
        """
        Validate concentration range coverage (USP-81 requirement: ≥3 concentration points)
        
        Args:
            concentrations: List of concentration values
            
        Returns:
            Dict with validation results
        """
        validation_results = {
            'is_compliant': len(concentrations) >= self.MIN_CONCENTRATION_POINTS,
            'concentration_count': len(concentrations),
            'required_count': self.MIN_CONCENTRATION_POINTS,
            'concentrations': sorted(concentrations),
            'overall_status': 'PASS' if len(concentrations) >= self.MIN_CONCENTRATION_POINTS else 'FAIL'
        }
        
        if validation_results['is_compliant']:
            # Calculate concentration range
            min_conc = min(concentrations)
            max_conc = max(concentrations)
            validation_results['concentration_range'] = {
                'min': min_conc,
                'max': max_conc,
                'range': max_conc - min_conc
            }
            
        return validation_results
    
    def calculate_potency(self, standard_data: Dict, sample_data: Dict) -> Dict:
        """
        Calculate potency using USP-81 methodology
        
        Args:
            standard_data: Standard curve data
            sample_data: Sample measurement data
            
        Returns:
            Dict with potency calculation results
        """
        try:
            # Extract standard curve data
            standard_concentrations = list(standard_data.keys())
            standard_responses = [np.mean(measurements) for measurements in standard_data.values()]
            
            # Fit standard curve (log-linear relationship)
            log_concentrations = np.log10(standard_concentrations)
            
            # Linear regression
            coeffs = np.polyfit(log_concentrations, standard_responses, 1)
            slope = coeffs[0]
            intercept = coeffs[1]
            
            # Calculate sample potency
            sample_response = np.mean(sample_data.get('measurements', [0]))
            
            if slope != 0:
                log_sample_conc = (sample_response - intercept) / slope
                sample_concentration = 10 ** log_sample_conc
                
                # Calculate potency relative to standard
                potency_result = {
                    'sample_response': sample_response,
                    'calculated_concentration': sample_concentration,
                    'standard_curve': {
                        'slope': slope,
                        'intercept': intercept,
                        'r_squared': self._calculate_r_squared(log_concentrations, standard_responses, coeffs)
                    },
                    'confidence_interval': self._calculate_confidence_interval(
                        log_concentrations, standard_responses, sample_response, slope, intercept
                    )
                }
            else:
                potency_result = {
                    'error': 'Invalid standard curve slope',
                    'sample_response': sample_response
                }
                
            return potency_result
            
        except Exception as e:
            return {'error': f'Potency calculation failed: {str(e)}'}
    
    def _calculate_r_squared(self, x: List[float], y: List[float], coeffs: List[float]) -> float:
        """Calculate R-squared value for curve fit"""
        try:
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        except:
            return 0
    
    def _calculate_confidence_interval(self, x: List[float], y: List[float], 
                                     sample_response: float, slope: float, intercept: float) -> Dict:
        """Calculate confidence interval for potency estimate"""
        try:
            n = len(x)
            if n < 3:
                return {'lower': None, 'upper': None, 'confidence_level': 0.95}
            
            # Calculate standard error of estimate
            y_pred = np.polyval([slope, intercept], x)
            residuals = y - y_pred
            mse = np.sum(residuals ** 2) / (n - 2)
            
            # Calculate prediction interval
            x_mean = np.mean(x)
            x_var = np.sum((x - x_mean) ** 2)
            
            # For 95% confidence interval
            t_value = 2.0  # Approximate for n > 30, should use t-distribution for small n
            
            sample_x = (sample_response - intercept) / slope if slope != 0 else 0
            
            se_pred = np.sqrt(mse * (1 + 1/n + (sample_x - x_mean)**2 / x_var))
            margin = t_value * se_pred
            
            return {
                'lower': sample_x - margin,
                'upper': sample_x + margin,
                'confidence_level': 0.95,
                'standard_error': se_pred
            }
        except:
            return {'lower': None, 'upper': None, 'confidence_level': 0.95}
    
    def comprehensive_usp81_validation(self, assay_data: Dict) -> USP81ValidationResult:
        """
        Comprehensive USP-81 validation
        
        Args:
            assay_data: Complete assay data including concentrations and measurements
            
        Returns:
            USP81ValidationResult with comprehensive validation
        """
        checks_passed = 0
        total_checks = 4
        details = {}
        recommendations = []
        
        # Check 1: Minimum replicates
        replicate_validation = self.validate_minimum_replicates(assay_data.get('concentration_data', {}))
        details['replicate_validation'] = replicate_validation
        if replicate_validation['is_compliant']:
            checks_passed += 1
        else:
            recommendations.append(f"Ensure ≥{self.MIN_REPLICATES} replicates per concentration")
        
        # Check 2: CV% threshold
        cv_validation = self.validate_cv_threshold(assay_data.get('concentration_data', {}))
        details['cv_validation'] = cv_validation
        if cv_validation['is_compliant']:
            checks_passed += 1
        else:
            recommendations.append(f"Ensure CV% ≤ {self.MAX_CV_PERCENT}% for all concentrations")
        
        # Check 3: Concentration range
        concentrations = list(assay_data.get('concentration_data', {}).keys())
        concentration_validation = self.validate_concentration_range(concentrations)
        details['concentration_validation'] = concentration_validation
        if concentration_validation['is_compliant']:
            checks_passed += 1
        else:
            recommendations.append(f"Ensure ≥{self.MIN_CONCENTRATION_POINTS} concentration points")
        
        # Check 4: Zone measurement precision
        zone_validation = self._validate_zone_measurements(assay_data)
        details['zone_validation'] = zone_validation
        if zone_validation['is_compliant']:
            checks_passed += 1
        else:
            recommendations.append("Ensure sufficient zone measurements for statistical validity")
        
        # Calculate overall score
        score = (checks_passed / total_checks) * 100
        
        # Determine compliance status
        is_compliant = score >= 80  # 80% threshold for compliance
        
        # Add general recommendations
        if is_compliant:
            recommendations.append("Consider implementing additional USP-81 features for enhanced compliance")
        else:
            recommendations.extend([
                "Review and improve measurement precision",
                "Implement quality control procedures",
                "Consider additional concentration points if needed"
            ])
        
        return USP81ValidationResult(
            is_compliant=is_compliant,
            score=score,
            checks_passed=checks_passed,
            total_checks=total_checks,
            details=details,
            recommendations=recommendations
        )
    
    def _validate_zone_measurements(self, assay_data: Dict) -> Dict:
        """Validate zone measurement precision"""
        zone_data = assay_data.get('zone_data', {})
        
        validation_result = {
            'is_compliant': True,
            'total_zones': 0,
            'valid_zones': 0,
            'overall_status': 'PASS'
        }
        
        total_zones = 0
        valid_zones = 0
        
        for standard, zones in zone_data.items():
            if isinstance(zones, dict) and 'measurements' in zones:
                zone_count = len(zones['measurements'])
                total_zones += zone_count
                
                if zone_count >= self.MIN_ZONE_MEASUREMENTS:
                    valid_zones += 1
                else:
                    validation_result['is_compliant'] = False
        
        validation_result['total_zones'] = total_zones
        validation_result['valid_zones'] = valid_zones
        
        if not validation_result['is_compliant']:
            validation_result['overall_status'] = 'FAIL'
        
        return validation_result
    
    def generate_usp81_report_data(self, validation_result: USP81ValidationResult, 
                                  assay_data: Dict) -> Dict:
        """
        Generate data for USP-81 compliance report
        
        Args:
            validation_result: USP-81 validation results
            assay_data: Original assay data
            
        Returns:
            Dict with formatted report data
        """
        report_data = {
            'validation_summary': {
                'overall_compliance': validation_result.is_compliant,
                'compliance_score': f"{validation_result.score:.1f}%",
                'checks_passed': f"{validation_result.checks_passed}/{validation_result.total_checks}",
                'status': 'COMPLIANT' if validation_result.is_compliant else 'NON-COMPLIANT'
            },
            'detailed_results': validation_result.details,
            'recommendations': validation_result.recommendations,
            'assay_information': {
                'total_concentrations': len(assay_data.get('concentration_data', {})),
                'total_measurements': sum(len(measurements) for measurements in 
                                        assay_data.get('concentration_data', {}).values()),
                'concentration_range': self._get_concentration_range(assay_data)
            },
            'usp81_requirements': {
                'minimum_replicates': f"≥{self.MIN_REPLICATES}",
                'max_cv_percent': f"≤{self.MAX_CV_PERCENT}%",
                'min_concentration_points': f"≥{self.MIN_CONCENTRATION_POINTS}",
                'min_zone_measurements': f"≥{self.MIN_ZONE_MEASUREMENTS}"
            }
        }
        
        return report_data
    
    def _get_concentration_range(self, assay_data: Dict) -> Dict:
        """Extract concentration range information"""
        concentrations = list(assay_data.get('concentration_data', {}).keys())
        if concentrations:
            return {
                'min': min(concentrations),
                'max': max(concentrations),
                'range': max(concentrations) - min(concentrations)
            }
        return {'min': 0, 'max': 0, 'range': 0}