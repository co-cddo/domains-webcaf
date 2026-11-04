Feature: Moving through an outcome that has not been answered yet

  Submitting an outcome's statements leads to its confirmation page. Roles
  that can only view an assessment skip the save, so an outcome they have not
  answered has nothing to confirm: they go on to the objective page instead,
  and nothing is saved (CS-507).

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1"
    And the user "cyber_advisor@example.gov.uk" exists
    And User "cyber_advisor@example.gov.uk" has the profile "Cyber advisor" assigned in "Ministry of Agriculture"
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And there is a "enhanced" profile assessment  for "System 1", "Ministry of Agriculture", for the period "current" in "draft" status and data "empty_assessment.json"

  Scenario: GovAssure lead submits statements for an unanswered outcome
    Given the user signs in with One Login as "other@example.gov.uk"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    And get assessment id from url and add to context
    Then navigate to "Objective C: Detecting Cyber Security Events"
    When Fill outcome "C1.f Understanding User's and System's Behaviour, and Threat Intelligence (within Security Monitoring)" with "achieved, partially-achieved, not-achieved" with "some,none,none"
    Then page has heading "Threat Intelligence (within Security Monitoring) Outcome"

  Scenario: Cyber advisor continues past an unanswered outcome without saving
    Given the user signs in with One Login as "cyber_advisor@example.gov.uk"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    And get assessment id from url and add to context
    Then navigate to "Objective C: Detecting Cyber Security Events"
    When Fill outcome "C1.f Understanding User's and System's Behaviour, and Threat Intelligence (within Security Monitoring)" with "achieved, partially-achieved, not-achieved" with "some,none,none"
    Then page has heading "Detecting Cyber Security Events"
    And confirm the current assessment has expected data "empty_assessment.json"
