"""
Topic utility functions for subject-wise classification
"""


def classify_topics_by_subject():
    """
    Classify existing topics by their subjects (Physics, Chemistry, Botany, Zoology)
    
    Returns:
        dict: Subject-wise topic classification
        
    Example:
        {
            'Physics': ['Mechanics', 'Thermodynamics', ...],
            'Chemistry': ['Organic Chemistry', 'Inorganic Chemistry', ...],
            'Botany': ['Plant Anatomy', 'Photosynthesis', ...],
            'Zoology': ['Animal Kingdom', 'Human Physiology', ...]
        }
    """
    from ..models import Topic
    
    # NEET subject classification patterns
    physics_keywords = [
        'mechanics', 'motion', 'force', 'energy', 'power', 'work', 'momentum', 'gravity',
        'thermodynamics', 'heat', 'temperature', 'kinetic', 'potential', 'oscillation',
        'wave', 'sound', 'light', 'optics', 'reflection', 'refraction', 'diffraction',
        'electricity', 'current', 'voltage', 'resistance', 'capacitor', 'magnetic',
        'electromagnetic', 'atom', 'nuclear', 'radioactivity', 'quantum', 'photon'
    ]
    
    chemistry_keywords = [
        'atomic', 'periodic', 'chemical', 'reaction', 'equation', 'compound', 'element',
        'organic', 'inorganic', 'carbon', 'hydrocarbon', 'alcohol', 'acid', 'base',
        'salt', 'ionic', 'covalent', 'molecular', 'solution', 'concentration', 'molarity',
        'thermochemistry', 'equilibrium', 'kinetics', 'electrochemistry', 'oxidation',
        'reduction', 'catalyst', 'polymer', 'biomolecule', 'coordination'
    ]
    
    botany_keywords = [
        'plant', 'leaf', 'stem', 'root', 'flower', 'fruit', 'seed', 'photosynthesis',
        'respiration', 'transpiration', 'anatomy', 'morphology', 'taxonomy', 'classification',
        'cell', 'tissue', 'xylem', 'phloem', 'cambium', 'meristem', 'reproduction',
        'pollination', 'fertilization', 'embryo', 'germination', 'growth', 'hormone',
        'auxin', 'gibberellin', 'cytokinin', 'ecology', 'biodiversity', 'ecosystem'
    ]
    
    zoology_keywords = [
        'animal', 'mammal', 'bird', 'fish', 'reptile', 'amphibian', 'insect', 'arthropod',
        'vertebrate', 'invertebrate', 'nervous', 'circulatory', 'respiratory', 'digestive',
        'excretory', 'reproductive', 'endocrine', 'muscular', 'skeletal', 'human',
        'physiology', 'anatomy', 'blood', 'heart', 'lung', 'kidney', 'brain', 'hormone',
        'enzyme', 'protein', 'genetics', 'heredity', 'dna', 'chromosome', 'evolution'
    ]
    
    # Get all topics
    topics = Topic.objects.all()
    
    classification = {
        'Physics': [],
        'Chemistry': [],
        'Botany': [],
        'Zoology': [],
        'Unclassified': []
    }
    
    for topic in topics:
        topic_name_lower = topic.name.lower()
        classified = False
        
        # Check for Physics keywords
        if any(keyword in topic_name_lower for keyword in physics_keywords):
            classification['Physics'].append(topic.name)
            classified = True
        
        # Check for Chemistry keywords
        elif any(keyword in topic_name_lower for keyword in chemistry_keywords):
            classification['Chemistry'].append(topic.name)
            classified = True
        
        # Check for Botany keywords
        elif any(keyword in topic_name_lower for keyword in botany_keywords):
            classification['Botany'].append(topic.name)
            classified = True
        
        # Check for Zoology keywords
        elif any(keyword in topic_name_lower for keyword in zoology_keywords):
            classification['Zoology'].append(topic.name)
            classified = True
        
        # If no keywords match, mark as unclassified
        if not classified:
            classification['Unclassified'].append(topic.name)
    
    return classification


def get_topics_by_subject(subject_name):
    """
    Get all topics for a specific subject
    
    Args:
        subject_name (str): Subject name ('Physics', 'Chemistry', 'Botany', 'Zoology')
        
    Returns:
        list: List of topic names for the subject
    """
    classification = classify_topics_by_subject()
    return classification.get(subject_name, [])


def get_topic_subject(topic_name):
    """
    Get the subject for a specific topic
    
    Args:
        topic_name (str): Name of the topic
        
    Returns:
        str: Subject name or 'Unclassified'
    """
    classification = classify_topics_by_subject()
    
    for subject, topics in classification.items():
        if topic_name in topics:
            return subject
    
    return 'Unclassified'


def update_topic_subjects():
    """
    Update all topics with their classified subjects
    This function can be called to populate subject fields in Topic model
    
    Returns:
        dict: Summary of classification results
    """
    from ..models import Topic
    
    classification = classify_topics_by_subject()
    summary = {}
    
    for subject, topic_names in classification.items():
        count = len(topic_names)
        summary[subject] = count
        
        # Update topics with subject (if Topic model has subject field)
        # This would be used after we add subject field to Topic model
        # for topic_name in topic_names:
        #     try:
        #         topic = Topic.objects.get(name=topic_name)
        #         topic.subject = subject
        #         topic.save()
        #     except Topic.DoesNotExist:
        #         pass
    
    return summary
