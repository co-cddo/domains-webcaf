import yaml
from functools import cached_property


class FrameworkRouter:
    def __init__(self, framework_path):
        self.file_path = framework_path
        self.framework = {}
        self._read()

    def _read(self):
        with open(self.file_path, 'r') as file:
            self.framework = yaml.safe_load(file)
    
    @cached_property
    def all(self) -> list[dict]:
        items = []
        
        for obj_key, objective in self.framework.get('objectives', {}).items():
            items.append({
                'type': 'objective',
                'id': obj_key,
                'code': objective.get('code'),
                'title': objective.get('title'),
                'description': objective.get('description')
            })
            
            for principle_key, principle in objective.get('principles', {}).items():
                items.append({
                    'type': 'principle',
                    'id': principle_key,
                    'code': principle.get('code'),
                    'title': principle.get('title'),
                    'description': principle.get('description'),
                    'objective_id': obj_key
                })
                
                for section_key, section in principle.get('sections', {}).items():
                    items.append({
                        'type': 'section',
                        'id': section_key,
                        'code': section.get('code'),
                        'title': section.get('title'),
                        'description': section.get('description'),
                        'scope': section.get('scope'),
                        'indicators': section.get('indicators'),
                        'principle_id': principle_key,
                        'objective_id': obj_key
                    })
        
        return items

