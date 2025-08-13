from utils.constants import SKILL_LEVELS, STATES, RANKS

def validate_wage_master_data(data):
    """Validate wage master data"""
    errors = []
    
    # Required fields (skill_level is now optional)
    required_fields = ['site_name', 'rank', 'state', 'base_wage']
    for field in required_fields:
        if not data.get(field):
            errors.append(f'{field} is required')
    
    # Validate skill level
    if data.get('skill_level') and data['skill_level'] not in SKILL_LEVELS:
        errors.append(f'skill_level must be one of: {", ".join(SKILL_LEVELS)}')
    
    # Validate base wage
    if data.get('base_wage'):
        try:
            wage = float(data['base_wage'])
            if wage <= 0:
                errors.append('base_wage must be greater than 0')
        except ValueError:
            errors.append('base_wage must be a valid number')
    
    # Validate string lengths
    if data.get('site_name') and len(data['site_name']) > 100:
        errors.append('site_name must be less than 100 characters')
    
    if data.get('rank') and len(data['rank']) > 50:
        errors.append('rank must be less than 50 characters')
    
    if data.get('state') and len(data['state']) > 50:
        errors.append('state must be less than 50 characters')
    
    return errors