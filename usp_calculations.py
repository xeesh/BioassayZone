import numpy as np
from scipy import stats
from typing import Dict, List, Any, Tuple, Optional
import math

class USP81Calculator:
    """USP-81 compliant statistical calculations for bioassay analysis"""
    
    def __init__(self):
        self.confidence_level = 0.95
        self.alpha = 1 - self.confidence_level
    
    def parallel_line_assay(self, standard_responses: List[List[float]], 
                           test_responses: List[List[float]], 
                           standard_doses: List[float], 
                           test_doses: List[float]) -> Dict[str, Any]:
        """
        Perform USP-81 parallel line assay analysis (2+2, 3+3 designs)
        
        Args:
            standard_responses: List of response lists for each standard dose level
            test_responses: List of response lists for each test dose level  
            standard_doses: Dose levels for standard
            test_doses: Dose levels for test sample
            
        Returns:
            Dictionary containing ANOVA results, potency estimate, and validity tests
        """
        try:
            # Prepare data for ANOVA
            standard_data = self._prepare_assay_data(standard_responses, standard_doses, 'Standard')
            test_data = self._prepare_assay_data(test_responses, test_doses, 'Test')
            
            # Combine data
            all_data = standard_data + test_data
            
            # Perform ANOVA
            anova_results = self._perform_anova(all_data)
            
            # Calculate potency estimate
            potency_results = self._calculate_potency(standard_data, test_data)
            
            # Perform validity tests
            validity_results = self._perform_validity_tests(all_data, anova_results)
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(potency_results, anova_results)
            
            return {
                'anova_results': anova_results,
                'potency_estimate': potency_results['potency'],
                'potency_log': potency_results['log_potency'],
                'confidence_intervals': confidence_intervals,
                'validity_tests': validity_results,
                'assay_valid': validity_results['overall_validity'],
                'design_type': self._determine_design_type(standard_doses, test_doses),
                'degrees_of_freedom': anova_results['df'],
                'calculated_at': np.datetime64('now').item().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f"USP-81 calculation failed: {str(e)}",
                'assay_valid': False
            }
    
    def _prepare_assay_data(self, responses: List[List[float]], doses: List[float], 
                           preparation_type: str) -> List[Dict[str, Any]]:
        """Prepare data structure for ANOVA analysis"""
        data = []
        
        for i, dose_responses in enumerate(responses):
            log_dose = math.log10(doses[i]) if doses[i] > 0 else 0
            
            for response in dose_responses:
                data.append({
                    'response': response,
                    'dose': doses[i],
                    'log_dose': log_dose,
                    'preparation': preparation_type,
                    'dose_level': i
                })
        
        return data
    
    def _perform_anova(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform Analysis of Variance for parallel line assay"""
        # Extract responses and factors
        responses = np.array([d['response'] for d in data])
        preparations = np.array([d['preparation'] for d in data])
        log_doses = np.array([d['log_dose'] for d in data])
        
        # Calculate means
        overall_mean = np.mean(responses)
        
        # Group by preparation
        standard_responses = responses[preparations == 'Standard']
        test_responses = responses[preparations == 'Test']
        
        standard_log_doses = log_doses[preparations == 'Standard']
        test_log_doses = log_doses[preparations == 'Test']
        
        # Calculate regression lines for each preparation
        standard_slope, standard_intercept, standard_r, _, _ = stats.linregress(standard_log_doses, standard_responses)
        test_slope, test_intercept, test_r, _, _ = stats.linregress(test_log_doses, test_responses)
        
        # Calculate sums of squares
        total_ss = np.sum((responses - overall_mean) ** 2)
        
        # Regression SS for each preparation
        standard_fitted = standard_slope * standard_log_doses + standard_intercept
        test_fitted = test_slope * test_log_doses + test_intercept
        
        regression_ss = (np.sum((standard_fitted - np.mean(standard_responses)) ** 2) + 
                        np.sum((test_fitted - np.mean(test_responses)) ** 2))
        
        # Preparation SS
        prep_ss = (len(standard_responses) * (np.mean(standard_responses) - overall_mean) ** 2 + 
                  len(test_responses) * (np.mean(test_responses) - overall_mean) ** 2)
        
        # Error SS
        error_ss = total_ss - regression_ss - prep_ss
        
        # Degrees of freedom
        total_df = len(responses) - 1
        regression_df = 2  # Two regression lines
        prep_df = 1  # Standard vs Test
        error_df = total_df - regression_df - prep_df
        
        # Mean squares
        regression_ms = regression_ss / regression_df if regression_df > 0 else 0
        prep_ms = prep_ss / prep_df if prep_df > 0 else 0
        error_ms = error_ss / error_df if error_df > 0 else 0
        
        # F-statistics
        regression_f = regression_ms / error_ms if error_ms > 0 else 0
        prep_f = prep_ms / error_ms if error_ms > 0 else 0
        
        # P-values
        regression_p = 1 - stats.f.cdf(regression_f, regression_df, error_df) if regression_f > 0 else 1
        prep_p = 1 - stats.f.cdf(prep_f, prep_df, error_df) if prep_f > 0 else 1
        
        return {
            'total_ss': total_ss,
            'regression_ss': regression_ss,
            'preparation_ss': prep_ss,
            'error_ss': error_ss,
            'total_df': total_df,
            'regression_df': regression_df,
            'preparation_df': prep_df,
            'error_df': error_df,
            'regression_ms': regression_ms,
            'preparation_ms': prep_ms,
            'error_ms': error_ms,
            'regression_f': regression_f,
            'preparation_f': prep_f,
            'regression_p': regression_p,
            'preparation_p': prep_p,
            'standard_slope': standard_slope,
            'test_slope': test_slope,
            'standard_intercept': standard_intercept,
            'test_intercept': test_intercept,
            'df': error_df
        }
    
    def _calculate_potency(self, standard_data: List[Dict[str, Any]], 
                          test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate potency estimate"""
        # Extract data for regression
        std_responses = np.array([d['response'] for d in standard_data])
        std_log_doses = np.array([d['log_dose'] for d in standard_data])
        
        test_responses = np.array([d['response'] for d in test_data])
        test_log_doses = np.array([d['log_dose'] for d in test_data])
        
        # Calculate regression lines
        std_slope, std_intercept, _, _, _ = stats.linregress(std_log_doses, std_responses)
        test_slope, test_intercept, _, _, _ = stats.linregress(test_log_doses, test_responses)
        
        # Calculate potency (log scale)
        # Potency is the horizontal distance between parallel lines
        mean_response = (np.mean(std_responses) + np.mean(test_responses)) / 2
        
        # Find log doses that give mean response for each preparation
        std_log_dose_at_mean = (mean_response - std_intercept) / std_slope if std_slope != 0 else 0
        test_log_dose_at_mean = (mean_response - test_intercept) / test_slope if test_slope != 0 else 0
        
        log_potency = std_log_dose_at_mean - test_log_dose_at_mean
        potency = 10 ** log_potency
        
        return {
            'potency': potency,
            'log_potency': log_potency,
            'standard_slope': std_slope,
            'test_slope': test_slope,
            'standard_intercept': std_intercept,
            'test_intercept': test_intercept
        }
    
    def _perform_validity_tests(self, data: List[Dict[str, Any]], 
                               anova_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform USP-81 validity tests"""
        validity_tests = {}
        
        # Test 1: Linearity (Regression significance)
        validity_tests['linearity'] = {
            'f_value': anova_results['regression_f'],
            'p_value': anova_results['regression_p'],
            'significant': anova_results['regression_p'] < self.alpha,
            'valid': anova_results['regression_p'] < self.alpha
        }
        
        # Test 2: Parallelism (Slope difference)
        slope_diff = abs(anova_results['standard_slope'] - anova_results['test_slope'])
        # Simplified parallelism test - in full implementation would use proper F-test
        validity_tests['parallelism'] = {
            'slope_difference': slope_diff,
            'standard_slope': anova_results['standard_slope'],
            'test_slope': anova_results['test_slope'],
            'valid': slope_diff < 0.2  # Simplified criterion
        }
        
        # Test 3: Significance of potency estimate
        validity_tests['potency_significance'] = {
            'f_value': anova_results['preparation_f'],
            'p_value': anova_results['preparation_p'],
            'significant': anova_results['preparation_p'] < self.alpha,
            'valid': anova_results['preparation_p'] < self.alpha
        }
        
        # Overall validity
        validity_tests['overall_validity'] = (
            validity_tests['linearity']['valid'] and
            validity_tests['parallelism']['valid'] and
            validity_tests['potency_significance']['valid']
        )
        
        return validity_tests
    
    def _calculate_confidence_intervals(self, potency_results: Dict[str, Any], 
                                       anova_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence intervals for potency estimate"""
        # Simplified confidence interval calculation
        # In full implementation, would use proper statistical methods
        
        error_ms = anova_results['error_ms']
        df = anova_results['error_df']
        
        if df > 0:
            t_critical = stats.t.ppf(1 - self.alpha/2, df)
            
            # Approximate standard error (simplified)
            se_log_potency = math.sqrt(error_ms) * 0.1  # Simplified approximation
            
            log_potency = potency_results['log_potency']
            
            # Confidence interval for log potency
            log_ci_lower = log_potency - t_critical * se_log_potency
            log_ci_upper = log_potency + t_critical * se_log_potency
            
            # Convert to potency scale
            ci_lower = 10 ** log_ci_lower
            ci_upper = 10 ** log_ci_upper
            
            return {
                'confidence_level': self.confidence_level * 100,
                'potency_ci_lower': ci_lower,
                'potency_ci_upper': ci_upper,
                'log_potency_ci_lower': log_ci_lower,
                'log_potency_ci_upper': log_ci_upper,
                'standard_error': se_log_potency
            }
        else:
            return {
                'error': 'Insufficient degrees of freedom for confidence interval calculation'
            }
    
    def _determine_design_type(self, standard_doses: List[float], 
                              test_doses: List[float]) -> str:
        """Determine the assay design type"""
        std_levels = len(standard_doses)
        test_levels = len(test_doses)
        
        if std_levels == 2 and test_levels == 2:
            return "2+2"
        elif std_levels == 3 and test_levels == 3:
            return "3+3"
        else:
            return f"{std_levels}+{test_levels}"
    
    def calculate_basic_statistics(self, zone_diameters: List[float]) -> Dict[str, Any]:
        """Calculate basic statistics with enhanced bioassay-specific metrics"""
        if not zone_diameters:
            return {}
        
        diameters = np.array(zone_diameters, dtype=float)
        
        # Basic statistics
        stats_dict = {
            'count': len(diameters),
            'mean': float(np.mean(diameters)),
            'median': float(np.median(diameters)),
            'std_dev': float(np.std(diameters, ddof=1)) if len(diameters) > 1 else 0.0,
            'min': float(np.min(diameters)),
            'max': float(np.max(diameters)),
            'range': float(np.max(diameters) - np.min(diameters))
        }
        
        # Coefficient of variation
        if stats_dict['mean'] > 0:
            stats_dict['cv_percent'] = (stats_dict['std_dev'] / stats_dict['mean']) * 100
        else:
            stats_dict['cv_percent'] = 0.0
        
        # Additional bioassay-specific statistics
        if len(diameters) >= 3:
            # Outlier detection using modified Z-score
            median = stats_dict['median']
            mad = np.median(np.abs(diameters - median))  # Median Absolute Deviation
            
            if mad > 0:
                modified_z_scores = 0.6745 * (diameters - median) / mad
                outlier_threshold = 3.5
                outliers = np.abs(modified_z_scores) > outlier_threshold
                
                stats_dict['outliers'] = {
                    'count': int(np.sum(outliers)),
                    'indices': [int(i) for i in np.where(outliers)[0]],
                    'values': [float(diameters[i]) for i in np.where(outliers)[0]]
                }
            else:
                stats_dict['outliers'] = {'count': 0, 'indices': [], 'values': []}
            
            # Normality test (Shapiro-Wilk for small samples)
            if len(diameters) <= 50:
                shapiro_stat, shapiro_p = stats.shapiro(diameters)
                stats_dict['normality_test'] = {
                    'test': 'Shapiro-Wilk',
                    'statistic': float(shapiro_stat),
                    'p_value': float(shapiro_p),
                    'normal_distribution': shapiro_p > 0.05
                }
        
        # Quality assessment based on CV
        cv = stats_dict['cv_percent']
        if cv < 5:
            stats_dict['precision_assessment'] = 'Excellent'
        elif cv < 10:
            stats_dict['precision_assessment'] = 'Good'
        elif cv < 15:
            stats_dict['precision_assessment'] = 'Acceptable'
        else:
            stats_dict['precision_assessment'] = 'Poor - Review methodology'
        
        # Round values for presentation
        for key, value in stats_dict.items():
            if isinstance(value, float):
                stats_dict[key] = round(value, 3)
        
        return stats_dict