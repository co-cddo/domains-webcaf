import unittest
from pathlib import Path

import yaml


class TestFrameworkIndexes(unittest.TestCase):
    def setUp(self):
        yaml_path = Path("frameworks/cyber-assessment-framework-v3.2.yaml")
        with open(yaml_path, "r") as f:
            self.framework = yaml.safe_load(f)

        self.objectives_indexes = []
        self.principles_indexes = []
        self.sections_indexes = []
        self.indicators_indexes = []

        self._populate_indexes()

    def _populate_indexes(self):
        """Populate all index collections by traversing the nested structure"""
        # Get objectives indexes
        for obj_idx, objective in self.framework.get("objectives", {}).items():
            self.objectives_indexes.append(int(obj_idx))

            # Get principles indexes for this objective
            for princ_idx, principle in objective.get("principles", {}).items():
                self.principles_indexes.append(int(princ_idx))

                # Get sections indexes for this principle
                for section_idx, section in principle.get("sections", {}).items():
                    self.sections_indexes.append(int(section_idx))

                    # Get indicator indexes for this section
                    indicators = section.get("indicators", {})
                    for indicator_type in ["not-achieved", "partially-achieved", "achieved"]:
                        for index in indicators.get(indicator_type, {}):
                            self.indicators_indexes.append(int(index))

    # There's no point testing the uniqueness of the objective indexes because they are always
    # in the same YAML dictionary and the duplicate index will just overwrite the first when the
    # YAML is parsed. Use the check-yaml pre-commit hook to catch this and other cases of
    # duplicate indexes within the same dictionary.

    def test_principle_indexes_are_unique(self):
        self._test_indexes_are_unique(self.principles_indexes, "principle")

    def test_section_indexes_are_unique(self):
        self._test_indexes_are_unique(self.sections_indexes, "section")

    def test_indicator_indexes_are_unique(self):
        self._test_indexes_are_unique(self.indicators_indexes, "indicator")

    def _test_indexes_are_unique(self, indexes, index_type):
        """Test that all indexes of a given type are unique"""
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

    def _test_indexes_are_continuous(self, indexes, index_type):
        min_idx = min(indexes)
        max_idx = max(indexes)
        expected_range = set(range(min_idx, max_idx + 1))

        missing_indexes = expected_range - set(indexes)

        if missing_indexes:
            missing_list = sorted(list(missing_indexes))
            self.fail(f"Missing {index_type} indexes: {missing_list}")

    def test_objective_indexes_are_continuous(self):
        self._test_indexes_are_continuous(self.objectives_indexes, "objective")

    def test_principle_indexes_are_continuous(self):
        self._test_indexes_are_continuous(self.principles_indexes, "principle")

    def test_section_indexes_are_continuous(self):
        self._test_indexes_are_continuous(self.sections_indexes, "section")

    def test_indicator_indexes_are_continuous(self):
        self._test_indexes_are_continuous(self.indicators_indexes, "indicator")


class TestFrameworkStructure(unittest.TestCase):
    def setUp(self):
        yaml_path = Path("frameworks/cyber-assessment-framework-v3.2.yaml")
        with open(yaml_path, "r") as f:
            self.framework = yaml.safe_load(f)
        self.objectives = {}
        self.principles = {}
        self.sections = {}

        self._populate_yaml_items()

    def _populate_yaml_items(self):
        for obj_idx, objective in self.framework.get("objectives", {}).items():
            self.objectives[obj_idx] = objective
            for princ_idx, principle in objective.get("principles", {}).items():
                self.principles[princ_idx] = principle
                for section_idx, section in principle.get("sections", {}).items():
                    self.sections[section_idx] = section

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
            expected_keys={"code", "title", "description", "sections"},
        )

    def test_sections_structure(self):
        expected_keys = {"code", "title", "description", "indicators", "assessment-rules"}

        self._test_structure(
            self.sections,
            "section",
            expected_keys=expected_keys,
        )

        for section_idx, section in self.sections.items():
            indicators = section.get("indicators", {})
            expected_indicator_categories = {"not-achieved", "partially-achieved", "achieved"}
            indicator_categories = set(indicators.keys())
            unexpected_categories = indicator_categories - expected_indicator_categories
            if unexpected_categories:
                self.fail(f"Section {section_idx} contains unexpected indicator categories: {unexpected_categories}")


if __name__ == "__main__":
    unittest.main()
