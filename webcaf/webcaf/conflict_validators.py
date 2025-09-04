import logging
import os

import yaml

from webcaf import settings


class ConflictValidator:
    pass


class CAF32ConflictValidator(ConflictValidator):
    logger = logging.getLogger("CAF32ConflictValidator")

    rules = yaml.safe_load(open(os.path.join(settings.BASE_DIR, "..", "frameworks", "conflict_rules-3.2.yaml")))

    @staticmethod
    def validate(submitted_data):
        """
        {'achieved_A1.a.5': 'agreed', 'achieved_A1.a.5_not_true_have_justification_comment': '', 'achieved_A1.a.6': 'agreed', 'achieved_A1.a.6_not_true_have_justification_comment': 'rtertertr', 'achieved_A1.a.7': 'agreed', 'achieved_A1.a.7_not_true_have_justification_comment': '', 'achieved_A1.a.8': 'agreed', 'achieved_A1.a.8_not_true_have_justification_comment': '', 'not-achieved_A1.a.1': 'not_true_no_justification', 'not-achieved_A1.a.1_agreed_comment': '', 'not-achieved_A1.a.2': 'not_true_have_justification', 'not-achieved_A1.a.2_agreed_comment': '', 'not-achieved_A1.a.3': 'agreed', 'not-achieved_A1.a.3_agreed_comment': 'retrter', 'not-achieved_A1.a.4': 'agreed', 'not-achieved_A1.a.4_agreed_comment': 'ertert'}
        :param submitted_data:
        :return:
        """
        conflicting_elements = []
        agreed_elements = [key for key, value in submitted_data.items() if value == "agreed"]
        CAF32ConflictValidator.logger.info(f"Found following items as agreed: {agreed_elements}")
        # Filter out the keys from the names
        keys = [item.split("_")[-1] for item in agreed_elements]
        key_prefix = keys[0].split(".")[0]
        rules_to_check = [
            rule
            for rule in CAF32ConflictValidator.rules["conflict_rules"]
            if rule["rule_id"].startswith(f"G_{key_prefix}")
        ]
        for rule in rules_to_check:
            common_elements = set(keys) & set(rule["matching_ids"])
            if len(common_elements) > 1:
                conflicting_elements.append({"rule": rule, "answers": common_elements})
        return conflicting_elements
