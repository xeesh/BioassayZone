import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class AuditLogger:
    """Handles audit logging for bioassay operations"""
    
    def __init__(self, log_file: str = 'audit_log.json'):
        self.log_file = log_file
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self):
        """Create log file if it doesn't exist"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)
    
    def log_action(self, user: str, action: str, description: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Log an action to the audit trail
        
        Args:
            user: Username or identifier of the person performing the action
            action: Type of action being performed
            description: Human-readable description of the action
            metadata: Additional data related to the action
        """
        try:
            # Load existing log entries
            log_entries = self._load_log_entries()
            
            # Create new log entry
            entry = {
                'timestamp': datetime.now().isoformat(),
                'user': user,
                'action': action,
                'description': description,
                'metadata': metadata or {}
            }
            
            # Add to log entries
            log_entries.append(entry)
            
            # Save back to file
            self._save_log_entries(log_entries)
            
        except Exception as e:
            # In a production system, this would use proper logging
            print(f"Failed to log action: {str(e)}")
    
    def get_audit_trail(self, assay_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail entries
        
        Args:
            assay_id: Optional assay ID to filter entries
            
        Returns:
            List of audit trail entries
        """
        try:
            log_entries = self._load_log_entries()
            
            if assay_id:
                # Filter entries for specific assay
                filtered_entries = []
                for entry in log_entries:
                    metadata = entry.get('metadata', {})
                    if metadata.get('assay_id') == assay_id:
                        filtered_entries.append(entry)
                return filtered_entries
            else:
                return log_entries
                
        except Exception as e:
            print(f"Failed to retrieve audit trail: {str(e)}")
            return []
    
    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent audit trail entries
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of recent audit trail entries
        """
        try:
            log_entries = self._load_log_entries()
            # Sort by timestamp (newest first) and limit
            sorted_entries = sorted(log_entries, 
                                  key=lambda x: x.get('timestamp', ''), 
                                  reverse=True)
            return sorted_entries[:limit]
            
        except Exception as e:
            print(f"Failed to retrieve recent entries: {str(e)}")
            return []
    
    def search_entries(self, search_term: str, search_field: str = 'description') -> List[Dict[str, Any]]:
        """
        Search audit trail entries
        
        Args:
            search_term: Term to search for
            search_field: Field to search in ('description', 'action', 'user')
            
        Returns:
            List of matching audit trail entries
        """
        try:
            log_entries = self._load_log_entries()
            matching_entries = []
            
            for entry in log_entries:
                field_value = entry.get(search_field, '').lower()
                if search_term.lower() in field_value:
                    matching_entries.append(entry)
            
            return matching_entries
            
        except Exception as e:
            print(f"Failed to search entries: {str(e)}")
            return []
    
    def get_user_activity(self, user: str) -> List[Dict[str, Any]]:
        """
        Get all activity for a specific user
        
        Args:
            user: Username to filter by
            
        Returns:
            List of audit trail entries for the user
        """
        try:
            log_entries = self._load_log_entries()
            user_entries = [entry for entry in log_entries if entry.get('user') == user]
            
            # Sort by timestamp (newest first)
            return sorted(user_entries, 
                         key=lambda x: x.get('timestamp', ''), 
                         reverse=True)
            
        except Exception as e:
            print(f"Failed to retrieve user activity: {str(e)}")
            return []
    
    def _load_log_entries(self) -> List[Dict[str, Any]]:
        """Load log entries from file"""
        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_log_entries(self, entries: List[Dict[str, Any]]):
        """Save log entries to file"""
        with open(self.log_file, 'w') as f:
            json.dump(entries, f, indent=2, default=str)
    
    def export_audit_trail(self, output_file: str, assay_id: Optional[str] = None):
        """
        Export audit trail to a JSON file
        
        Args:
            output_file: Path to export file
            assay_id: Optional assay ID to filter entries
        """
        try:
            entries = self.get_audit_trail(assay_id)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'assay_id': assay_id,
                'entry_count': len(entries),
                'entries': entries
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
        except Exception as e:
            raise Exception(f"Failed to export audit trail: {str(e)}")
    
    def validate_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of the audit log
        
        Returns:
            Dictionary with validation results
        """
        try:
            entries = self._load_log_entries()
            
            validation_result = {
                'total_entries': len(entries),
                'valid_entries': 0,
                'invalid_entries': 0,
                'errors': []
            }
            
            required_fields = ['timestamp', 'user', 'action', 'description']
            
            for i, entry in enumerate(entries):
                is_valid = True
                
                # Check required fields
                for field in required_fields:
                    if field not in entry or not entry[field]:
                        validation_result['errors'].append(f"Entry {i}: Missing required field '{field}'")
                        is_valid = False
                
                # Validate timestamp format
                try:
                    datetime.fromisoformat(entry.get('timestamp', ''))
                except ValueError:
                    validation_result['errors'].append(f"Entry {i}: Invalid timestamp format")
                    is_valid = False
                
                if is_valid:
                    validation_result['valid_entries'] += 1
                else:
                    validation_result['invalid_entries'] += 1
            
            validation_result['integrity_score'] = (
                validation_result['valid_entries'] / validation_result['total_entries'] 
                if validation_result['total_entries'] > 0 else 0
            )
            
            return validation_result
            
        except Exception as e:
            return {
                'error': f"Validation failed: {str(e)}",
                'integrity_score': 0
            }
