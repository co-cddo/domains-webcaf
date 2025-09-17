import unittest
from pathlib import Path

import yaml


class TestFrameworkIndexes(unittest.TestCase):
    # Note the limitations of this class in the frameworks README
    def setUp(self):
        yaml_path = Path("frameworks/cyber-assessment-framework-v3.2.yaml")
        with open(yaml_path, "r") as f:
            self.framework = yaml.safe_load(f)

        self.objectives_indexes = []
        self.principles_indexes = []
        self.outcomes_indexes = []
        self.indicators_indexes = []

        self._populate_indexes()

    def _populate_indexes(self):
        for obj_idx, objective in self.framework.get("objectives", {}).items():
            self.objectives_indexes.append(obj_idx)
            for princ_idx, principle in objective.get("principles", {}).items():
                self.principles_indexes.append(princ_idx)
                for outcome_idx, outcome in principle.get("outcomes", {}).items():
                    self.outcomes_indexes.append(outcome_idx)
                    indicators = outcome.get("indicators", {})
                    for indicator_type in ["not-achieved", "partially-achieved", "achieved"]:
                        for index in indicators.get(indicator_type, {}):
                            self.indicators_indexes.append(index)

    # There's no point testing the uniqueness of the objective indexes because they are always
    # in the same YAML dictionary and the duplicate index will just overwrite the first when the
    # YAML is parsed. Use the check-yaml pre-commit hook to catch this and other cases of
    # duplicate indexes within the same dictionary.

    def test_principle_indexes_are_unique(self):
        self._test_indexes_are_unique(self.principles_indexes, "principle")

    def test_outcome_indexes_are_unique(self):
        self._test_indexes_are_unique(self.outcomes_indexes, "outcome")

    def test_indicator_indexes_are_unique(self):
        self._test_indexes_are_unique(self.indicators_indexes, "indicator")

    def _test_indexes_are_unique(self, indexes, index_type):
        seen_indexes = {}
        duplicate_indexes = []
        for index in indexes:
            if index in seen_indexes:
                if index not in duplicate_indexes:
                    duplicate_indexes.append(index)
            else:
                seen_indexes[index] = True
        if duplicate_indexes:
            error_msg = f"\nDuplicate {index_type} indexes found:\n"
            for index in duplicate_indexes:
                occurrences = indexes.count(index)
                error_msg += f"Index {index} appears {occurrences} times\n"
            self.fail(error_msg)

    def test_indicators_unique_within_outcomes(self):
        for objective in self.framework.get("objectives", {}).values():
            for principle in objective.get("principles", {}).values():
                for sec_idx, outcome in principle.get("outcomes", {}).items():
                    outcome_indicators = []
                    for level in ["not-achieved", "partially-achieved", "achieved"]:
                        level_indicators = outcome.get("indicators", {}).get(level, {})
                        for indicator_idx in level_indicators.keys():
                            outcome_indicators.append(indicator_idx)
                    seen_indices = {}
                    duplicates = []
                    for idx in outcome_indicators:
                        if idx in seen_indices:
                            duplicates.append(idx)
                        else:
                            seen_indices[idx] = True
                    if duplicates:
                        error_msg = f"\nDuplicate indicator indices in outcome {outcome.get('code', sec_idx)}:\n"
                        for idx in set(duplicates):
                            count = outcome_indicators.count(idx)
                            error_msg += f"Index {idx} appears {count} times\n"
                        self.fail(error_msg)

    def test_indicator_indices_within_outcomes_match_code_prefix(self):
        for objective in self.framework.get("objectives", {}).values():
            for principle in objective.get("principles", {}).values():
                for sec_idx, outcome in principle.get("outcomes", {}).items():
                    outcome_code = outcome.get("code", "")
                    if not outcome_code:
                        self.fail(f"outcome {sec_idx} does not have a code defined")
                    for level in ["not-achieved", "partially-achieved", "achieved"]:
                        level_indicators = outcome.get("indicators", {}).get(level, {})
                        for indicator_idx in level_indicators.keys():
                            if not str(indicator_idx).startswith(outcome_code):
                                self.fail(
                                    f"Indicator index {indicator_idx} in outcome {outcome_code} "
                                    f"does not start with outcome code"
                                )


class TestFrameworkStructure(unittest.TestCase):
    def setUp(self):
        yaml_path = Path("frameworks/cyber-assessment-framework-v3.2.yaml")
        with open(yaml_path, "r") as f:
            self.framework = yaml.safe_load(f)
        self.objectives = {}
        self.principles = {}
        self.outcomes = {}

        self._populate_yaml_items()

    def _populate_yaml_items(self):
        for obj_idx, objective in self.framework.get("objectives", {}).items():
            self.objectives[obj_idx] = objective
            for princ_idx, principle in objective.get("principles", {}).items():
                self.principles[princ_idx] = principle
                for outcome_idx, outcome in principle.get("outcomes", {}).items():
                    self.outcomes[outcome_idx] = outcome

    def _test_structure(self, items, item_type, expected_keys):
        for idx, item in items.items():
            item_keys = set(item.keys())

            unexpected_keys = item_keys - expected_keys
            if unexpected_keys:
                self.fail(f"{item_type.capitalize()} {idx} contains unexpected keys: {unexpected_keys}")

            missing_keys = expected_keys - item_keys
            if missing_keys:
                self.fail(f"{item_type.capitalize()} {idx} is missing required keys: {missing_keys}")

    def test_objectives_structure(self):
        self._test_structure(
            self.objectives,
            "objective",
            expected_keys={"code", "title", "description", "principles"},
        )

    def test_principles_structure(self):
        self._test_structure(
            self.principles,
            "principle",
            expected_keys={"code", "title", "description", "outcomes"},
        )

    def test_outcomes_structure(self):
        expected_keys = {"code", "title", "description", "indicators", "assessment-rules", "min_profile_requirement"}

        self._test_structure(
            self.outcomes,
            "outcome",
            expected_keys=expected_keys,
        )

        for outcome_idx, outcome in self.outcomes.items():
            indicators = outcome.get("indicators", {})
            expected_indicator_categories = {"not-achieved", "partially-achieved", "achieved"}
            indicator_categories = set(indicators.keys())
            unexpected_categories = indicator_categories - expected_indicator_categories
            if unexpected_categories:
                self.fail(f"outcome {outcome_idx} contains unexpected indicator categories: {unexpected_categories}")


if __name__ == "__main__":
    unittest.main()
