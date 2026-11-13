Feature: GovAssure lead submits an assessment for independent review

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
    And the user "alice@example.gov.uk" exists
    And User "alice@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the user "assessor_1@example.com" exists
    And User "assessor_1@example.com" has the profile "Independent assurance reviewer" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And there is a "enhanced" profile assessment for "System 1", "Ministry of Agriculture", for the period "current" in "draft" status and data "alice_completed_assessment.json"

  Scenario: Submitting an independent assessment creates a review for the independent assessor
    Given the user logs in with username "alice@example.gov.uk" and password "password"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    Then page has heading "Complete a WebCAF self-assessment"
    And get assessment id from url and add to context
    And confirm the current assessment has expected data "alice_completed_assessment.json"
    And confirm the current assessment has version as "caf40" type as "independent" and profile as "enhanced"
    And click link with text "Complete the full self-assessment"
    When click button with text "Save and Send for Review"
    Then page has heading "Self-assessment completed"
    And logs out by clicking link
